"""
Security validation for uploaded documents in DocTrust.

Enforces:
- Supported formats only: PDF, DOCX, XLSX, PPTX.
- Magic signature / MIME type verification (no relying on client headers).
- Structural integrity checks.
- PDF active content inspection (/JavaScript, /Launch, /EmbeddedFiles, etc.).
- Office ZIP security:
  * Zip Slip path traversal rejection.
  * Encrypted entry rejection.
  * Decompression bomb / resource exhaustion limits (max 1000 entries, 150MB uncompressed, 10:1 ratio).
  * VBA macro detection (vbaProject.bin rejection).
  * OpenXML content type validation.
- Safe filename sanitization.
"""

import os
import re
import zipfile
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

import magic
from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}

EXTENSION_TO_FILE_TYPE = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".xlsx": "XLSX",
    ".pptx": "PPTX",
}

EXPECTED_CONTENT_TYPES = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# Dangerous PDF tokens that could trigger client-side script execution or external connections
PDF_DANGEROUS_PATTERNS = [
    re.compile(rb"/JavaScript\b", re.IGNORECASE),
    re.compile(rb"/JS\b", re.IGNORECASE),
    re.compile(rb"/Launch\b", re.IGNORECASE),
    re.compile(rb"/EmbeddedFiles\b", re.IGNORECASE),
    re.compile(rb"/SubmitForm\b", re.IGNORECASE),
    re.compile(rb"/ImportData\b", re.IGNORECASE),
]

# Office ZIP safety limits
MAX_ZIP_ENTRIES = 1000
MAX_UNCOMPRESSED_SIZE_BYTES = 150 * 1024 * 1024  # 150 MB
MAX_COMPRESSION_RATIO = 10.0


def sanitize_filename(raw_filename: str) -> str:
    """
    Sanitize an uploaded filename.
    Strips directory separators, null bytes, and path traversal tokens.
    Truncates to 100 characters while preserving the extension.
    """
    if not raw_filename:
        return "unnamed_document"

    # Extract base name only (defends against /path/to/file or C:\\file)
    name = Path(raw_filename).name
    # Strip null bytes and non-printable control characters
    name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", name)
    # Strip dangerous characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
    if not name or name.startswith("."):
        name = f"document_{name}"

    if len(name) > 100:
        base, ext = os.path.splitext(name)
        max_base = 100 - len(ext)
        name = base[:max_base] + ext

    return name


def validate_pdf_content(file_bytes: bytes):
    """
    Validate that file_bytes is a valid PDF structure and does not
    contain dangerous active content or executable actions.
    """
    if not file_bytes.startswith(b"%PDF-"):
        raise ValidationError("Invalid PDF file: Missing %PDF- header.")

    # Search for dangerous active PDF actions
    for pattern in PDF_DANGEROUS_PATTERNS:
        if pattern.search(file_bytes):
            raise ValidationError(
                "PDF contains forbidden active scripts or actions (e.g. JavaScript, Launch)."
            )


