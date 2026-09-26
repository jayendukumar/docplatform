"""Small durable job-state helpers; execution remains in the API until workers are isolated."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from sqlalchemy import and_, or_, select, update

from app.models import Job


LEASE_SECONDS = 60
SUPPORTED_KINDS = {"render", "extraction"}


def enqueue(connection, kind: str, payload: dict[str, Any], job_id: str) -> None:
    if kind not in SUPPORTED_KINDS:
        raise ValueError("unsupported job kind")
    connection.execute(Job.__table__.insert().values(
        id=job_id, kind=kind, status="queued", payload_json=json.dumps(payload), attempts=0))


def claim(connection, job_id: str, worker_id: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    row = connection.execute(select(Job.id, Job.kind, Job.payload_json, Job.status,
                                    Job.lease_expires_at, Job.attempts).where(
        and_(Job.id == job_id, or_(Job.status == "queued",
                                   and_(Job.status == "running", Job.lease_expires_at < now))))
    ).mappings().one_or_none()
    if row is None:
        return None
    lease = now + timedelta(seconds=LEASE_SECONDS)
    connection.execute(update(Job).where(Job.id == job_id).values(
        status="running", lease_owner=worker_id, lease_expires_at=lease,
        attempts=row["attempts"] + 1, updated_at=now))
    return {"id": row["id"], "kind": row["kind"], "payload": json.loads(row["payload_json"]),
            "attempts": row["attempts"] + 1}


def claim_next(connection, worker_id: str, kind: str | None = None) -> dict[str, Any] | None:
    """Claim the oldest queued or expired job for a deployment supervisor."""
    now = datetime.now(timezone.utc)
    conditions = [or_(Job.status == "queued", and_(Job.status == "running", Job.lease_expires_at < now))]
    if kind is not None:
        conditions.append(Job.kind == kind)
    row = connection.execute(select(Job.id).where(*conditions)
        .order_by(Job.created_at, Job.id).limit(1)).first()
    if row is None:
        return None
    return claim(connection, row[0], worker_id)
