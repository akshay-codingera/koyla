import os
import shutil
import hashlib
import zipfile
from pathlib import Path
from typing import Tuple, Union, Optional
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from app.services.security.antivirus import clamav_scanner

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

FORBIDDEN_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".dll", ".so",
    ".msi", ".jar", ".bin", ".com", ".scr", ".pif", ".app", ".dmg",
    ".elf", ".py", ".php", ".jsp", ".asp", ".aspx"
}

ALLOWED_MIME_TYPES = set(ALLOWED_EXTENSIONS.values()).union({
    "application/x-pdf",
    "image/pjpeg",
    "image/x-png",
    "application/csv",
    "text/comma-separated-values",
})

# Forbidden executable magic byte headers
FORBIDDEN_MAGIC_SIGNATURES = [
    (b"MZ", "DOS/Windows Executable (PE)"),
    (b"\x7fELF", "Linux ELF Binary"),
    (b"\xca\xfe\xba\xbe", "Java Class / Mach-O Fat Binary"),
    (b"\xfe\xed\xfa\xce", "Mach-O 32-bit Binary"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit Binary"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32-bit Binary (reverse)"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit Binary (reverse)"),
]

class StorageService:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.STORAGE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir = Path(settings.STORAGE_QUARANTINE_DIR)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str, content_type: Optional[str] = None) -> str:
        """
        Validates file extension against allowed and forbidden sets, sanitizes filename.
        Returns the canonical MIME type or raises HTTPException.
        """
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file: filename cannot be empty."
            )
        
        # Check for path traversal / null bytes
        if "\x00" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: null bytes detected in filename."
            )

        safe_name = Path(filename).name
        ext = Path(safe_name).suffix.lower()

        if ext in FORBIDDEN_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security violation: Executable or script file extension '{ext}' is forbidden."
            )

        if ext not in ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS.keys()))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Supported formats: {allowed_list}"
            )

        return ALLOWED_EXTENSIONS[ext]

    def validate_content(self, file_path_or_bytes: Union[str, Path, bytes], expected_ext: str) -> None:
        """
        Validates magic bytes / content structure against expected file extension.
        Rejects forbidden executable binaries and MIME/content mismatches.
        """
        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                header = f.read(2048)
            file_path = str(file_path_or_bytes)
        else:
            header = file_path_or_bytes[:2048]
            file_path = None

        if len(header) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security validation failed: File is empty (0 bytes)."
            )

        # 1. Reject forbidden executable binary signatures
        for sig, desc in FORBIDDEN_MAGIC_SIGNATURES:
            if header.startswith(sig):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security violation: Forbidden executable binary signature detected ({desc})."
                )

        # 2. Check extension-specific magic bytes & structure
        ext = expected_ext.lower()
        if ext == ".pdf":
            # PDF header must contain %PDF within initial 1024 bytes
            if b"%PDF" not in header[:1024]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MIME/content signature mismatch: file lacks valid %PDF header."
                )
        elif ext in (".docx", ".xlsx"):
            # Zip header PK\x03\x04 or PK\x05\x06
            if not (header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"MIME/content signature mismatch: {ext.upper()} file lacks valid ZIP/Office archive header."
                )
            # If path available, inspect zip contents for Office XML parts
            if file_path:
                try:
                    with zipfile.ZipFile(file_path, "r") as zf:
                        namelist = zf.namelist()
                        if ext == ".docx" and not any(n.startswith("word/") or n == "[Content_Types].xml" for n in namelist):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="MIME/content signature mismatch: DOCX archive missing Word document structures."
                            )
                        if ext == ".xlsx" and not any(n.startswith("xl/") or n == "[Content_Types].xml" for n in namelist):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="MIME/content signature mismatch: XLSX archive missing Excel spreadsheet structures."
                            )
                except zipfile.BadZipFile:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"MIME/content signature mismatch: Corrupted or invalid {ext.upper()} archive."
                    )
        elif ext == ".xls":
            # OLE2 Compound Document header: \xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1
            if not header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MIME/content signature mismatch: XLS file lacks valid OLE2 compound document header."
                )
        elif ext == ".png":
            # PNG header: \x89PNG\r\n\x1a\n
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MIME/content signature mismatch: PNG file lacks valid PNG magic header."
                )
        elif ext in (".jpg", ".jpeg"):
            # JPEG SOI header: \xff\xd8\xff
            if not header.startswith(b"\xff\xd8\xff"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MIME/content signature mismatch: JPEG file lacks valid SOI magic header."
                )
        elif ext in (".csv", ".txt"):
            # Must be valid decodable text without null bytes or binary signatures
            if b"\x00" in header:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security violation: Binary null bytes detected in {ext.upper()} text file."
                )
            if header.startswith(b"PK\x03\x04") or header.startswith(b"%PDF") or header.startswith(b"\x89PNG"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"MIME/content signature mismatch: Binary archive header found in {ext.upper()} file."
                )

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
        Saves uploaded file via security quarantine pipeline:
        1. Sanitize filename & extension.
        2. Stream into quarantine directory storage/quarantine/{document_id}/{safe_filename}.
        3. Enforce maximum file size (100 MB).
        4. Validate magic byte header & content consistency.
        5. Scan for malware via ClamAV adapter (if enabled/running).
        6. Atomically promote from quarantine to storage/documents/{organization_id}/{document_id}/{safe_filename}.
        Returns: (file_path, sha256_hash, file_size_bytes)
        """
        safe_filename = Path(upload_file.filename).name
        ext = Path(safe_filename).suffix.lower()

        # Step 1: Validate file extension
        self.validate_file(safe_filename, upload_file.content_type)

        # Step 2: Quarantine staging
        doc_quarantine_dir = self.quarantine_dir / document_id
        doc_quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path = doc_quarantine_dir / safe_filename

        sha256 = hashlib.sha256()
        total_size = 0
        max_size = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100 * 1024 * 1024)

        try:
            await upload_file.seek(0)
            with open(quarantine_path, "wb") as f:
                while chunk := await upload_file.read(65536):
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum permitted upload limit of {max_size // (1024*1024)} MB."
                        )
                    sha256.update(chunk)
                    f.write(chunk)

            # Step 3: Validate magic bytes and format structure on quarantined file
            self.validate_content(quarantine_path, ext)

            # Step 4: ClamAV Antivirus check
            scan_res = clamav_scanner.scan_file(str(quarantine_path))
            if not scan_res.is_clean:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security check failed: {scan_res.message}"
                )
            if scan_res.scanner_status == "UNAVAILABLE" and getattr(settings, "CLAMAV_REQUIRED", False):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Antivirus scan is required by policy, but ClamAV service is currently unavailable."
                )

            # Step 5: Atomically promote to permanent storage
            target_dir = self.base_dir / organization_id / document_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / safe_filename

            shutil.move(str(quarantine_path), str(target_path))
            shutil.rmtree(doc_quarantine_dir, ignore_errors=True)

            return str(target_path), sha256.hexdigest(), total_size

        except Exception:
            # Clean up quarantine on any failure
            shutil.rmtree(doc_quarantine_dir, ignore_errors=True)
            raise

    def save_bytes(
        self,
        data: bytes,
        filename: str,
        organization_id: str,
        document_id: str,
        skip_validation: bool = False
    ) -> Tuple[str, str, int]:
        """
        Saves raw bytes (for synthetic generation or test seeding) with security checks.
        Returns: (file_path, sha256_hash, file_size_bytes)
        """
        safe_filename = Path(filename).name
        ext = Path(safe_filename).suffix.lower()

        if not skip_validation:
            self.validate_file(safe_filename)
            self.validate_content(data, ext)

        target_dir = self.base_dir / organization_id / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_filename

        with open(target_path, "wb") as f:
            f.write(data)

        sha256 = hashlib.sha256(data).hexdigest()
        return str(target_path), sha256, len(data)

storage_service = StorageService()