def validate_office_zip_content(file_bytes: bytes, file_type: str):
    """
    Validate Office OpenXML files (DOCX, XLSX, PPTX).
    Ensures safe archive limits (zip bombs), no path traversal (zip slip),
    no encrypted entries, no VBA macros, and valid OpenXML structure.
    """
    try:
        zf = zipfile.ZipFile(BytesIO(file_bytes))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValidationError(f"Invalid {file_type} file: corrupted or not a valid archive.") from exc

    infolist = zf.infolist()
    if len(infolist) > MAX_ZIP_ENTRIES:
        raise ValidationError(f"Invalid {file_type} file: entry count exceeds security limit ({MAX_ZIP_ENTRIES}).")

    total_uncompressed = 0
    total_compressed = 0
    names = set()

    for info in infolist:
        # Check for encrypted entry
        if info.flag_bits & 0x1:
            raise ValidationError(f"Encrypted entries in {file_type} files are not permitted.")

        # Check for Zip Slip / path traversal
        norm_name = os.path.normpath(info.filename)
        if norm_name.startswith("..") or os.path.isabs(info.filename) or "\\" in info.filename:
            raise ValidationError("Archive contains forbidden directory traversal paths.")

        # Macro check
        lower_name = info.filename.lower()
        if "vbaproject.bin" in lower_name or "vba" in lower_name and lower_name.endswith(".bin"):
            raise ValidationError(f"Office documents containing macros are strictly prohibited.")

        names.add(info.filename)
        total_uncompressed += info.file_size
        total_compressed += info.compress_size

        if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
            raise ValidationError("Archive exceeds maximum uncompressed size limit (potential zip bomb).")

    if total_compressed > 0:
        ratio = total_uncompressed / total_compressed
        if ratio > MAX_COMPRESSION_RATIO and total_uncompressed > 5 * 1024 * 1024:
            raise ValidationError("Archive compression ratio exceeds security limits (potential zip bomb).")

    # Verify OpenXML structure
    if "[Content_Types].xml" not in names:
        raise ValidationError(f"Invalid {file_type} file: missing [Content_Types].xml.")

    try:
        ct_data = zf.read("[Content_Types].xml")
        root = ET.fromstring(ct_data)
        content_types = {elem.attrib.get("ContentType", "") for elem in root}
        
        # Ensure correct main part type is present
        if file_type == "DOCX":
            if not any("wordprocessingml.document" in ct for ct in content_types):
                raise ValidationError("File is not a valid DOCX document.")
        elif file_type == "XLSX":
            if not any("spreadsheetml.sheet" in ct for ct in content_types):
                raise ValidationError("File is not a valid XLSX spreadsheet.")
        elif file_type == "PPTX":
            if not any("presentationml.presentation" in ct for ct in content_types):
                raise ValidationError("File is not a valid PPTX presentation.")

        # Reject macro-enabled types
        for ct in content_types:
            if "macroEnabled" in ct or "vba" in ct.lower():
                raise ValidationError("Macro-enabled Office documents are strictly prohibited.")

    except ET.ParseError as exc:
        raise ValidationError("Malformed OpenXML content types definition.") from exc


def validate_document_upload(file_obj, raw_filename: str) -> tuple[str, str, bytes]:
    """
    Performs comprehensive security and integrity validation on an uploaded file.

    Returns:
        tuple (file_type, content_type, file_bytes)

    Raises:
        ValidationError: If any security check or structure check fails.
    """
    if not raw_filename:
        raise ValidationError("Original filename must be provided.")

    ext = Path(raw_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    file_type = EXTENSION_TO_FILE_TYPE[ext]
    expected_mime = EXPECTED_CONTENT_TYPES[file_type]

    # Read bytes from file_obj (streaming or memory file)
    file_bytes = file_obj.read()
    if not file_bytes:
        raise ValidationError("Uploaded file is empty (0 bytes).")

    max_size = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024)
    if len(file_bytes) > max_size:
        raise ValidationError(
            f"File size ({len(file_bytes)} bytes) exceeds maximum permitted limit ({max_size} bytes)."
        )

    # Magic MIME type check on initial chunk
    sample = file_bytes[:4096]
    detected_mime = magic.from_buffer(sample, mime=True)

    if file_type == "PDF":
        if detected_mime != "application/pdf":
            raise ValidationError(
                f"File signature mismatch. Detected '{detected_mime}', expected '{expected_mime}'."
            )
        validate_pdf_content(file_bytes)
    else:
        # DOCX, XLSX, PPTX are zip archives
        valid_zip_mimes = {
            "application/zip",
            "application/x-zip-compressed",
            "application/octet-stream",
            expected_mime,
        }
        if detected_mime not in valid_zip_mimes and not expected_mime.startswith(detected_mime):
            raise ValidationError(
                f"File signature mismatch for Office document. Detected '{detected_mime}'."
            )
        validate_office_zip_content(file_bytes, file_type)

    return file_type, expected_mime, file_bytes
