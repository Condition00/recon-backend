import asyncio
import os
import uuid

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT, Role, User
from app.domains.participants.models import Participant

RUN_LIVE_TESTS = os.getenv("RUN_LIVE_TESTS") == "1"
BASE_URL = os.getenv("LIVE_BASE_URL", "http://127.0.0.1:8000")
API_PREFIX = "/api/v1"

pytestmark = pytest.mark.skipif(
    not RUN_LIVE_TESTS,
    reason="Set RUN_LIVE_TESTS=1 to execute live-server points tests.",
)


@pytest_asyncio.fixture
async def live_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def db_session_factory():
    engine = create_async_engine(
        str(settings.ASYNC_DATABASE_URI),
        poolclass=NullPool,
    )
    factory = async_sessionmaker(
        engine,
        class_=SQLModelAsyncSession,
        expire_on_commit=False,
    )
    try:
        yield factory
    finally:
        await engine.dispose()


async def _ensure_role(session_factory, name: str) -> Role:
    async with session_factory() as session:
        result = await session.exec(select(Role).where(Role.name == name))
        role = result.one_or_none()
        if role is not None:
            return role
        role = Role(name=name, description=f"auto-created for live tests: {name}")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        return role


async def _create_user(session_factory, *, role_name: str, suffix: str) -> User:
    role = await _ensure_role(session_factory, role_name)
    async with session_factory() as session:
        user = User(
            email=f"live-{role_name}-{suffix}@example.com",
            username=f"live_{role_name}_{suffix}",
            role_id=role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_participant_for_user(session_factory, user: User, *, suffix: str) -> Participant:
    async with session_factory() as session:
        participant = Participant(
            user_id=user.id,
            display_name=f"live-points-{suffix}",
            institution="VIT-AP",
            year=2,
        )
        session.add(participant)
        await session.commit()
        await session.refresh(participant)
        return participant


def _set_auth_cookie(client: httpx.AsyncClient, user: User, role_name: str) -> None:
    token = create_access_token(user.id, role_name)
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_live_points_award_and_leaderboard_flow(
    live_client: httpx.AsyncClient, db_session_factory
):
    suffix = uuid.uuid4().hex[:8]
    admin = await _create_user(db_session_factory, role_name=ROLE_ADMIN, suffix=f"admin-{suffix}")
    p1_user = await _create_user(db_session_factory, role_name=ROLE_PARTICIPANT, suffix=f"p1-{suffix}")
    p2_user = await _create_user(db_session_factory, role_name=ROLE_PARTICIPANT, suffix=f"p2-{suffix}")
    p1 = await _create_participant_for_user(db_session_factory, p1_user, suffix=f"p1-{suffix}")
    p2 = await _create_participant_for_user(db_session_factory, p2_user, suffix=f"p2-{suffix}")

    _set_auth_cookie(live_client, admin, ROLE_ADMIN)
    r1 = await live_client.post(
        f"{API_PREFIX}/points/award",
        json={
            "participant_id": str(p1.id),
            "amount": 120,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": f"live-award-1-{suffix}",
        },
    )
    r2 = await live_client.post(
        f"{API_PREFIX}/points/award",
        json={
            "participant_id": str(p2.id),
            "amount": 80,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": f"live-award-2-{suffix}",
        },
    )
    assert r1.status_code == 201
    assert r2.status_code == 201

    _set_auth_cookie(live_client, p1_user, ROLE_PARTICIPANT)
    me = await live_client.get(f"{API_PREFIX}/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 120

    board = await live_client.get(f"{API_PREFIX}/points/leaderboard?skip=0&limit=50")
    assert board.status_code == 200
    ids = [e["participant_id"] for e in board.json()["entries"]]
    assert str(p1.id) in ids
    assert str(p2.id) in ids


@pytest.mark.asyncio
async def test_live_points_idempotency_and_payload_conflict(
    live_client: httpx.AsyncClient, db_session_factory
):
    suffix = uuid.uuid4().hex[:8]
    admin = await _create_user(db_session_factory, role_name=ROLE_ADMIN, suffix=f"admin-{suffix}")
    user = await _create_user(db_session_factory, role_name=ROLE_PARTICIPANT, suffix=f"p-{suffix}")
    participant = await _create_participant_for_user(db_session_factory, user, suffix=f"p-{suffix}")

    _set_auth_cookie(live_client, admin, ROLE_ADMIN)
    payload = {
        "participant_id": str(participant.id),
        "amount": 35,
        "reason": "schedule.session.attend",
        "idempotency_key": f"live-idem-{suffix}",
    }
    first = await live_client.post(f"{API_PREFIX}/points/award", json=payload)
    second = await live_client.post(f"{API_PREFIX}/points/award", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["transaction"]["id"] == second.json()["transaction"]["id"]

    conflicting = await live_client.post(
        f"{API_PREFIX}/points/award",
        json={**payload, "amount": 40},
    )
    assert conflicting.status_code == 409


@pytest.mark.asyncio
async def test_live_points_concurrent_awards_same_participant(
    live_client: httpx.AsyncClient, db_session_factory
):
    suffix = uuid.uuid4().hex[:8]
    admin = await _create_user(db_session_factory, role_name=ROLE_ADMIN, suffix=f"admin-{suffix}")
    user = await _create_user(db_session_factory, role_name=ROLE_PARTICIPANT, suffix=f"p-{suffix}")
    participant = await _create_participant_for_user(db_session_factory, user, suffix=f"p-{suffix}")

    _set_auth_cookie(live_client, admin, ROLE_ADMIN)

    async def _award(amount: int, idem_suffix: str) -> httpx.Response:
        return await live_client.post(
            f"{API_PREFIX}/points/award",
            json={
                "participant_id": str(participant.id),
                "amount": amount,
                "reason": "zone.lock_hunt.complete",
                "idempotency_key": f"live-conc-{suffix}-{idem_suffix}",
            },
        )

    a, b = await asyncio.gather(_award(15, "a"), _award(25, "b"))
    assert a.status_code == 201
    assert b.status_code == 201

    _set_auth_cookie(live_client, user, ROLE_PARTICIPANT)
    me = await live_client.get(f"{API_PREFIX}/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 40


@pytest.mark.asyncio
async def test_live_points_admin_authz_and_maintenance_endpoints(
    live_client: httpx.AsyncClient, db_session_factory
):
    suffix = uuid.uuid4().hex[:8]
    admin = await _create_user(db_session_factory, role_name=ROLE_ADMIN, suffix=f"admin-{suffix}")
    user = await _create_user(db_session_factory, role_name=ROLE_PARTICIPANT, suffix=f"p-{suffix}")
    participant = await _create_participant_for_user(db_session_factory, user, suffix=f"p-{suffix}")

    _set_auth_cookie(live_client, admin, ROLE_ADMIN)
    award = await live_client.post(
        f"{API_PREFIX}/points/award",
        json={
            "participant_id": str(participant.id),
            "amount": 20,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": f"live-maint-award-{suffix}",
        },
    )
    assert award.status_code == 201

    _set_auth_cookie(live_client, user, ROLE_PARTICIPANT)
    forbidden = await live_client.get(f"{API_PREFIX}/points/transactions")
    assert forbidden.status_code == 403

    _set_auth_cookie(live_client, admin, ROLE_ADMIN)
    txs = await live_client.get(f"{API_PREFIX}/points/transactions")
    assert txs.status_code == 200
    assert "transactions" in txs.json()

    rebuild = await live_client.post(f"{API_PREFIX}/points/leaderboard/cache/rebuild")
    assert rebuild.status_code == 200
    assert rebuild.json()["total_ranked"] >= 1

    drain = await live_client.post(f"{API_PREFIX}/points/outbox/drain?limit=200")
    assert drain.status_code == 200
    body = drain.json()
    assert "processed" in body and "sent" in body and "failed" in body and "remaining_ready" in body
