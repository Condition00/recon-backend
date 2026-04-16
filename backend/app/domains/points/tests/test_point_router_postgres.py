import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models  # noqa: F401
from app.db.database import get_db
from app.db.post_commit import pop_post_commit_hooks
from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT, ROLE_PARTNER, Role, User
from app.main import app
from app.utils.deps import get_current_user, get_redis

TEST_POSTGRES_DSN = os.getenv("TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_POSTGRES_DSN,
    reason="Set TEST_POSTGRES_DSN to run Postgres-backed points concurrency tests.",
)


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str | int | float] = {}
        self.sorted_sets: dict[str, dict[str, float]] = {}

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value, ex=None):
        self.kv[key] = value

    async def delete(self, *keys: str):
        count = 0
        for key in keys:
            if key in self.kv:
                del self.kv[key]
                count += 1
            if key in self.sorted_sets:
                del self.sorted_sets[key]
                count += 1
        return count

    async def publish(self, channel: str, payload):
        return 0

    async def zadd(self, key: str, mapping: dict[str, float]):
        bucket = self.sorted_sets.setdefault(key, {})
        bucket.update(mapping)
        return 1

    async def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False):
        rows = sorted(self.sorted_sets.get(key, {}).items(), key=lambda row: (-row[1], row[0]))
        if stop == -1:
            rows = rows[start:]
        else:
            rows = rows[start : stop + 1]
        return rows if withscores else [member for member, _ in rows]

    async def rename(self, source_key: str, destination_key: str):
        if source_key in self.sorted_sets:
            self.sorted_sets[destination_key] = self.sorted_sets.pop(source_key)
            return True
        raise KeyError(source_key)


@pytest_asyncio.fixture
async def pg_session_factory():
    engine = create_async_engine(TEST_POSTGRES_DSN)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def pg_client(pg_session_factory):
    async def override_get_db():
        async with pg_session_factory() as session:
            try:
                yield session
                await session.commit()
                hooks = pop_post_commit_hooks(session)
                for hook in hooks:
                    await hook()
            except Exception:
                pop_post_commit_hooks(session)
                await session.rollback()
                raise

    fake_redis = FakeRedis()

    async def override_get_redis():
        return fake_redis

    app.state.disable_points_outbox_daemon = True
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=True) as client:
        yield client
    app.dependency_overrides.clear()
    if hasattr(app.state, "disable_points_outbox_daemon"):
        delattr(app.state, "disable_points_outbox_daemon")


@pytest_asyncio.fixture
async def pg_seeded_roles(pg_session_factory):
    async with pg_session_factory() as session:
        session.add_all(
            [
                Role(name=ROLE_ADMIN, description="Admin"),
                Role(name=ROLE_PARTICIPANT, description="Participant"),
                Role(name=ROLE_PARTNER, description="Partner"),
            ]
        )
        await session.commit()


@pytest_asyncio.fixture
async def pg_create_user(pg_session_factory, pg_seeded_roles):
    async def _create(*, email: str, username: str, role_name: str = ROLE_PARTICIPANT) -> User:
        async with pg_session_factory() as session:
            role = (await session.exec(select(Role).where(Role.name == role_name))).one()
            user = User(email=email, username=username, role_id=role.id)
            user.role = role
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user.role = role
            return user

    return _create


