from collections.abc import AsyncGenerator, Callable
from pathlib import Path
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models  # noqa: F401
from app.db.database import get_db
from app.db.post_commit import pop_post_commit_hooks
from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT, ROLE_PARTNER, Role, User
from app.main import app
from app.utils.deps import get_current_user, get_redis


TEST_DATABASE_URL = "sqlite+aiosqlite://"


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

    async def zincrby(self, key: str, increment: float, member: str):
        bucket = self.sorted_sets.setdefault(key, {})
        bucket[member] = float(bucket.get(member, 0.0)) + float(increment)
        return bucket[member]

    async def zrevrank(self, key: str, member: str):
        ranked = sorted(self.sorted_sets.get(key, {}).items(), key=lambda row: (-row[1], row[0]))
        for idx, (m, _) in enumerate(ranked):
            if m == member:
                return idx
        return None

    async def zscore(self, key: str, member: str):
        return self.sorted_sets.get(key, {}).get(member)

    async def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False):
        ranked = sorted(self.sorted_sets.get(key, {}).items(), key=lambda row: (-row[1], row[0]))
        if stop == -1:
            sliced = ranked[start:]
        else:
            sliced = ranked[start : stop + 1]
        if withscores:
            return [(m, s) for m, s in sliced]
        return [m for m, _ in sliced]

    async def zcard(self, key: str):
        return len(self.sorted_sets.get(key, {}))

    async def rename(self, source_key: str, destination_key: str):
        if source_key in self.sorted_sets:
            self.sorted_sets[destination_key] = self.sorted_sets.pop(source_key)
            return True
        if source_key in self.kv:
            self.kv[destination_key] = self.kv.pop(source_key)
            return True
        raise KeyError(source_key)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest_asyncio.fixture
async def seeded_roles(session_factory) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                Role(name=ROLE_ADMIN, description="Admin"),
                Role(name=ROLE_PARTICIPANT, description="Participant"),
                Role(name=ROLE_PARTNER, description="Partner"),
            ]
        )
        await session.commit()


@pytest_asyncio.fixture
async def client(session_factory, seeded_roles) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        async with session_factory() as session:
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

    app.state.disable_points_outbox_daemon = True
    app.dependency_overrides[get_db] = override_get_db
    fake_redis = FakeRedis()

    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=True,
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()
    if hasattr(app.state, "disable_points_outbox_daemon"):
        delattr(app.state, "disable_points_outbox_daemon")


@pytest_asyncio.fixture
async def create_user(session_factory) -> Callable[..., User]:
    async def _create_user(*, role_name: str = ROLE_PARTICIPANT, email: str, username: str) -> User:
        async with session_factory() as session:
            role = (await session.exec(select(Role).where(Role.name == role_name))).one()
            user = User(email=email, username=username, role_id=role.id)
            user.role = role
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user.role = role
            return user

    return _create_user


@pytest.fixture
def auth_override():
    original = app.dependency_overrides.get(get_current_user)

    def _set(user: User) -> None:
        async def override_current_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = override_current_user

    yield _set

    if original is not None:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)
