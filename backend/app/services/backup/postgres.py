"""
PostgreSQL native backup and restore engine for Koyla.
Wraps pg_dump and psql / pg_restore with safe environment credential passing,
redacted logging, clean flags (--no-owner, --no-privileges), and SQLite test fallbacks.
"""
import logging
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


def redact_database_url(url: str) -> str:
    """
    Redacts password and sensitive user info from a database connection string.
    Example: postgresql://postgres:secret@localhost:5432/koyla -> postgresql://postgres:***@localhost:5432/koyla
    """
    if not url:
        return ""
    # Match scheme://user:pass@host...
    pattern = r"(://[^:]+:)([^@]+)(@)"
    return re.sub(pattern, r"\1***\3", url)


def parse_db_url(db_url: str) -> Dict[str, Any]:
    """
    Parses a SQLAlchemy or standard database URL into connection parameters.
    Handles dialects like postgresql+psycopg2://, postgresql://, sqlite:///.
    """
    clean_url = db_url.strip()
    # Normalize SQLAlchemy driver tags (e.g., postgresql+psycopg2 -> postgresql)
    if "://" in clean_url:
        scheme_full, remainder = clean_url.split("://", 1)
        base_scheme = scheme_full.split("+")[0]
        parsed = urlparse(f"{base_scheme}://{remainder}")
    else:
        parsed = urlparse(clean_url)

    scheme = parsed.scheme.lower()
    if scheme in ("sqlite", "sqlite3"):
        if ":///" in clean_url:
            path_part = clean_url.split(":///", 1)[1]
            if path_part.startswith("/"):
                db_path = "/" + path_part.lstrip("/")
            else:
                db_path = path_part
        else:
            db_path = parsed.path

        if db_path.startswith("/") and len(db_path) > 2 and db_path[2] == ":":
            # Windows absolute path /C:/...
            db_path = db_path[1:]

        if db_path != ":memory:":
            db_path = os.path.normpath(db_path)

        return {
            "engine": "sqlite",
            "db_path": db_path or ":memory:",
            "raw_url": redact_database_url(clean_url),
        }

    return {
        "engine": "postgresql",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "username": parsed.username or "postgres",
        "password": parsed.password or "",
        "database": (parsed.path or "/koyla").lstrip("/"),
        "raw_url": redact_database_url(clean_url),
    }


