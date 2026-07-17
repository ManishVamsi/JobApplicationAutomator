"""Resume service — upload to object storage, extract text, queue LLM parsing."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.resume import Resume
from app.services.storage_service import StorageService

logger = get_logger(__name__)


class ResumeService:
    """Handles resume upload, text extraction, and parsing orchestration."""

    def __init__(self, storage: StorageService) -> None:
        self._storage = storage

    async def upload_resume(
        self,
        db: AsyncSession,
        user_id: str,
        filename: str,
        file_bytes: bytes,
        content_type: str,
    ) -> Resume:
        """Upload a resume file and create/update the DB record.

        On re-upload: deletes the old file from storage and replaces the record.
        """
        # Delete existing resume if any
        result = await db.execute(
            select(Resume).where(Resume.user_id == user_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            try:
                await self._storage.delete(existing.storage_path)
            except Exception:
                logger.warning("Failed to delete old resume file", key=existing.storage_path)
            await db.delete(existing)
            await db.flush()

        # Upload to storage
        storage_key = StorageService.make_key(user_id, filename)
        await self._storage.upload(storage_key, file_bytes, content_type)

        # Create DB record
        resume = Resume(
            user_id=user_id,
            filename=filename,
            storage_path=storage_key,
            file_size_bytes=len(file_bytes),
            content_type=content_type,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(resume)
        await db.flush()

        logger.info("Resume uploaded", user_id=user_id, filename=filename, size=len(file_bytes))
        return resume

    @staticmethod
    def extract_text(file_bytes: bytes, content_type: str) -> str:
        """Extract raw text from PDF or DOCX in-memory."""
        if content_type == "application/pdf":
            return ResumeService._extract_pdf_text(file_bytes)
        elif content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return ResumeService._extract_docx_text(file_bytes)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    @staticmethod
    def _extract_pdf_text(file_bytes: bytes) -> str:
        """Extract text from PDF bytes using PyPDF2."""
        from io import BytesIO

        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)

    @staticmethod
    def _extract_docx_text(file_bytes: bytes) -> str:
        """Extract text from DOCX bytes using python-docx."""
        from io import BytesIO

        from docx import Document

        doc = Document(BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
