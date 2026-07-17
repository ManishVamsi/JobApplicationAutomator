"""Users router — profile, resume upload, API token management."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import ApiTokenInfo, ApiTokenResponse, UserProfile, UserUpdate
from app.services.resume_service import ResumeService
from app.services.storage_service import get_storage_service
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

user_service = UserService()

MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/me", response_model=UserProfile)
async def get_profile(user: CurrentUser) -> UserProfile:
    """Get the current user's profile."""
    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        target_roles=user.target_roles or [],
        target_locations=user.target_locations or [],
        work_auth_status=user.work_auth_status,
        created_at=user.created_at.isoformat(),
    )


@router.put("/me", response_model=UserProfile)
async def update_profile(
    body: UserUpdate,
    user: CurrentUser,
    db: DbSession,
) -> UserProfile:
    """Update the current user's profile."""
    updated = await user_service.update_profile(
        db,
        str(user.id),
        name=body.name,
        target_roles=body.target_roles,
        target_locations=body.target_locations,
        work_auth_status=body.work_auth_status,
    )
    return UserProfile(
        id=str(updated.id),
        email=updated.email,
        name=updated.name,
        target_roles=updated.target_roles or [],
        target_locations=updated.target_locations or [],
        work_auth_status=updated.work_auth_status,
        created_at=updated.created_at.isoformat(),
    )


@router.post("/me/resume", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Upload a PDF/DOCX resume (max 10MB).

    Stores in object storage, triggers LLM-based parsing.
    Re-upload replaces the previous resume.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Use PDF or DOCX.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    storage = get_storage_service()
    resume_service = ResumeService(storage)
    resume = await resume_service.upload_resume(
        db,
        str(user.id),
        file.filename or "resume",
        file_bytes,
        file.content_type or "application/pdf",
    )

    # Extract text and queue parsing task
    try:
        text = ResumeService.extract_text(file_bytes, file.content_type or "")
        # TODO: Queue Celery task for LLM parsing with extracted text
    except Exception:
        pass  # Text extraction failure is non-fatal; resume is still stored

    return {
        "id": str(resume.id),
        "filename": resume.filename,
        "size_bytes": resume.file_size_bytes,
        "message": "Resume uploaded. Parsing will complete in the background.",
    }


@router.post("/me/api-token", response_model=ApiTokenResponse)
async def generate_api_token(
    user: CurrentUser,
    db: DbSession,
) -> ApiTokenResponse:
    """Generate or rotate the extension API token.

    Returns the raw token ONCE — copy it now. It cannot be retrieved again.
    If a token already exists, it is revoked and replaced.
    """
    raw_token = await user_service.generate_api_token(db, str(user.id))
    return ApiTokenResponse(
        token=raw_token,
        message="Token generated. Copy it now — it will not be shown again.",
    )


@router.delete("/me/api-token", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_token(
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Revoke the current API token without generating a new one."""
    revoked = await user_service.revoke_api_token(db, str(user.id))
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active API token found.",
        )


@router.get("/me/api-token", response_model=ApiTokenInfo | None)
async def get_api_token_info(
    user: CurrentUser,
    db: DbSession,
) -> ApiTokenInfo | None:
    """Get the current API token's metadata (prefix only — never the raw token)."""
    info = await user_service.get_api_token_info(db, str(user.id))
    if info is None:
        return None
    return ApiTokenInfo(**info)