class PostgresBackupEngine:
    """
    Native PostgreSQL backup and restore orchestrator.
    Guarantees:
    - Never exposes passwords in command line arguments (uses PGPASSWORD environment variable).
    - Redacts credentials in all application logs.
    - Applies --no-owner and --no-privileges for portable restorations across environments.
    - Supports clean SQLite fallback for unit tests and local mock execution.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.raw_database_url = database_url or settings.DATABASE_URL
        self.db_params = parse_db_url(self.raw_database_url)
        self.is_postgres = self.db_params["engine"] == "postgresql"

    def dump(self, output_path: Path) -> Path:
        """
        Executes a database dump and saves output to output_path.
        Returns the confirmed path to the dump file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.is_postgres:
            return self._dump_postgres(output_path)
        else:
            return self._dump_sqlite(output_path)

    def _dump_postgres(self, output_path: Path) -> Path:
        pg_dump_bin = shutil.which("pg_dump")
        if not pg_dump_bin:
            raise RuntimeError(
                "pg_dump executable not found on system PATH. "
                "Ensure postgresql-client is installed in the runtime environment."
            )

        cmd = [
            pg_dump_bin,
            "-h", str(self.db_params["host"]),
            "-p", str(self.db_params["port"]),
            "-U", str(self.db_params["username"]),
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            "-f", str(output_path),
            str(self.db_params["database"]),
        ]

        env = os.environ.copy()
        if self.db_params["password"]:
            env["PGPASSWORD"] = str(self.db_params["password"])

        sanitized_cmd = [
            pg_dump_bin,
            "-h", str(self.db_params["host"]),
            "-p", str(self.db_params["port"]),
            "-U", str(self.db_params["username"]),
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            "-f", str(output_path),
            str(self.db_params["database"]),
        ]
        logger.info("Executing pg_dump command: %s (target=%s)", " ".join(sanitized_cmd), self.db_params["raw_url"])

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            err_msg = result.stderr.strip() or f"Process exited with code {result.returncode}"
            logger.error("pg_dump execution failed: %s", err_msg)
            raise RuntimeError(f"Database dump failed: {err_msg}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"pg_dump completed but output file '{output_path}' is missing or empty")

        # Cross-version compatibility: neutralize settings introduced in newer pg_dump (e.g. v17 transaction_timeout)
        try:
            sql_text = output_path.read_text(encoding="utf-8", errors="ignore")
            if "transaction_timeout" in sql_text:
                cleaned_sql = re.sub(r"SET\s+transaction_timeout\s*=[^;]+;", "-- SET transaction_timeout ignored for cross-version compatibility", sql_text)
                output_path.write_text(cleaned_sql, encoding="utf-8")
        except Exception as e:
            logger.debug("Cross-version SQL sanitization skipped: %s", e)

        logger.info("Database dump successfully created at '%s' (%d bytes)", output_path, output_path.stat().st_size)
        return output_path

    def _dump_sqlite(self, output_path: Path) -> Path:
        db_path = self.db_params.get("db_path", ":memory:")
        logger.info("Executing SQLite dump for %s to %s", db_path, output_path)
        try:
            conn = sqlite3.connect(db_path)
            with open(output_path, "w", encoding="utf-8") as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            conn.close()
        except Exception as e:
            logger.error("SQLite dump failed: %s", str(e))
            raise RuntimeError(f"SQLite database dump failed: {str(e)}")

        return output_path

    def check_target_has_tables(self, target_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determines whether the target database contains existing schema objects/tables.
        Used as part of the safety barrier before restoring.
        """
        params = target_params or self.db_params
        if params["engine"] == "postgresql":
            psql_bin = shutil.which("psql")
            if not psql_bin:
                return False  # Cannot check directly via psql binary, defer to connection
            query = "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
            cmd = [
                psql_bin,
                "-h", str(params["host"]),
                "-p", str(params["port"]),
                "-U", str(params["username"]),
                "-d", str(params["database"]),
                "-t",
                "-A",
                "-c", query,
            ]
            env = os.environ.copy()
            if params.get("password"):
                env["PGPASSWORD"] = str(params["password"])
            try:
                res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    val = res.stdout.strip()
                    count = int(val) if val.isdigit() else 0
                    return count > 0
            except Exception as e:
                logger.warning("Could not probe existing postgres tables: %s", str(e))
                return False
            return False
        else:
            db_path = params.get("db_path", ":memory:")
            if db_path != ":memory:" and not Path(db_path).exists():
                return False
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                count = cursor.fetchone()[0]
                conn.close()
                return count > 0
            except Exception:
                return False

    def restore(
        self,
        dump_path: Path,
        force: bool = False,
        target_db_url: Optional[str] = None
    ) -> bool:
        """
        Restores a database from a dump file.
        Requires force=True if target database contains existing tables.
        """
        dump_path = Path(dump_path)
        if not dump_path.is_file():
            raise FileNotFoundError(f"Database dump file does not exist at '{dump_path}'")

        target_params = parse_db_url(target_db_url) if target_db_url else self.db_params

        # Safety barrier: refuse restore if target has existing data and force is False
        if not force and self.check_target_has_tables(target_params):
            refusal_msg = (
                f"Safety barrier: Target database '{target_params['raw_url']}' contains existing tables. "
                "Restoration refused unless force=True is explicitly specified."
            )
            logger.warning(refusal_msg)
            raise RuntimeError(refusal_msg)

        if target_params["engine"] == "postgresql":
            return self._restore_postgres(dump_path, target_params)
        else:
            return self._restore_sqlite(dump_path, target_params)

    def _restore_postgres(self, dump_path: Path, target_params: Dict[str, Any]) -> bool:
        psql_bin = shutil.which("psql")
        if not psql_bin:
            raise RuntimeError(
                "psql executable not found on system PATH. "
                "Ensure postgresql-client is installed in the runtime environment."
            )

        cmd = [
            psql_bin,
            "-h", str(target_params["host"]),
            "-p", str(target_params["port"]),
            "-U", str(target_params["username"]),
            "-d", str(target_params["database"]),
            "-f", str(dump_path),
        ]

        env = os.environ.copy()
        if target_params.get("password"):
            env["PGPASSWORD"] = str(target_params["password"])

        sanitized_cmd = [
            psql_bin,
            "-h", str(target_params["host"]),
            "-p", str(target_params["port"]),
            "-U", str(target_params["username"]),
            "-d", str(target_params["database"]),
            "-f", str(dump_path),
        ]
        logger.info("Executing psql restore: %s (target=%s)", " ".join(sanitized_cmd), target_params["raw_url"])

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            err_msg = result.stderr.strip() or f"Process exited with code {result.returncode}"
            logger.error("Database restore failed via psql: %s", err_msg)
            raise RuntimeError(f"Database restore failed: {err_msg}")

        logger.info("Database successfully restored from '%s' into '%s'", dump_path, target_params["raw_url"])
        return True

    def _restore_sqlite(self, dump_path: Path, target_params: Dict[str, Any]) -> bool:
        db_path = target_params.get("db_path", ":memory:")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.info("Executing SQLite restore for %s from %s", db_path, dump_path)
        try:
            with open(dump_path, "r", encoding="utf-8") as f:
                sql_script = f.read()

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.executescript(sql_script)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("SQLite restore failed: %s", str(e))
            raise RuntimeError(f"SQLite database restore failed: {str(e)}")
