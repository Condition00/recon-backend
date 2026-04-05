import pytest

from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTICIPANT


@pytest.mark.asyncio
async def test_apply_as_partner_and_fetch_my_profile(client, auth_override, create_user):
    user = await create_user(role_name=ROLE_PARTICIPANT, email="partnerapp@example.com", username="partnerapp")
    auth_override(user)

    response = await client.post(
        "/api/v1/partners/apply",
        json={
            "company_name": "Acme Security",
            "company_website": "https://acme.example",
            "contact_name": "Riley",
            "contact_email": "riley@acme.example",
            "sponsorship_type": "hybrid",
            "offering_writeup": "We provide CTF sponsorship and swag.",
            "incentives": [
                {
                    "title": "Prize Pool",
                    "incentive_type": "monetary",
                    "monetary_value": "5000.00",
                    "description": "Prize funding",
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"
    assert len(response.json()["incentives"]) == 1

    me_response = await client.get("/api/v1/partners/me")

    assert me_response.status_code == 200
    assert me_response.json()["company_name"] == "Acme Security"


@pytest.mark.asyncio
async def test_admin_can_review_partner_application(client, auth_override, create_user):
    applicant = await create_user(role_name=ROLE_PARTICIPANT, email="applicant@example.com", username="applicant")
    admin = await create_user(role_name=ROLE_ADMIN, email="partneradmin@example.com", username="partneradmin")

    auth_override(applicant)
    apply_response = await client.post(
        "/api/v1/partners/apply",
        json={
            "company_name": "Blue Team Labs",
            "company_website": "https://blueteam.example",
            "contact_name": "Jordan",
            "contact_email": "jordan@blueteam.example",
            "sponsorship_type": "monetary",
            "offering_writeup": "Funding challenges and booths.",
            "incentives": [],
        },
    )
    partner_id = apply_response.json()["id"]

    auth_override(admin)
    review_response = await client.post(
        f"/api/v1/partners/{partner_id}/review",
        json={"status": "approved", "review_notes": "Approved for event sponsorship."},
    )

    assert review_response.status_code == 200
    assert review_response.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_partner_asset_upload_requires_approved_application(client, auth_override, create_user):
    user = await create_user(role_name=ROLE_PARTICIPANT, email="assetwait@example.com", username="assetwait")
    auth_override(user)

    await client.post(
        "/api/v1/partners/apply",
        json={
            "company_name": "Pending Partner",
            "company_website": "https://pending.example",
            "contact_name": "Jamie",
            "contact_email": "jamie@pending.example",
            "sponsorship_type": "in_kind",
            "offering_writeup": "Offering event assets.",
            "incentives": [],
        },
    )

    asset_response = await client.post(
        "/api/v1/partners/me/assets",
        json={"file_key": "partners/logo.png", "asset_type": "logo", "label": "Logo"},
    )

    assert asset_response.status_code == 403
    assert asset_response.json()["detail"] == "Insufficient permissions"
