"""Portals router — CRUD for job portal connections."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.models.portal import PortalType
from app.schemas.portal import PortalCreate, PortalResponse
from app.services.portal_service import PortalService

router = APIRouter(prefix="/portals", tags=["portals"])

portal_service = PortalService()


@router.post("", response_model=PortalResponse, status_code=status.HTTP_201_CREATED)
async def create_portal(
    body: PortalCreate,
    request: Request,
    user: CurrentUser,
    db: DbSession,
) -> PortalResponse:
    """Add a new portal connection with encrypted credentials."""
    ip = request.client.host if request.client else None
    portal = await portal_service.create_portal(
        db,
        str(user.id),
        PortalType(body.portal_type),
        body.display_name,
        body.credentials,
        ip,
    )
    return PortalResponse(
        id=str(portal.id),
        portal_type=portal.portal_type.value,
        display_name=portal.display_name,
        status=portal.status.value,
        created_at=portal.created_at.isoformat(),
    )


@router.get("", response_model=list[PortalResponse])
async def list_portals(user: CurrentUser, db: DbSession) -> list[PortalResponse]:
    """List all portals for the current user."""
    portals = await portal_service.list_portals(db, str(user.id))
    return [
        PortalResponse(
            id=str(p.id),
            portal_type=p.portal_type.value,
            display_name=p.display_name,
            status=p.status.value,
            created_at=p.created_at.isoformat(),
        )
        for p in portals
    ]


@router.delete("/{portal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portal(
    portal_id: str,
    request: Request,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a portal and its encrypted credentials."""
    ip = request.client.host if request.client else None
    try:
        await portal_service.delete_portal(db, str(user.id), portal_id, ip)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portal not found")