@pytest.fixture
def pg_auth_override():
    original = app.dependency_overrides.get(get_current_user)

    def _set(user: User):
        async def override() -> User:
            return user

        app.dependency_overrides[get_current_user] = override

    yield _set
    if original is not None:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_postgres_concurrent_awards_same_participant(pg_client, pg_create_user, pg_auth_override):
    admin = await pg_create_user(email="pg-admin@example.com", username="pgadmin", role_name=ROLE_ADMIN)
    player = await pg_create_user(email="pg-player@example.com", username="pgplayer")

    pg_auth_override(player)
    create = await pg_client.post(
        "/api/v1/participants/me",
        json={"display_name": "pg-lock", "institution": "VIT-AP", "year": 2},
    )
    assert create.status_code == 201
    participant_id = create.json()["id"]

    pg_auth_override(admin)

    async def _award(idem: str, amount: int):
        return await pg_client.post(
            "/api/v1/points/award",
            json={
                "participant_id": participant_id,
                "amount": amount,
                "reason": "zone.lock_hunt.complete",
                "idempotency_key": idem,
            },
        )

    r1, r2 = await asyncio.gather(_award(str(uuid.uuid4()), 30), _award(str(uuid.uuid4()), 40))
    assert r1.status_code == 201
    assert r2.status_code == 201

    pg_auth_override(player)
    me = await pg_client.get("/api/v1/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 70


@pytest.mark.asyncio
async def test_postgres_concurrent_same_idempotency_same_payload_single_effect(
    pg_client, pg_create_user, pg_auth_override
):
    admin = await pg_create_user(email="pg-admin-idem@example.com", username="pgadminidem", role_name=ROLE_ADMIN)
    player = await pg_create_user(email="pg-player-idem@example.com", username="pgplayeridem")

    pg_auth_override(player)
    create = await pg_client.post(
        "/api/v1/participants/me",
        json={"display_name": "pg-idem-same", "institution": "VIT-AP", "year": 2},
    )
    assert create.status_code == 201
    participant_id = create.json()["id"]

    pg_auth_override(admin)
    idem_key = str(uuid.uuid4())

    async def _award():
        return await pg_client.post(
            "/api/v1/points/award",
            json={
                "participant_id": participant_id,
                "amount": 55,
                "reason": "zone.lock_hunt.complete",
                "idempotency_key": idem_key,
            },
        )

    r1, r2 = await asyncio.gather(_award(), _award())
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["transaction"]["id"] == r2.json()["transaction"]["id"]

    pg_auth_override(player)
    me = await pg_client.get("/api/v1/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 55


@pytest.mark.asyncio
async def test_postgres_concurrent_same_idempotency_different_payload_conflicts(
    pg_client, pg_create_user, pg_auth_override
):
    admin = await pg_create_user(
        email="pg-admin-idem-conflict@example.com",
        username="pgadminidemconflict",
        role_name=ROLE_ADMIN,
    )
    player = await pg_create_user(email="pg-player-idem-conflict@example.com", username="pgplayeridemconflict")

    pg_auth_override(player)
    create = await pg_client.post(
        "/api/v1/participants/me",
        json={"display_name": "pg-idem-conflict", "institution": "VIT-AP", "year": 2},
    )
    assert create.status_code == 201
    participant_id = create.json()["id"]

    pg_auth_override(admin)
    idem_key = str(uuid.uuid4())

    async def _award(amount: int):
        return await pg_client.post(
            "/api/v1/points/award",
            json={
                "participant_id": participant_id,
                "amount": amount,
                "reason": "zone.lock_hunt.complete",
                "idempotency_key": idem_key,
            },
        )

    r1, r2 = await asyncio.gather(_award(30), _award(40))
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]

    pg_auth_override(player)
    me = await pg_client.get("/api/v1/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] in (30, 40)


@pytest.mark.asyncio
async def test_postgres_concurrent_spend_only_one_succeeds_when_insufficient(
    pg_client, pg_create_user, pg_auth_override
):
    admin = await pg_create_user(email="pg-admin-spend@example.com", username="pgadminspend", role_name=ROLE_ADMIN)
    player = await pg_create_user(email="pg-player-spend@example.com", username="pgplayerspend")

    pg_auth_override(player)
    create = await pg_client.post(
        "/api/v1/participants/me",
        json={"display_name": "pg-spend-race", "institution": "VIT-AP", "year": 2},
    )
    assert create.status_code == 201
    participant_id = create.json()["id"]

    pg_auth_override(admin)
    seed = await pg_client.post(
        "/api/v1/points/award",
        json={
            "participant_id": participant_id,
            "amount": 50,
            "reason": "schedule.session.attend",
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert seed.status_code == 201

    async def _spend(idem: str):
        return await pg_client.post(
            "/api/v1/points/award",
            json={
                "participant_id": participant_id,
                "amount": -40,
                "reason": "shop.redeem",
                "idempotency_key": idem,
            },
        )

    r1, r2 = await asyncio.gather(_spend(str(uuid.uuid4())), _spend(str(uuid.uuid4())))
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]

    pg_auth_override(player)
    me = await pg_client.get("/api/v1/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 10
