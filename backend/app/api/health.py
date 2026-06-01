from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.session import get_async_session
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Basic API health check."""
    return {"status": "ok", "service": "jobtracker-api"}


@router.get("/database", status_code=status.HTTP_200_OK)
async def database_health(session: AsyncSession = Depends(get_async_session)) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@router.get("/redis", status_code=status.HTTP_200_OK)
async def redis_health() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        from app.config import settings
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        return {"status": "error", "redis": str(e)}


@router.get("/celery", status_code=status.HTTP_200_OK)
async def celery_health() -> Dict[str, Any]:
    """Check Celery worker availability."""
    try:
        i = celery_app.control.inspect()
        ping_result = i.ping()
        if not ping_result:
            return {"status": "error", "celery": "no workers available"}
        return {"status": "ok", "celery": "workers available", "nodes": list(ping_result.keys())}
    except Exception as e:
        return {"status": "error", "celery": str(e)}
