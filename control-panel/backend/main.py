"""Decepticon Control Panel — admin-only dashboard API."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth, database as db, job_runner

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "frontend" / "dist"

app = FastAPI(
    title="Decepticon Control Panel",
    description="Admin dashboard for offensive security tooling",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class SettingUpdate(BaseModel):
    value: str
    description: Optional[str] = None


class JobCreate(BaseModel):
    tool: str
    target: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class EngagementCreate(BaseModel):
    name: str
    target_url: str
    notes: str = ""


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ── Lifecycle ────────────────────────────────────────────────────────────────


@app.on_event("startup")
def startup() -> None:
    db.init_db()
    auth.ensure_default_admin()


# ── Auth routes ──────────────────────────────────────────────────────────────


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict[str, Any]:
    user = auth.authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_access_token(user["id"], user["username"], user["role"])
    db.log_audit(user["id"], "login", "session", details=f"user={user['username']}")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
    }


@app.get("/api/auth/me")
def me(user: dict = Depends(auth.get_current_user)) -> dict[str, Any]:
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


@app.post("/api/auth/change-password")
def change_password(
    body: PasswordChange,
    user: dict = Depends(auth.require_admin),
) -> dict[str, str]:
    row = db.get_user_by_id(user["id"])
    if not row or not auth.verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    db.update_user_password(user["id"], auth.hash_password(body.new_password))
    db.log_audit(user["id"], "change_password", "user", str(user["id"]))
    return {"status": "ok"}


# ── Dashboard stats ──────────────────────────────────────────────────────────


@app.get("/api/stats")
def stats(user: dict = Depends(auth.get_current_user)) -> dict[str, Any]:
    return db.get_dashboard_stats()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


# ── Settings (admin-only write) ──────────────────────────────────────────────


@app.get("/api/settings")
def list_settings(user: dict = Depends(auth.get_current_user)) -> list[dict]:
    return db.get_all_settings()


@app.get("/api/settings/{key}")
def get_setting(key: str, user: dict = Depends(auth.get_current_user)) -> dict:
    row = db.get_setting(key)
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    return row


@app.put("/api/settings/{key}")
def update_setting(
    key: str,
    body: SettingUpdate,
    user: dict = Depends(auth.require_admin),
) -> dict:
    if not db.get_setting(key):
        raise HTTPException(status_code=404, detail="Setting not found")
    if body.value in ("••••••••", "********"):
        raise HTTPException(status_code=400, detail="Provide a new value for masked secrets")
    db.set_setting(key, body.value, body.description, updated_by=user["id"])
    db.log_audit(user["id"], "settings_update", "settings", key)
    return {"key": key, "value": body.value, "status": "updated"}


@app.post("/api/settings/bulk")
def bulk_settings(
    updates: dict[str, str],
    user: dict = Depends(auth.require_admin),
) -> dict[str, str]:
    count = 0
    for key, value in updates.items():
        if not db.get_setting(key):
            continue
        if value in ("••••••••", "********"):
            continue
        db.set_setting(key, value, updated_by=user["id"])
        count += 1
    db.log_audit(user["id"], "settings_bulk_update", "settings", str(count))
    return {"status": "ok", "updated": str(count)}


# ── Jobs ─────────────────────────────────────────────────────────────────────


@app.get("/api/jobs")
def list_jobs(
    limit: int = 50,
    user: dict = Depends(auth.get_current_user),
) -> list[dict]:
    return db.list_jobs(limit)


@app.get("/api/jobs/running")
def running_jobs(user: dict = Depends(auth.get_current_user)) -> list[dict]:
    return db.list_running_jobs()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, user: dict = Depends(auth.get_current_user)) -> dict:
    row = db.get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return row


@app.post("/api/jobs")
def create_job(
    body: JobCreate,
    user: dict = Depends(auth.require_admin),
) -> dict[str, Any]:
    if body.tool not in job_runner.TOOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool. Available: {list(job_runner.TOOLS.keys())}",
        )
    job_id = job_runner.start_job(body.tool, body.target, body.params, user["id"])
    return {"job_id": job_id, "status": "queued"}


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: int, user: dict = Depends(auth.require_admin)) -> dict:
    if not job_runner.stop_job(job_id, user["id"]):
        raise HTTPException(status_code=404, detail="Job not running")
    return {"job_id": job_id, "status": "stopped"}


@app.get("/api/tools")
def list_tools(user: dict = Depends(auth.get_current_user)) -> list[dict]:
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in job_runner.TOOLS.items()
    ]


# ── Engagements ──────────────────────────────────────────────────────────────


@app.get("/api/engagements")
def list_engagements(user: dict = Depends(auth.get_current_user)) -> list[dict]:
    return db.list_engagements()


@app.post("/api/engagements")
def create_engagement(
    body: EngagementCreate,
    user: dict = Depends(auth.require_admin),
) -> dict:
    eid = db.create_engagement(body.name, body.target_url, body.notes, user["id"])
    return {"id": eid, "status": "created"}


@app.delete("/api/engagements/{engagement_id}")
def delete_engagement(
    engagement_id: int,
    user: dict = Depends(auth.require_admin),
) -> dict:
    if not db.delete_engagement(engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    db.log_audit(user["id"], "delete_engagement", "engagement", str(engagement_id))
    return {"status": "deleted"}


# ── Audit log (admin) ────────────────────────────────────────────────────────


@app.get("/api/audit")
def audit_log(
    limit: int = 100,
    user: dict = Depends(auth.require_admin),
) -> list[dict]:
    return db.get_audit_log(limit)


# ── Static frontend ──────────────────────────────────────────────────────────


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "Control panel API running. Build frontend or open /api/docs"},
        status_code=200,
    )


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.exception_handler(404)
async def spa_fallback(request: Request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"detail": "Not found"}, status_code=404)
