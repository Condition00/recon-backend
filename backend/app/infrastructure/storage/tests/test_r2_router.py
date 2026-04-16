import uuid

import pytest

from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTNER, Role


class _FakeR2Service:
    def generate_upload_url(self, file_key: str, content_type: str) -> str:
        return f"https://storage.test/upload/{file_key}?content_type={content_type}"

    def generate_read_url(self, file_key: str) -> str:
        return f"https://storage.test/read/{file_key}"


@pytest.fixture(autouse=True)
def fake_r2_service(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.storage.controller.s3_controller.get_r2_service",
        lambda: _FakeR2Service(),
    )


@pytest.mark.asyncio
async def test_participant_private_read_url_requires_owner_or_visible_profile(
    client, auth_override, create_user
):
    owner = await create_user(email="photo-owner@example.com", username="photoowner")
    viewer = await create_user(email="photo-viewer@example.com", username="photoviewer")
    file_key = f"participants/{owner.id}/{uuid.uuid4().hex}.png"

    auth_override(owner)
    create_response = await client.post(
        "/api/v1/participants/me",
        json={
            "display_name": "redteamrose",
            "institution": "VIT-AP",
            "year": 2,
            "profile_photo_file_key": file_key,
            "talent_visible": False,
        },
    )
    assert create_response.status_code == 201

    auth_override(viewer)
    forbidden_response = await client.get("/api/v1/r2/read-url", params={"file_key": file_key})

    assert forbidden_response.status_code == 403

    auth_override(owner)
    toggle_response = await client.patch(
        "/api/v1/participants/me/talent-visibility",
        json={"talent_visible": True, "talent_contact_shareable": False},
    )
    assert toggle_response.status_code == 200

    auth_override(viewer)
    allowed_response = await client.get("/api/v1/r2/read-url", params={"file_key": file_key})

    assert allowed_response.status_code == 200
    assert allowed_response.json()["read_url"].endswith(file_key)


@pytest.mark.asyncio
async def test_partner_private_read_url_allows_owner_and_admin_only(client, auth_override, create_user):
    applicant = await create_user(email="storagepartner@example.com", username="storagepartner")
    admin = await create_user(role_name=ROLE_ADMIN, email="storageadmin@example.com", username="storageadmin")
    stranger = await create_user(email="storagestranger@example.com", username="storagestranger")

    auth_override(applicant)
    apply_response = await client.post(
        "/api/v1/partners/apply",
        json={
            "company_name": "Signal Forge",
            "company_website": "https://signalforge.example",
            "contact_name": "Morgan",
            "contact_email": "morgan@signalforge.example",
            "sponsorship_type": "hybrid",
            "offering_writeup": "Assets and booth support.",
            "incentives": [],
        },
    )
    assert apply_response.status_code == 201
    partner_id = apply_response.json()["id"]

    auth_override(admin)
    review_response = await client.post(
        f"/api/v1/partners/{partner_id}/review",
        json={"status": "approved", "review_notes": "Approved for storage test."},
    )
    assert review_response.status_code == 200

    applicant.role = Role(name=ROLE_PARTNER, description="Partner")
    file_key = f"partners/{partner_id}/{uuid.uuid4().hex}.png"

    auth_override(applicant)
    asset_response = await client.post(
        "/api/v1/partners/me/assets",
        json={"file_key": file_key, "asset_type": "logo", "label": "Brand Logo"},
    )
    assert asset_response.status_code == 201

    auth_override(stranger)
    forbidden_response = await client.get("/api/v1/r2/read-url", params={"file_key": file_key})
    assert forbidden_response.status_code == 403

    auth_override(applicant)
    owner_response = await client.get("/api/v1/r2/read-url", params={"file_key": file_key})
    assert owner_response.status_code == 200

    auth_override(admin)
    admin_response = await client.get("/api/v1/r2/read-url", params={"file_key": file_key})
    assert admin_response.status_code == 200
