import asyncio
import datetime
import uuid
from uuid import uuid4

import pytest
from sqlmodel import col, select

from app.domains.zones.models import Zone, ZoneRegistration


async def _create_zone(
    session_factory,
    *,
    name: str,
    short_name: str,
    is_active: bool = True,
) -> Zone:
    async with session_factory() as session:
        zone = Zone(
            name=name,
            short_name=short_name,
            category="challenge",
            zone_type="booth",
            status="green",
            location="Hall A",
            points=50,
            color="#22C55E",
            tags=["security", "network"],
            is_active=is_active,
        )
        session.add(zone)
        await session.commit()
        await session.refresh(zone)
        return zone


@pytest.mark.asyncio
async def test_zone_catalog_and_detail(client, auth_override, create_user, session_factory):
    user = await create_user(email="zones-list@example.com", username="zoneslist")
    auth_override(user)

    zone_a = await _create_zone(session_factory, name="Network Warfare", short_name="NW")
    await _create_zone(session_factory, name="Legacy Inactive", short_name="LI", is_active=False)

    catalog = await client.get("/api/v1/zones")
    assert catalog.status_code == 200
    assert len(catalog.json()) == 1
    assert catalog.json()[0]["shortName"] == "NW"
    assert catalog.json()[0]["registeredCount"] == 0

    detail = await client.get(f"/api/v1/zones/{zone_a.id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == str(zone_a.id)
    assert detail.json()["name"] == "Network Warfare"
    assert detail.json()["type"] == "booth"


@pytest.mark.asyncio
async def test_zone_register_unregister_and_me_endpoints(
    client, auth_override, create_user, session_factory
):
    user = await create_user(email="zones-reg@example.com", username="zonesreg")
    auth_override(user)
    create_me = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "zone-regger", "institution": "VIT-AP", "year": 2},
    )
    assert create_me.status_code == 201

    zone = await _create_zone(session_factory, name="Forensics", short_name="FORENSICS")

    register = await client.post(f"/api/v1/zones/{zone.id}/register")
    assert register.status_code == 201
    first_code = register.json()["code"]
    assert register.json()["zoneId"] == str(zone.id)
    assert register.json()["isActive"] is True
    assert first_code

    register_again = await client.post(f"/api/v1/zones/{zone.id}/register")
    assert register_again.status_code == 200
    assert register_again.json()["code"] == first_code

    regs = await client.get("/api/v1/me/registrations")
    assert regs.status_code == 200
    assert regs.json()["zoneIds"] == [str(zone.id)]

    passes = await client.get("/api/v1/me/passes")
    assert passes.status_code == 200
    assert len(passes.json()["passes"]) == 1
    assert passes.json()["passes"][0]["zoneId"] == str(zone.id)

    unregister = await client.delete(f"/api/v1/zones/{zone.id}/register")
    assert unregister.status_code == 200
    assert unregister.json()["isActive"] is False

    regs_after = await client.get("/api/v1/me/registrations")
    assert regs_after.status_code == 200
    assert regs_after.json()["zoneIds"] == []


@pytest.mark.asyncio
async def test_zone_register_requires_participant_profile(client, auth_override, create_user, session_factory):
    user = await create_user(email="zones-noprofile@example.com", username="zonesnoprofile")
    auth_override(user)

    zone = await _create_zone(session_factory, name="Red Team", short_name="REDTEAM")
    register = await client.post(f"/api/v1/zones/{zone.id}/register")
    assert register.status_code == 404
    assert "Participant profile not found" in register.json()["detail"]


@pytest.mark.asyncio
async def test_me_passes_returns_checked_in_timestamp(client, auth_override, create_user, session_factory):
    user = await create_user(email="zones-pass-checkin@example.com", username="zonespasscheckin")
    auth_override(user)
    create_me = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "zone-pass-checkin", "institution": "VIT-AP", "year": 3},
    )
    assert create_me.status_code == 201
    participant_id = uuid.UUID(create_me.json()["id"])

    zone = await _create_zone(session_factory, name="Blue Team", short_name="BLUETEAM")

    async with session_factory() as session:
        registration = ZoneRegistration(
            participant_id=participant_id,
            zone_id=zone.id,
            pass_code=f"code-{uuid4().hex}",
            is_active=True,
            checked_in_at=datetime.datetime.now(datetime.timezone.utc),
        )
        session.add(registration)
        await session.commit()

    passes = await client.get("/api/v1/me/passes")
    assert passes.status_code == 200
    assert len(passes.json()["passes"]) == 1
    assert passes.json()["passes"][0]["checkedInAt"] is not None


@pytest.mark.asyncio
async def test_concurrent_register_same_zone_is_idempotent(
    client, auth_override, create_user, session_factory
):
    user = await create_user(email="zones-race@example.com", username="zonesrace")
    auth_override(user)

    create_me = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "zone-race", "institution": "VIT-AP", "year": 2},
    )
    assert create_me.status_code == 201

    zone = await _create_zone(session_factory, name="Race Zone", short_name="RACEZONE")

    async def _register():
        return await client.post(f"/api/v1/zones/{zone.id}/register")

    r1, r2 = await asyncio.gather(_register(), _register())
    statuses = [r1.status_code, r2.status_code]
    assert set(statuses).issubset({200, 201})
    assert 201 in statuses

    regs = await client.get("/api/v1/me/registrations")
    assert regs.status_code == 200
    assert regs.json()["zoneIds"] == [str(zone.id)]

    async with session_factory() as session:
        count_stmt = (
            select(col(ZoneRegistration.id))
            .where(ZoneRegistration.zone_id == zone.id)
            .where(ZoneRegistration.is_active.is_(True))
        )
        rows = await session.exec(count_stmt)
        assert len(list(rows.all())) == 1
