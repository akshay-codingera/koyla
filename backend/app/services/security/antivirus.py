import socket
import struct
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ScanResult:
    def __init__(
        self,
        is_clean: bool,
        scanner_status: str,
        virus_name: Optional[str] = None,
        message: str = "",
        scanned: bool = False
    ):
        self.is_clean = is_clean
        self.scanner_status = scanner_status  # "ACTIVE", "UNAVAILABLE", "DISABLED"
        self.virus_name = virus_name
        self.message = message
        self.scanned = scanned

    def to_dict(self) -> dict:
        return {
            "is_clean": self.is_clean,
            "scanner_status": self.scanner_status,
            "virus_name": self.virus_name,
            "message": self.message,
            "scanned": self.scanned
        }

class ClamAVScanner:
    """
    ClamAV TCP Daemon Integration Adapter.
    Interacts with clamd using the standard INSTREAM protocol.
    Accurately reports operational status: ACTIVE, UNAVAILABLE, or DISABLED.
    Never claims malware scanning is active if ClamAV daemon is not reachable.
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: Optional[float] = None,
        enabled: Optional[bool] = None
    ):
        self.host = host or settings.CLAMAV_HOST
        self.port = port or settings.CLAMAV_PORT
        self.timeout = timeout if timeout is not None else settings.CLAMAV_TIMEOUT_SECONDS
        self.enabled = enabled if enabled is not None else settings.CLAMAV_ENABLED

    def ping(self) -> bool:
        """Sends PING command to clamd daemon."""
        if not self.enabled:
            return False
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
                s.sendall(b"zPING\0")
                resp = s.recv(1024)
                return b"PONG" in resp
        except Exception:
            return False

    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scans a file using ClamAV zINSTREAM protocol.
        """
        if not self.enabled:
            return ScanResult(
                is_clean=True,
                scanner_status="DISABLED",
                message="ClamAV antivirus scanning is disabled in configuration.",
                scanned=False
            )

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
                s.sendall(b"zINSTREAM\0")
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536):
                        s.sendall(struct.pack("!I", len(chunk)) + chunk)
                # Zero-length chunk signals end of stream
                s.sendall(struct.pack("!I", 0))

                response = s.recv(4096).decode("utf-8", errors="replace").strip()
                if "OK" in response:
                    return ScanResult(
                        is_clean=True,
                        scanner_status="ACTIVE",
                        message="File scanned clean by ClamAV daemon.",
                        scanned=True
                    )
                elif "FOUND" in response:
                    parts = response.split("FOUND")[0].replace("stream:", "").strip()
                    virus_name = parts if parts else "MalwareDetected"
                    logger.warning(f"ClamAV detected malware in {file_path}: {virus_name}")
                    return ScanResult(
                        is_clean=False,
                        scanner_status="ACTIVE",
                        virus_name=virus_name,
                        message=f"Malware signature detected: {virus_name}",
                        scanned=True
                    )
                else:
                    return ScanResult(
                        is_clean=False,
                        scanner_status="ACTIVE",
                        message=f"Unexpected scanner response: {response}",
                        scanned=True
                    )
        except (socket.error, socket.timeout, ConnectionRefusedError) as e:
            logger.info(f"ClamAV daemon at {self.host}:{self.port} unreachable ({e}). Scanning inactive.")
            return ScanResult(
                is_clean=True,
                scanner_status="UNAVAILABLE",
                message=f"ClamAV daemon at {self.host}:{self.port} unreachable ({e}). Scanner inactive.",
                scanned=False
            )

    def health(self) -> dict:
        """
        Genuine health check for ClamAV daemon.
        """
        if not self.enabled:
            return {"status": "DISABLED", "message": "ClamAV scanning disabled"}
        if self.ping():
            return {"status": "ACTIVE", "message": f"ClamAV daemon active at {self.host}:{self.port}"}
        return {"status": "UNAVAILABLE", "message": f"ClamAV daemon at {self.host}:{self.port} unreachable"}

clamav_scanner = ClamAVScanner()
