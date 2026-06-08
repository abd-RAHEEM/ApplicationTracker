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


@router.get("/db-debug", status_code=status.HTTP_200_OK)
async def database_debug(session: AsyncSession = Depends(get_async_session)) -> Dict[str, Any]:
    """Temporary debugging endpoint to inspect database tables and run migrations programmatically."""
    import os
    import traceback
    
    # 1. Query existing tables
    tables = []
    tables_error = None
    try:
        result = await session.execute(text(
            "SELECT tablename FROM pg_catalog.pg_tables "
            "WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'"
        ))
        tables = [row[0] for row in result.fetchall()]
    except Exception as e:
        tables_error = str(e)

    # 2. Test sync connection via psycopg (for Alembic env.py)
    import psycopg
    db_url_sync = os.environ.get("DATABASE_URL_SYNC", "Not Set")
    sync_conn_status = "unknown"
    sync_error = None
    if db_url_sync != "Not Set":
        try:
            conn_str = db_url_sync.replace("postgresql+psycopg://", "postgresql://")
            conn = psycopg.connect(conn_str)
            conn.close()
            sync_conn_status = "connected"
        except Exception as e:
            sync_conn_status = "failed"
            sync_error = f"{type(e).__name__}: {str(e)}"

    # File system check to debug paths on Render
    fs_debug = {}
    try:
        import os
        fs_debug["cwd"] = os.getcwd()
        fs_debug["cwd_list"] = os.listdir(os.getcwd())
        fs_debug["file_path"] = __file__
        fs_debug["file_dir_list"] = os.listdir(os.path.dirname(__file__))
        
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        fs_debug["parent_dir"] = parent_dir
        if os.path.exists(parent_dir):
            fs_debug["parent_dir_list"] = os.listdir(parent_dir)
            fs_debug["alembic_ini_exists"] = os.path.exists(os.path.join(parent_dir, "alembic.ini"))
            fs_debug["alembic_dir_exists"] = os.path.exists(os.path.join(parent_dir, "alembic"))
            if fs_debug["alembic_dir_exists"]:
                fs_debug["alembic_dir_list"] = os.listdir(os.path.join(parent_dir, "alembic"))
    except Exception as e:
        fs_debug["error"] = str(e)

    # 3. Attempt programmatic Alembic migration
    from alembic.config import Config
    from alembic import command
    alembic_status = "unknown"
    alembic_error = None
    
    try:
        # Resolve path to alembic.ini
        ini_path = "alembic.ini"
        if not os.path.exists(ini_path):
            ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "alembic.ini")
        
        alembic_cfg = Config(ini_path)
        # Resolve script_location to absolute path
        alembic_dir = os.path.join(os.path.dirname(ini_path), "alembic")
        alembic_cfg.set_main_option("script_location", alembic_dir)
        
        # Override with env var sync URL explicitly to verify setup
        if db_url_sync != "Not Set":
            alembic_cfg.set_main_option("sqlalchemy.url", db_url_sync)
            
        command.upgrade(alembic_cfg, "head")
        alembic_status = "success"
    except Exception as e:
        alembic_status = "failed"
        alembic_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

    return {
        "tables": tables,
        "tables_error": tables_error,
        "database_url_sync_set": db_url_sync != "Not Set",
        "sync_conn_status": sync_conn_status,
        "sync_error": sync_error,
        "fs_debug": fs_debug,
        "alembic_status": alembic_status,
        "alembic_error": alembic_error,
    }


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
