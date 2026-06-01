"""
Root API router — mounts all versioned sub-routers.

All routes are served under /v1 prefix.
Adding a new feature module requires only one line here.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.users import router as users_router

# ── Root v1 Router ─────────────────────────────────────────────────────────────
api_router = APIRouter(prefix="/v1")

# ── Phase 1 ────────────────────────────────────────────────────────────────────
api_router.include_router(auth_router)
api_router.include_router(users_router)

# ── Phase 2 (Gmail) ───────────────────────────────
from app.api.gmail import router as gmail_router
api_router.include_router(gmail_router)

# ── Phase 3 (Sync) ────────────────────────────────────────────────────────────
from app.api.sync import router as sync_router
api_router.include_router(sync_router)

# ── Phase 3–4 (Sync + Applications) ───────────────────────────────────────────
from app.api.analytics import router as analytics_router
from app.api.health import router as health_router

api_router.include_router(analytics_router)
api_router.include_router(health_router)
# from app.api.sync import router as sync_router
# from app.api.applications import router as applications_router
# from app.api.dashboard import router as dashboard_router
# api_router.include_router(sync_router)
# api_router.include_router(applications_router)
# api_router.include_router(dashboard_router)

# ── Phase 5–6 (Analytics + Bin) ───────────────────────────────────────────────
# from app.api.analytics import router as analytics_router
# from app.api.bin import router as bin_router
# api_router.include_router(analytics_router)
# api_router.include_router(bin_router)
