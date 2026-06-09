"""Application API endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_async_session
from app.dependencies import get_current_user
from app.models.application import Application, ApplicationStatus
from app.models.deleted_application import DeletedApplication
from app.models.status_history import ApplicationStatusHistory, StatusSource
from app.models.user import User

router = APIRouter(prefix="/applications", tags=["Applications"])


class StatusUpdateRequest(BaseModel):
    status: ApplicationStatus
    notes: str | None = None


@router.patch(
    "/{app_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Manually update application status",
)
async def manual_update_status(
    app_id: UUID,
    payload: StatusUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """
    Manually override an application's status.
    Generates a history log with source='manual_update'.
    """
    from sqlalchemy import select
    from datetime import datetime, timezone
    
    result = await session.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user.id)
    )
    app = result.scalars().first()
    
    if not app:
        return {"status": "error", "message": "Application not found"}
        
    now = datetime.now(timezone.utc)
    app.current_status = payload.status
    app.last_activity_at = now
    
    history = ApplicationStatusHistory(
        application_id=app.id,
        user_id=user.id,
        status=payload.status.value,
        source=StatusSource.MANUAL_UPDATE.value,
        detected_at=now,
        notes=payload.notes,
    )
    session.add(history)
    await session.commit()
    
    from app.worker.tasks import generate_analytics_task
    generate_analytics_task.delay(str(user.id))
    
    return {"status": "success", "message": "Status updated successfully"}


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List applications with filtering and search",
)
async def list_applications(
    status_filter: ApplicationStatus | None = Query(None, alias="status"),
    company: str | None = Query(None),
    role: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Returns a paginated list of applications for the user.
    Supports filtering by status, and case-insensitive search by company/role.
    """
    stmt = select(Application).where(
        Application.user_id == user.id,
        Application.is_deleted == False  # noqa: E712
    )

    if status_filter:
        stmt = stmt.where(Application.current_status == status_filter)
    if company:
        stmt = stmt.where(Application.company_name.ilike(f"%{company}%"))
    if role:
        stmt = stmt.where(Application.role_title.ilike(f"%{role}%"))

    stmt = stmt.order_by(Application.last_activity_at.desc()).offset(offset).limit(limit)
    
    result = await session.execute(stmt)
    apps = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(app.id),
                "company_name": app.company_name,
                "role_title": app.role_title,
                "current_status": app.current_status.value,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "last_activity_at": app.last_activity_at.isoformat(),
                "created_at": app.created_at.isoformat(),
                "confidence_scores": app.confidence_scores,
            }
            for app in apps
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{app_id}/timeline",
    status_code=status.HTTP_200_OK,
    summary="Get application timeline",
)
async def get_application_timeline(
    app_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Returns the status history timeline for an application.
    """
    result = await session.execute(
        select(ApplicationStatusHistory)
        .where(
            ApplicationStatusHistory.application_id == app_id,
            ApplicationStatusHistory.user_id == user.id,
        )
        .order_by(ApplicationStatusHistory.detected_at.asc())
    )
    history = result.scalars().all()
    
    return [
        {
            "id": str(h.id),
            "status": h.status,
            "source": h.source,
            "detected_at": h.detected_at.isoformat(),
            "notes": h.notes,
            "confidence_scores": h.confidence_scores,
        }
        for h in history
    ]


@router.delete(
    "/{app_id}",
    status_code=status.HTTP_200_OK,
    summary="Move application to bin",
)
async def delete_application(
    app_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Soft deletes an application by moving it to the bin.
    It will be automatically purged after 15 days.
    """
    from datetime import datetime, timezone, timedelta
    
    result = await session.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user.id)
    )
    app = result.scalars().first()
    
    if not app or app.is_deleted:
        raise HTTPException(status_code=404, detail="Application not found")
        
    now = datetime.now(timezone.utc)
    app.is_deleted = True
    app.deleted_at = now
    
    bin_record = DeletedApplication(
        application_id=app.id,
        user_id=user.id,
        deleted_at=now,
        purge_after=now + timedelta(days=15),
        deleted_by="user",
    )
    session.add(bin_record)
    await session.commit()
    
    return {"status": "success", "message": "Application moved to bin"}


@router.post(
    "/{app_id}/restore",
    status_code=status.HTTP_200_OK,
    summary="Restore application from bin",
)
async def restore_application(
    app_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Restores a soft-deleted application.
    """
    result = await session.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user.id)
    )
    app = result.scalars().first()
    
    if not app or not app.is_deleted:
        raise HTTPException(status_code=404, detail="Application not found in bin")
        
    app.is_deleted = False
    app.deleted_at = None
    
    # Remove bin record
    await session.execute(
        select(DeletedApplication).where(DeletedApplication.application_id == app_id)
    )
    # Actually we can just delete it directly
    from sqlalchemy import delete
    await session.execute(
        delete(DeletedApplication).where(DeletedApplication.application_id == app_id)
    )
    
    await session.commit()
    return {"status": "success", "message": "Application restored"}


@router.get(
    "/bin/list",
    status_code=status.HTTP_200_OK,
    summary="List applications in bin",
)
async def list_bin(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Returns a list of soft-deleted applications for the user.
    """
    stmt = (
        select(Application, DeletedApplication.purge_after)
        .join(DeletedApplication, Application.id == DeletedApplication.application_id)
        .where(
            Application.user_id == user.id,
            Application.is_deleted == True  # noqa: E712
        )
        .order_by(Application.deleted_at.desc())
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    return [
        {
            "id": str(app.id),
            "company_name": app.company_name,
            "role_title": app.role_title,
            "deleted_at": app.deleted_at.isoformat() if app.deleted_at else None,
            "purge_after": purge_after.isoformat() if purge_after else None,
        }
        for app, purge_after in rows
    ]


@router.delete(
    "/bin/{app_id}/purge",
    status_code=status.HTTP_200_OK,
    summary="Permanently purge application from bin",
)
async def purge_application(
    app_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Permanently deletes an application and all its associated data from the database.
    This action cannot be undone.
    """
    from sqlalchemy import delete as sa_delete

    result = await session.execute(
        select(Application).where(
            Application.id == app_id,
            Application.user_id == user.id,
            Application.is_deleted == True  # noqa: E712
        )
    )
    app = result.scalars().first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found in bin")

    # Remove the bin record
    await session.execute(
        sa_delete(DeletedApplication).where(DeletedApplication.application_id == app_id)
    )
    # Remove status history
    from app.models.status_history import ApplicationStatusHistory
    await session.execute(
        sa_delete(ApplicationStatusHistory).where(
            ApplicationStatusHistory.application_id == app_id
        )
    )
    # Remove the application itself
    await session.delete(app)
    await session.commit()

    return {"status": "success", "message": "Application permanently deleted"}
