import uuid

import pytest

from app.domains.auth.models import ROLE_ADMIN
from app.domains.points.schemas import PointAwardCreate
from app.domains.points.service import award_points


async def _seed_points(session_factory, *, actor, participant_id: uuid.UUID, amount: int) -> None:
    async with session_factory() as session:
        payload = PointAwardCreate(
            participant_id=participant_id,
            amount=amount,
            reason="test.seed",
            idempotency_key=f"test.seed.{uuid.uuid4().hex}",
        )
        await award_points(session, payload=payload, actor=actor)
        await session.commit()


def _redeem_payload(key: str) -> dict[str, str]:
    return {"idempotency_key": key}


async def _create_participant(client, auth_override, user, display_name: str) -> uuid.UUID:
    auth_override(user)
    response = await client.post(
        "/api/v1/participants/me",
        json={"display_name": display_name, "institution": "VIT-AP", "year": 2},
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_admin_creates_shop_item(client, auth_override, create_user):
    """Admin can create a shop item and it appears in the catalogue."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin@example.com", username="shopadmin")
    auth_override(admin)

    create_resp = await client.post(
        "/api/v1/shop/",
        json={
            "name": "Recon Sticker Pack",
            "description": "A pack of 5 holographic cybersecurity stickers",
            "point_cost": 50,
            "stock": 100,
        },
    )

    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["name"] == "Recon Sticker Pack"
    assert data["point_cost"] == 50
    assert data["stock"] == 100
    assert data["remaining_stock"] == 100
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_participant_lists_active_shop_items(client, auth_override, create_user):
    """Participants can browse the active catalogue."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin2@example.com", username="shopadmin2")
    participant = await create_user(email="buyer@example.com", username="buyer")

    auth_override(admin)
    await client.post(
        "/api/v1/shop/",
        json={"name": "T-Shirt", "description": "Black tee", "point_cost": 200, "stock": 50},
    )
    await client.post(
        "/api/v1/shop/",
        json={"name": "Lanyard", "description": "Event lanyard", "point_cost": 30},
    )

    auth_override(participant)
    list_resp = await client.get("/api/v1/shop/")

    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2
    names = {i["name"] for i in items}
    assert "T-Shirt" in names
    assert "Lanyard" in names


@pytest.mark.asyncio
async def test_participant_gets_single_item(client, auth_override, create_user):
    """GET /shop/{id} returns item detail."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin3@example.com", username="shopadmin3")
    participant = await create_user(email="viewer@example.com", username="viewer")

    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Cap", "description": "Baseball cap", "point_cost": 80, "stock": 20},
    )
    item_id = create_resp.json()["id"]

    auth_override(participant)
    get_resp = await client.get(f"/api/v1/shop/{item_id}")

    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Cap"
    assert get_resp.json()["remaining_stock"] == 20


@pytest.mark.asyncio
async def test_admin_updates_shop_item(client, auth_override, create_user):
    """Admin can update item fields including toggling is_active."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin4@example.com", username="shopadmin4")
    auth_override(admin)

    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Mousepad", "description": "Large mousepad", "point_cost": 150, "stock": 10},
    )
    item_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/shop/{item_id}",
        json={"point_cost": 120, "is_active": False},
    )

    assert patch_resp.status_code == 200
    assert patch_resp.json()["point_cost"] == 120
    assert patch_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_redeem_insufficient_balance_returns_400(client, auth_override, create_user, session_factory):
    """Redeeming without enough points fails with 400."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin5@example.com", username="shopadmin5")
    participant_user = await create_user(email="broke@example.com", username="broke")

    # Create participant profile
    auth_override(participant_user)
    await client.post(
        "/api/v1/participants/me",
        json={"display_name": "brokeplayer", "institution": "VIT-AP", "year": 2},
    )

    # Admin creates shop item
    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Premium Badge", "description": "Gold badge", "point_cost": 500, "stock": 5},
    )
    item_id = create_resp.json()["id"]

    # Participant tries to redeem (0 balance)
    auth_override(participant_user)
    redeem_resp = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("redeem-insufficient-1"),
    )

    assert redeem_resp.status_code == 400
    assert "Insufficient points" in redeem_resp.json()["detail"]


@pytest.mark.asyncio
async def test_redeem_with_balance_succeeds(client, auth_override, create_user, session_factory):
    """Redeeming with sufficient points succeeds and deducts balance."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin6@example.com", username="shopadmin6")
    participant_user = await create_user(email="rich@example.com", username="rich")

    # Create participant profile
    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "richplayer", "institution": "VIT-AP", "year": 3},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])

    # Seed points for participant
    await _seed_points(
        session_factory,
        actor=admin,
        participant_id=participant_id,
        amount=1000,
    )

    # Admin creates a shop item
    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Hoodie", "description": "Black hoodie", "point_cost": 300, "stock": 10},
    )
    item_id = create_resp.json()["id"]

    # Participant redeems
    auth_override(participant_user)
    redeem_resp = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("redeem-success-1"),
    )

    assert redeem_resp.status_code == 200
    data = redeem_resp.json()
    assert data["item_name"] == "Hoodie"
    assert data["point_cost"] == 300
    assert data["fulfilled_at"] is None

    # Verify remaining stock decreased
    get_resp = await client.get(f"/api/v1/shop/{item_id}")
    assert get_resp.json()["remaining_stock"] == 9

    # Verify in redemption history
    history_resp = await client.get("/api/v1/shop/me/redemptions")
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["item_name"] == "Hoodie"


