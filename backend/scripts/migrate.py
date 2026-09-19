import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.db.database import engine, Base
import app.models

def run_migrations():
    print(f"Connecting to database: {engine.url.render_as_string(hide_password=True)} ...")
    
    with engine.connect() as conn:
        print("Ensuring pgvector extension is enabled...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        
        # Verify pgvector
        res = conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")).fetchone()
        if res:
            print(f"pgvector extension active: {res[0]} v{res[1]}")
        else:
            print("WARNING: pgvector extension not found!")
            
    print("Creating all database tables via SQLAlchemy metadata...")
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        inspector = inspect(engine)
        chunk_cols = [c["name"] for c in inspector.get_columns("chunks")]
        if "chunk_type" not in chunk_cols:
            print("Adding chunk_type column to chunks table...")
            conn.execute(text("ALTER TABLE chunks ADD COLUMN chunk_type VARCHAR(20) DEFAULT 'TEXT';"))
            conn.commit()
        if "metadata_json" not in chunk_cols:
            print("Adding metadata_json column to chunks table...")
            conn.execute(text("ALTER TABLE chunks ADD COLUMN metadata_json JSON;"))
            conn.commit()
        conn.execute(text("ALTER TABLE chunks ALTER COLUMN section_heading TYPE TEXT;"))
        conn.execute(text("ALTER TABLE processing_jobs ALTER COLUMN error_message TYPE TEXT;"))
        conn.commit()

        # Table continuation migrations
        table_cols = [c["name"] for c in inspector.get_columns("tables")]
        if "logical_table_id" not in table_cols:
            print("Adding logical table continuation columns to tables...")
            conn.execute(text("ALTER TABLE tables ADD COLUMN logical_table_id VARCHAR(36);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tables_logical_table_id ON tables (logical_table_id);"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN is_continuation BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN continuation_of_id VARCHAR(36) REFERENCES tables(id);"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN part_number INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN total_parts INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN has_repeated_headers BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN continuation_confidence FLOAT DEFAULT 1.0;"))
            conn.execute(text("ALTER TABLE tables ADD COLUMN continuation_status VARCHAR(50) DEFAULT 'STANDALONE';"))
            conn.commit()

        row_cols = [c["name"] for c in inspector.get_columns("table_rows")]
        if "source_page" not in row_cols:
            print("Adding source_page and logical_row_index to table_rows...")
            conn.execute(text("ALTER TABLE table_rows ADD COLUMN source_page INTEGER;"))
            conn.execute(text("ALTER TABLE table_rows ADD COLUMN logical_row_index INTEGER;"))
            conn.commit()

        # Verification tasks columns
        verif_cols = [c["name"] for c in inspector.get_columns("verification_tasks")]
        if "organization_id" not in verif_cols:
            print("Adding organization_id to verification_tasks...")
            conn.execute(text("ALTER TABLE verification_tasks ADD COLUMN organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE;"))
            conn.commit()
        if "field_id" not in verif_cols:
            print("Adding field_id to verification_tasks...")
            conn.execute(text("ALTER TABLE verification_tasks ADD COLUMN field_id VARCHAR(36) REFERENCES extracted_fields(id) ON DELETE CASCADE;"))
            conn.commit()
        if "reconciliation_group_id" not in verif_cols:
            print("Adding reconciliation_group_id to verification_tasks...")
            conn.execute(text("ALTER TABLE verification_tasks ADD COLUMN reconciliation_group_id VARCHAR(36) REFERENCES reconciliation_groups(id) ON DELETE CASCADE;"))
            conn.commit()
        if "action_taken" not in verif_cols:
            print("Adding action_taken to verification_tasks...")
            conn.execute(text("ALTER TABLE verification_tasks ADD COLUMN action_taken VARCHAR(50);"))
            conn.commit()
        if "corrected_value" not in verif_cols:
            print("Adding corrected_value to verification_tasks...")
            conn.execute(text("ALTER TABLE verification_tasks ADD COLUMN corrected_value TEXT;"))
            conn.commit()
        if "evidence_context" not in verif_cols:
            print("Adding evidence_context to verification_tasks...")
            conn.execute(text("ALTER TABLE verification_tasks ADD COLUMN evidence_context JSON;"))
            conn.commit()

        # Purge stale deterministic or legacy embeddings when transitioning to neural model
        from app.services.embedding import get_embedding_provider
        from app.db.database import SessionLocal
        active_provider = get_embedding_provider()
        is_neural = active_provider.model_info().get("is_neural", False)
        print(f"Active embedding provider during migration: {active_provider.model_name} (is_neural: {is_neural})")
        
        if is_neural:
            # Purge any old deterministic or legacy embeddings
            res_del = conn.execute(text("DELETE FROM embeddings WHERE model_name != :active_model;"), {"active_model": active_provider.model_name})
            conn.commit()
            if res_del.rowcount:
                print(f"Purged {res_del.rowcount} stale embeddings not matching active neural model '{active_provider.model_name}'.")

            # Re-index all documents with genuine neural embeddings
            print(f"Re-indexing all document chunks with neural model '{active_provider.model_name}'...")
            session = SessionLocal()
            try:
                from app.services.indexing import indexing_service
                reindex_res = indexing_service.reindex_all(session, force=False)
                print(f"Neural re-indexing complete: {reindex_res.get('total_indexed')} chunks indexed in {reindex_res.get('time_taken_ms')}ms.")
            finally:
                session.close()

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Migrations complete. Active database tables ({len(tables)}):")
    for t in sorted(tables):
        print(f"  - {t}")

if __name__ == "__main__":
    run_migrations()
