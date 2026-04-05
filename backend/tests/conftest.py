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
from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT, ROLE_PARTNER, Role, User
from app.main import app
from app.utils.deps import get_current_user


TEST_DATABASE_URL = "sqlite+aiosqlite://"


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
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=True,
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()


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
