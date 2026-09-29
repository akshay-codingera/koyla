"""
API endpoints for Koyla Backup, Restore & Disaster Recovery.
Restricted strictly to users with the SYSTEM_ADMIN role.
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.models.user import User
from app.services.audit import log_audit_event
from app.services.backup import (
    BackupRestoreService,
    BackupService,
    verify_backup,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def require_system_admin(current_user: User = Depends(get_current_active_user)) -> User:
    roles = [r.code for r in current_user.roles]
    if "SYSTEM_ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: SYSTEM_ADMIN role required for disaster recovery operations."
        )
    return current_user


class BackupCreateRequest(BaseModel):
    compress: bool = True
    include_db: Optional[bool] = None
    include_docs: Optional[bool] = None
    include_reports: Optional[bool] = None
    retention_count: Optional[int] = None


class BackupVerifyRequest(BaseModel):
    backup_path: str


class BackupRestoreRequest(BaseModel):
    backup_path: str
    force: bool = False
    target_storage_dir: Optional[str] = None
    target_reports_dir: Optional[str] = None
    target_db_url: Optional[str] = None


@router.post("/create", response_model=Dict[str, Any])
def create_backup(
    req: BackupCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_system_admin),
):
    """
    Triggers an immediate cryptographic backup of Koyla system state:
    database dump, durable documents, and statutory reports.
    """
    service = BackupService()
    try:
        result = service.create_backup(
            compress=req.compress,
            include_db=req.include_db,
            include_docs=req.include_docs,
            include_reports=req.include_reports,
            custom_retention=req.retention_count,
        )

        # Audit logging
        try:
            log_audit_event(
                db=db,
                action="BACKUP_CREATE",
                actor_id=admin_user.id,
                actor_name=admin_user.username,
                role_code="SYSTEM_ADMIN",
                organization_id=admin_user.organization_id,
                object_type="BACKUP",
                object_id=result.get("backup_id"),
                ip_address=request.client.host if request.client else None,
                details={
                    "backup_path": result.get("path"),
                    "is_compressed": result.get("is_compressed"),
                    "file_count": result.get("file_count"),
                    "total_bytes": result.get("total_bytes"),
                    "integrity_status": result.get("integrity_status"),
                },
            )
        except Exception as audit_err:
            logger.warning("Failed to record audit event for backup create: %s", str(audit_err))

        return result
    except Exception as exc:
        logger.error("API backup creation failed: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(exc)}"
        )


@router.get("/list", response_model=List[Dict[str, Any]])
def list_backups(
    admin_user: User = Depends(require_system_admin),
):
    """
    Lists existing backup archives and directories sorted by creation time descending.
    """
    service = BackupService()
    return service.list_backups()


@router.post("/verify", response_model=Dict[str, Any])
def verify_backup_endpoint(
    req: BackupVerifyRequest,
    admin_user: User = Depends(require_system_admin),
):
    """
    Verifies cryptographic SHA-256 hashes and structural completeness of a backup archive.
    """
    report = verify_backup(req.backup_path)
    return report.to_dict()


@router.post("/restore", response_model=Dict[str, Any])
def restore_backup_endpoint(
    req: BackupRestoreRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_system_admin),
):
    """
    Executes a verified restoration from a backup package into the Koyla runtime.
    Strictly enforces the safety barrier: requires force=True if target data exists.
    """
    service = BackupRestoreService()
    try:
        from pathlib import Path
        result = service.restore_backup(
            backup_target=req.backup_path,
            force=req.force,
            target_storage_dir=Path(req.target_storage_dir) if req.target_storage_dir else None,
            target_reports_dir=Path(req.target_reports_dir) if req.target_reports_dir else None,
            target_db_url=req.target_db_url,
        )

        # Audit logging
        try:
            log_audit_event(
                db=db,
                action="BACKUP_RESTORE",
                actor_id=admin_user.id,
                actor_name=admin_user.username,
                role_code="SYSTEM_ADMIN",
                organization_id=admin_user.organization_id,
                object_type="BACKUP",
                object_id=result.get("backup_id"),
                ip_address=request.client.host if request.client else None,
                details={
                    "backup_path": req.backup_path,
                    "force": req.force,
                    "files_restored": result.get("files_restored"),
                    "components_restored": result.get("components_restored"),
                },
            )
        except Exception as audit_err:
            logger.warning("Failed to record audit event for backup restore: %s", str(audit_err))

        return result
    except RuntimeError as r_err:
        # Safety barrier or operational refusal
        if "Safety barrier" in str(r_err) or "force=True" in str(r_err):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(r_err)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(r_err)
        )
    except ValueError as v_err:
        # Verification failure
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(v_err)
        )
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(fnf)
        )
    except Exception as exc:
        logger.error("API restoration failed: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restoration failed: {str(exc)}"
        )
