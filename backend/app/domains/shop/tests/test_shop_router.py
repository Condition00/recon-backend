import uuid

import pytest

from app.domains.auth.models import ROLE_ADMIN


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
    redeem_resp = await client.post(f"/api/v1/shop/{item_id}/redeem")

    assert redeem_resp.status_code == 400
    assert "Insufficient points" in redeem_resp.json()["detail"]


@pytest.mark.asyncio
async def test_redeem_with_balance_succeeds(client, auth_override, create_user, session_factory):
    """Redeeming with sufficient points succeeds and deducts balance."""
    from app.domains.points.models import PointLedgerEntry
    from app.domains.participants.models import Participant

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
    async with session_factory() as session:
        entry = PointLedgerEntry(
            participant_id=participant_id,
            amount=1000,
            reason="test.seed",
        )
        session.add(entry)
        await session.commit()

    # Admin creates a shop item
    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Hoodie", "description": "Black hoodie", "point_cost": 300, "stock": 10},
    )
    item_id = create_resp.json()["id"]

    # Participant redeems
    auth_override(participant_user)
    redeem_resp = await client.post(f"/api/v1/shop/{item_id}/redeem")

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
    from app.domains.points.models import PointLedgerEntry

    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin7@example.com", username="shopadmin7")
    participant_user = await create_user(email="merch@example.com", username="merch")

    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "merchcollector", "institution": "VIT-AP", "year": 1},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])

    async with session_factory() as session:
        session.add(PointLedgerEntry(participant_id=participant_id, amount=500, reason="test.seed"))
        await session.commit()

    auth_override(admin)
    create_resp = await client.post(
        "/api/v1/shop/",
        json={"name": "Keychain", "description": "Metal keychain", "point_cost": 40, "stock": 50},
    )
    item_id = create_resp.json()["id"]

    auth_override(participant_user)
    redeem_resp = await client.post(f"/api/v1/shop/{item_id}/redeem")
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
    from app.domains.points.models import PointLedgerEntry

    admin = await create_user(role_name=ROLE_ADMIN, email="shopadmin8@example.com", username="shopadmin8")
    participant_user = await create_user(email="redeemer@example.com", username="redeemer")

    auth_override(participant_user)
    profile_resp = await client.post(
        "/api/v1/participants/me",
        json={"display_name": "serialredeemer", "institution": "VIT-AP", "year": 4},
    )
    participant_id = uuid.UUID(profile_resp.json()["id"])

    async with session_factory() as session:
        session.add(PointLedgerEntry(participant_id=participant_id, amount=2000, reason="test.seed"))
        await session.commit()

    auth_override(admin)
    item1 = await client.post("/api/v1/shop/", json={"name": "Pin", "description": "Enamel pin", "point_cost": 20, "stock": 100})
    item2 = await client.post("/api/v1/shop/", json={"name": "Pen", "description": "Ballpoint pen", "point_cost": 10, "stock": 200})

    auth_override(participant_user)
    r1 = await client.post(f"/api/v1/shop/{item1.json()['id']}/redeem")
    r2 = await client.post(f"/api/v1/shop/{item2.json()['id']}/redeem")

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