@pytest.mark.asyncio
async def test_admin_fulfills_redemption(client, auth_override, create_user, session_factory):
    """Admin can mark a redemption as fulfilled."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin7@example.com", username="shopadmin7")
    participant_user = await create_user(email="merch@example.com", username="merch")

    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "merchcollector", "institution": "VIT-AP", "year": 1},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])

    await _seed_points(
        session_factory,
        actor=admin,
        participant_id=participant_id,
        amount=500,
    )

    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Keychain", "description": "Metal keychain", "point_cost": 40, "stock": 50},
    )
    item_id = create_resp.json()["id"]

    auth_override(participant_user)
    redeem_resp = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("redeem-fulfill-1"),
    )
    redemption_id = redeem_resp.json()["id"]

    # Admin fulfills
    auth_override(admin)
    fulfill_resp = await client.patch(
        f"/api/v1/shop/redemptions/{redemption_id}/fulfill",
        json={"fulfillment_notes": "Handed over at booth A"},
    )

    assert fulfill_resp.status_code == 200
    assert fulfill_resp.json()["fulfilled_at"] is not None
    assert fulfill_resp.json()["fulfillment_notes"] == "Handed over at booth A"


@pytest.mark.asyncio
async def test_admin_lists_redemptions_with_filter(client, auth_override, create_user, session_factory):
    """Admin can list all redemptions and filter by fulfilled state."""
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin8@example.com", username="shopadmin8")
    participant_user = await create_user(email="redeemer@example.com", username="redeemer")

    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "serialredeemer", "institution": "VIT-AP", "year": 4},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])

    await _seed_points(
        session_factory,
        actor=admin,
        participant_id=participant_id,
        amount=2000,
    )

    auth_override(admin)
    item1 = await client.post("/api/v1/shop/", json={"name": "Pin", "description": "Enamel pin", "point_cost": 20, "stock": 100})
    item2 = await client.post("/api/v1/shop/", json={"name": "Pen", "description": "Ballpoint pen", "point_cost": 10, "stock": 200})

    auth_override(participant_user)
    r1 = await client.post(
        f"/api/v1/shop/{item1.json()['id']}/redeem",
        json=_redeem_payload("redeem-list-1"),
    )
    r2 = await client.post(
        f"/api/v1/shop/{item2.json()['id']}/redeem",
        json=_redeem_payload("redeem-list-2"),
    )

    # Fulfill one
    auth_override(admin)
    await client.patch(f"/api/v1/shop/redemptions/{r1.json()['id']}/fulfill", json={})

    # List all
    all_resp = await client.get("/api/v1/shop/redemptions")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 2

    # Filter unfulfilled
    unfulfilled_resp = await client.get("/api/v1/shop/redemptions?fulfilled=false")
    assert len(unfulfilled_resp.json()) == 1
    assert unfulfilled_resp.json()[0]["item_name"] == "Pen"

    # Filter fulfilled
    fulfilled_resp = await client.get("/api/v1/shop/redemptions?fulfilled=true")
    assert len(fulfilled_resp.json()) == 1
    assert fulfilled_resp.json()[0]["item_name"] == "Pin"


@pytest.mark.asyncio
async def test_redeem_idempotency_returns_same_redemption_without_double_spend(
    client, auth_override, create_user, session_factory
):
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin9@example.com", username="shopadmin9")
    participant_user = await create_user(email="idemshop@example.com", username="idemshop")

    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "idem-shopper", "institution": "VIT-AP", "year": 3},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])

    await _seed_points(session_factory, actor=admin, participant_id=participant_id, amount=400)

    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Patch", "description": "Velcro patch", "point_cost": 150, "stock": 5},
    )
    item_id = create_resp.json()["id"]

    auth_override(participant_user)
    first = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("redeem-idem-1"),
    )
    second = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("redeem-idem-1"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    points_me = await client.get("/api/v1/points/me")
    assert points_me.status_code == 200
    assert points_me.json()["balance"] == 250

    redemptions = await client.get("/api/v1/shop/me/redemptions")
    assert redemptions.status_code == 200
    assert len(redemptions.json()) == 1


@pytest.mark.asyncio
async def test_redeem_rejects_blank_idempotency_key(
    client, auth_override, create_user, session_factory
):
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin11@example.com", username="shopadmin11")
    participant_user = await create_user(email="blankidem@example.com", username="blankidem")

    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "blank-idem", "institution": "VIT-AP", "year": 2},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])
    await _seed_points(session_factory, actor=admin, participant_id=participant_id, amount=200)

    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Blank Key Item", "description": "test", "point_cost": 50, "stock": 5},
    )
    item_id = create_resp.json()["id"]

    auth_override(participant_user)
    redeem = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("   "),
    )
    assert redeem.status_code == 422


@pytest.mark.asyncio
async def test_redeem_immediately_keeps_points_rank_and_dashboard_consistent(
    client, auth_override, create_user, session_factory
):
    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin10@example.com", username="shopadmin10")
    buyer = await create_user(email="buyer-fast@example.com", username="buyerfast")
    rival = await create_user(email="rival-fast@example.com", username="rivalfast")

    buyer_participant_id = await _create_participant(client, auth_override, buyer, "buyer-fast")
    rival_participant_id = await _create_participant(client, auth_override, rival, "rival-fast")

    auth_override(admin)
    for participant_id, amount, idem in (
        (buyer_participant_id, 200, "redeem-consistency-seed-1"),
        (rival_participant_id, 180, "redeem-consistency-seed-2"),
    ):
        response = await client.post(
            "/api/v1/points/award",
            json={
                "participant_id": str(participant_id),
                "amount": amount,
                "reason": "zone.lock_hunt.complete",
                "idempotency_key": idem,
            },
        )
        assert response.status_code == 201

    create_item = await client.post(
        "/api/v1/shop/",
        json={"name": "Fast Badge", "description": "Instant redeem", "point_cost": 50, "stock": 10},
    )
    item_id = create_item.json()["id"]

    auth_override(buyer)
    redeem_resp = await client.post(
        f"/api/v1/shop/{item_id}/redeem",
        json=_redeem_payload("redeem-consistency-1"),
    )
    assert redeem_resp.status_code == 200

    points_me = await client.get("/api/v1/points/me")
    rank_me = await client.get("/api/v1/points/leaderboard/me")
    dashboard = await client.get("/api/v1/me/dashboard")

    assert points_me.status_code == 200
    assert rank_me.status_code == 200
    assert dashboard.status_code == 200
    assert points_me.json()["balance"] == 150
    assert rank_me.json()["points"] == 150
    assert dashboard.json()["pointsBalance"] == 150
    assert dashboard.json()["leaderboardRank"] == rank_me.json()["rank"]
