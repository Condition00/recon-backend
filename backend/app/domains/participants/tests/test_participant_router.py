import pytest
import uuid

from app.domains.auth.models import ROLE_ADMIN
from app.domains.zones.models import Zone, ZoneRegistration


@pytest.mark.asyncio
async def test_create_and_get_my_participant_profile(client, auth_override, create_user):
    user = await create_user(email="participant1@example.com", username="participant1")
    auth_override(user)

    create_response = await client.post(
        "/api/v1/participants/me",
        json={
            "display_name": "ciphercat",
            "institution": "VIT-AP",
            "year": 3,
            "linkedin_acc": "https://linkedin.com/in/ciphercat",
            "github_acc": "https://github.com/ciphercat",
            "x_acc": "https://x.com/ciphercat",
            "phone": "9999999999",
            "profile_photo_file_key": "participants/ciphercat.png",
            "talent_visible": True,
            "talent_contact_shareable": False,
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["display_name"] == "ciphercat"
    assert create_response.json()["can_edit"] is True

    get_response = await client.get("/api/v1/participants/me")

    assert get_response.status_code == 200
    assert get_response.json()["institution"] == "VIT-AP"
    assert get_response.json()["phone"] == "9999999999"
    assert get_response.json()["is_self"] is True


@pytest.mark.asyncio
async def test_other_authenticated_user_sees_read_only_participant_view(client, auth_override, create_user):
    owner = await create_user(email="owner@example.com", username="owner")
    viewer = await create_user(email="viewer@example.com", username="viewer")
    auth_override(owner)

    create_response = await client.post(
        "/api/v1/participants/me",
        json={
            "display_name": "packetwitch",
            "institution": "VIT-AP",
            "year": 2,
            "linkedin_acc": "https://linkedin.com/in/packetwitch",
            "github_acc": "https://github.com/packetwitch",
            "x_acc": "https://x.com/packetwitch",
            "phone": "8888888888",
            "profile_photo_file_key": "participants/packetwitch.png",
            "talent_visible": False,
            "talent_contact_shareable": False,
        },
    )
    participant_id = create_response.json()["id"]

    auth_override(viewer)
    get_response = await client.get(f"/api/v1/participants/{participant_id}")

    assert get_response.status_code == 200
    assert get_response.json()["can_edit"] is False
    assert get_response.json()["linkedin_acc"] is None
    assert get_response.json()["phone"] is None
    assert get_response.json()["profile_photo_file_key"] is None


@pytest.mark.asyncio
async def test_toggle_talent_visibility_exposes_social_links_to_other_users(client, auth_override, create_user):
    owner = await create_user(email="owner2@example.com", username="owner2")
    viewer = await create_user(email="viewer2@example.com", username="viewer2")
    auth_override(owner)

    create_response = await client.post(
        "/api/v1/participants/me",
        json={
            "display_name": "shellfox",
            "institution": "VIT-AP",
            "year": 4,
            "github_acc": "https://github.com/shellfox",
            "phone": "7777777777",
        },
    )
    participant_id = create_response.json()["id"]

    toggle_response = await client.patch(
        "/api/v1/participants/me/talent-visibility",
        json={"talent_visible": True, "talent_contact_shareable": True},
    )

    assert toggle_response.status_code == 200
    assert toggle_response.json()["talent_visible"] is True

    auth_override(viewer)
    get_response = await client.get(f"/api/v1/participants/{participant_id}")

    assert get_response.status_code == 200
    assert get_response.json()["github_acc"] == "https://github.com/shellfox"
    assert get_response.json()["phone"] == "7777777777"


@pytest.mark.asyncio
async def test_admin_can_filter_participants_by_check_in_state(client, auth_override, create_user):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin@example.com", username="admin")
    attendee = await create_user(email="attendee@example.com", username="attendee")
    auth_override(attendee)

    create_response = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "zeroday", "institution": "VIT-AP", "year": 1},
    )
    participant_id = create_response.json()["id"]

    auth_override(admin)
    check_in_response = await client.post(f"/api/v1/participants/{participant_id}/checkin")

    assert check_in_response.status_code == 200
    assert check_in_response.json()["id"] == participant_id

    list_response = await client.get("/api/v1/participants?checked_in=true")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["display_name"] == "zeroday"


@pytest.mark.asyncio
async def test_participant_dashboard_aggregates_points_and_zone_checkins(
    client, auth_override, create_user, session_factory
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin-dash@example.com", username="admindash")
    user = await create_user(email="dash-user@example.com", username="dashuser")
    other = await create_user(email="dash-other@example.com", username="dashother")

    auth_override(user)
    me_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "dash-main", "institution": "VIT-AP", "year": 2},
    )
    assert me_resp.status_code == 201
    participant_id = uuid.UUID(me_resp.json()["id"])

    auth_override(other)
    other_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "dash-other-display", "institution": "VIT-AP", "year": 2},
    )
    assert other_resp.status_code == 201
    other_participant_id = uuid.UUID(other_resp.json()["id"])

    auth_override(admin)
    award_user = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 100,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "dash-award-user-1",
        },
    )
    award_other = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(other_participant_id),
            "amount": 150,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "dash-award-other-1",
        },
    )
    assert award_user.status_code == 201
    assert award_other.status_code == 201

    async with session_factory() as session:
        zone = Zone(
            name="Dashboard Zone",
            short_name="DASH",
            category="challenge",
            zone_type="booth",
            status="green",
            location="Hall D",
            points=30,
            color="#0EA5E9",
            tags=["ops"],
            is_active=True,
        )
        session.add(zone)
        await session.flush()
        reg = ZoneRegistration(
            participant_id=participant_id,
            zone_id=zone.id,
            pass_code="dash-pass-code",
            is_active=True,
            checked_in_at=zone.created_at,
        )
        session.add(reg)
        await session.commit()

    auth_override(user)
    dashboard = await client.get("/api/v1/me/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["displayName"] == "dash-main"
    assert body["registrationId"] == str(participant_id)
    assert body["pointsBalance"] == 100
    assert body["zonesCheckedInCount"] == 1
    assert len(body["checkedInZoneIds"]) == 1
    assert body["eventsRegisteredCount"] == 0
    assert body["leaderboardRank"] == 2


@pytest.mark.asyncio
async def test_participant_dashboard_alias_matches_portal_path(
    client, auth_override, create_user
):
    user = await create_user(email="dashboard-alias@example.com", username="dashboardalias")
    auth_override(user)

    create_response = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "dash-alias", "institution": "VIT-AP", "year": 2},
    )
    assert create_response.status_code == 201

    canonical = await client.get("/api/v1/me/dashboard")
    alias = await client.get("/api/v1/participants/me/dashboard")

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert alias.json() == canonical.json()
