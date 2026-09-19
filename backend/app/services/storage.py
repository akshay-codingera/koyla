import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException
from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

ALLOWED_MIME_TYPES = set(ALLOWED_EXTENSIONS.values()).union({
    "application/x-pdf",
    "image/pjpeg",
    "image/x-png",
})

class StorageService:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.STORAGE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str, content_type: str = None) -> str:
        """
        Validates file extension and MIME type.
        Returns the canonical MIME type or raises HTTPException.
        """
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS.keys()))
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{ext}'. Supported formats: {allowed_list}"
            )
        
        expected_mime = ALLOWED_EXTENSIONS[ext]
        return expected_mime

    def compute_sha256(self, file_obj) -> str:
        """
        Computes SHA-256 hash by streaming chunks of 64KB.
        """
        sha256 = hashlib.sha256()
        file_obj.seek(0)
        while chunk := file_obj.read(65536):
            sha256.update(chunk)
        file_obj.seek(0)
        return sha256.hexdigest()

    def compute_file_sha256(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def save_uploaded_file(
        self,
        upload_file: UploadFile,
        organization_id: str,
        document_id: str
    ) -> Tuple[str, str, int]:
        """
        Saves uploaded file to partitioned path:
        storage/documents/{organization_id}/{document_id}/{safe_filename}
        Returns: (file_path, sha256_hash, file_size_bytes)
        """
        target_dir = self.base_dir / organization_id / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = Path(upload_file.filename).name
        target_path = target_dir / safe_filename

        sha256 = hashlib.sha256()
        total_size = 0
        
        await upload_file.seek(0)
        with open(target_path, "wb") as f:
            while chunk := await upload_file.read(65536):
                total_size += len(chunk)
                sha256.update(chunk)
                f.write(chunk)
                
        return str(target_path), sha256.hexdigest(), total_size

    def save_bytes(
        self,
        data: bytes,
        filename: str,
        organization_id: str,
        document_id: str
    ) -> Tuple[str, str, int]:
        """
        Saves raw bytes (for synthetic generation or tests) to partitioned path.
        Returns: (file_path, sha256_hash, file_size_bytes)
        """
        target_dir = self.base_dir / organization_id / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = Path(filename).name
        target_path = target_dir / safe_filename
        
        with open(target_path, "wb") as f:
            f.write(data)
            
        sha256 = hashlib.sha256(data).hexdigest()
        return str(target_path), sha256, len(data)

storage_service = StorageService()
