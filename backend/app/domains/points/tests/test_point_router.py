import asyncio
import uuid

import pytest

from app.domains.auth.models import ROLE_ADMIN
from app.infrastructure.cache.service import keys
from app.main import app
from app.utils.deps import get_redis


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str | int | float] = {}
        self.sorted_sets: dict[str, dict[str, float]] = {}
        self.fail_publish = False
        self.fail_zcard = False
        self.fail_zrevrange = False
        self.fail_rename = False

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

    async def scan(self, cursor=0, match=None, count=200):
        return 0, []

    async def publish(self, channel: str, payload):
        if self.fail_publish:
            raise RuntimeError("simulated publish failure")
        return 0

    async def rename(self, source_key: str, destination_key: str):
        if self.fail_rename:
            raise RuntimeError("simulated rename failure")
        if source_key in self.sorted_sets:
            self.sorted_sets[destination_key] = self.sorted_sets.pop(source_key)
            return True
        if source_key in self.kv:
            self.kv[destination_key] = self.kv.pop(source_key)
            return True
        raise KeyError(source_key)

    async def zadd(self, key: str, mapping: dict[str, float]):
        bucket = self.sorted_sets.setdefault(key, {})
        bucket.update(mapping)
        return 1

    async def zincrby(self, key: str, increment: float, member: str):
        bucket = self.sorted_sets.setdefault(key, {})
        bucket[member] = float(bucket.get(member, 0.0)) + float(increment)
        return bucket[member]

    async def zrevrank(self, key: str, member: str):
        ranked = self._sorted_desc(key)
        for idx, (m, _) in enumerate(ranked):
            if m == member:
                return idx
        return None

    async def zscore(self, key: str, member: str):
        return self.sorted_sets.get(key, {}).get(member)

    async def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False):
        if self.fail_zrevrange:
            raise RuntimeError("simulated zrevrange failure")
        ranked = self._sorted_desc(key)
        if stop == -1:
            sliced = ranked[start:]
        else:
            sliced = ranked[start : stop + 1]
        if withscores:
            return [(m, s) for m, s in sliced]
        return [m for m, _ in sliced]

    async def zcard(self, key: str):
        if self.fail_zcard:
            raise RuntimeError("simulated zcard failure")
        return len(self.sorted_sets.get(key, {}))

    def _sorted_desc(self, key: str) -> list[tuple[str, float]]:
        bucket = self.sorted_sets.get(key, {})
        return sorted(bucket.items(), key=lambda row: (-row[1], row[0]))


@pytest.fixture
def redis_override():
    original = app.dependency_overrides.get(get_redis)
    fake = FakeRedis()

    async def _get_fake_redis():
        return fake

    app.dependency_overrides[get_redis] = _get_fake_redis
    yield fake

    if original is not None:
        app.dependency_overrides[get_redis] = original
    else:
        app.dependency_overrides.pop(get_redis, None)


async def _create_participant(client, auth_override, user, display_name: str) -> uuid.UUID:
    auth_override(user)
    response = await client.post(
        "/api/v1/participants/me",
        json={
            "display_name": display_name,
            "institution": "VIT-AP",
            "year": 2,
        },
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_award_points_and_get_my_balance(client, auth_override, create_user, redis_override):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_1@example.com", username="adminp1")
    player = await create_user(email="player_points_1@example.com", username="playerp1")
    participant_id = await _create_participant(client, auth_override, player, "ranker1")

    auth_override(admin)
    award_response = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 120,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "award-1",
        },
    )
    assert award_response.status_code == 201
    assert award_response.json()["resulting_balance"] == 120
    assert award_response.json()["transaction"]["resulting_balance"] == 120

    auth_override(player)
    me_response = await client.get("/api/v1/points/me")
    assert me_response.status_code == 200
    assert me_response.json()["balance"] == 120
    assert len(me_response.json()["recent_transactions"]) == 1


@pytest.mark.asyncio
async def test_spend_cannot_push_balance_negative(client, auth_override, create_user, redis_override):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_2@example.com", username="adminp2")
    player = await create_user(email="player_points_2@example.com", username="playerp2")
    participant_id = await _create_participant(client, auth_override, player, "ranker2")

    auth_override(admin)
    earn = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 50,
            "reason": "schedule.session.attend",
            "idempotency_key": "spend-guard-earn-1",
        },
    )
    assert earn.status_code == 201

    spend = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": -60,
            "reason": "shop.redeem",
            "idempotency_key": "spend-guard-spend-1",
        },
    )
    assert spend.status_code == 409
    assert spend.json()["detail"] == "Insufficient points balance"


@pytest.mark.asyncio
async def test_idempotency_key_prevents_duplicate_mutations(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_3@example.com", username="adminp3")
    player = await create_user(email="player_points_3@example.com", username="playerp3")
    participant_id = await _create_participant(client, auth_override, player, "ranker3")

    auth_override(admin)
    payload = {
        "participant_id": str(participant_id),
        "amount": 40,
        "reason": "zone.lock_hunt.complete",
        "idempotency_key": "stable-award-3",
    }

    first = await client.post("/api/v1/points/award", json=payload)
    second = await client.post("/api/v1/points/award", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["transaction"]["id"] == second.json()["transaction"]["id"]
    assert second.json()["resulting_balance"] == 40

    auth_override(player)
    me = await client.get("/api/v1/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 40
    assert len(me.json()["recent_transactions"]) == 1


@pytest.mark.asyncio
async def test_leaderboard_and_my_rank(client, auth_override, create_user, redis_override):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_4@example.com", username="adminp4")
    p1 = await create_user(email="player_points_4a@example.com", username="playerp4a")
    p2 = await create_user(email="player_points_4b@example.com", username="playerp4b")
    p3 = await create_user(email="player_points_4c@example.com", username="playerp4c")

    id1 = await _create_participant(client, auth_override, p1, "alpha")
    id2 = await _create_participant(client, auth_override, p2, "beta")
    id3 = await _create_participant(client, auth_override, p3, "gamma")

    auth_override(admin)
    await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id1),
            "amount": 90,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "board-1",
        },
    )
    await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id2),
            "amount": 60,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "board-2",
        },
    )
    await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id3),
            "amount": 30,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "board-3",
        },
    )

    auth_override(p1)
    leaderboard = await client.get("/api/v1/points/leaderboard?skip=0&limit=2")
    assert leaderboard.status_code == 200
    assert leaderboard.json()["total_ranked"] == 3
    assert leaderboard.json()["entries"][0]["display_name"] == "alpha"
    assert leaderboard.json()["entries"][1]["display_name"] == "beta"

    auth_override(p2)
    my_rank = await client.get("/api/v1/points/leaderboard/me")
    assert my_rank.status_code == 200
    assert my_rank.json()["rank"] == 2
    assert my_rank.json()["points"] == 60


@pytest.mark.asyncio
async def test_leaderboard_me_rank_matches_ordered_leaderboard_for_ties(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_6@example.com", username="adminp6")
    p1 = await create_user(email="player_points_6a@example.com", username="playerp6a")
    p2 = await create_user(email="player_points_6b@example.com", username="playerp6b")

    id1 = await _create_participant(client, auth_override, p1, "tied-a")
    id2 = await _create_participant(client, auth_override, p2, "tied-b")

    auth_override(admin)
    first_award = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id1),
            "amount": 100,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "tie-1",
        },
    )
    second_award = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id2),
            "amount": 100,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "tie-2",
        },
    )
    assert first_award.status_code == 201
    assert second_award.status_code == 201

    board = await client.get("/api/v1/points/leaderboard?skip=0&limit=10")
    assert board.status_code == 200
    entries = board.json()["entries"]
    assert len(entries) == 2

    by_participant = {entry["participant_id"]: entry["rank"] for entry in entries}
    assert by_participant[str(id1)] in (1, 2)
    assert by_participant[str(id2)] in (1, 2)
    assert by_participant[str(id1)] != by_participant[str(id2)]

    auth_override(p1)
    p1_rank = await client.get("/api/v1/points/leaderboard/me")
    auth_override(p2)
    p2_rank = await client.get("/api/v1/points/leaderboard/me")
    assert p1_rank.status_code == 200
    assert p2_rank.status_code == 200
    assert p1_rank.json()["rank"] == by_participant[str(id1)]
    assert p2_rank.json()["rank"] == by_participant[str(id2)]


@pytest.mark.asyncio
async def test_idempotency_key_conflict_for_different_payload_returns_409(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_7@example.com", username="adminp7")
    p1 = await create_user(email="player_points_7a@example.com", username="playerp7a")
    p2 = await create_user(email="player_points_7b@example.com", username="playerp7b")

    id1 = await _create_participant(client, auth_override, p1, "idem-a")
    id2 = await _create_participant(client, auth_override, p2, "idem-b")

    auth_override(admin)
    first = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id1),
            "amount": 25,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "shared-idem-key-1",
        },
    )
    assert first.status_code == 201

    conflicting = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(id2),
            "amount": 25,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "shared-idem-key-1",
        },
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["detail"] == "idempotency_key already exists for a different payload"


@pytest.mark.asyncio
async def test_admin_transactions_requires_admin_and_supports_filters(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_5@example.com", username="adminp5")
    player = await create_user(email="player_points_5@example.com", username="playerp5")
    participant_id = await _create_participant(client, auth_override, player, "delta")

    auth_override(admin)
    await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 70,
            "reason": "schedule.session.attend",
            "idempotency_key": "admin-tx-1",
        },
    )
    await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": -20,
            "reason": "shop.redeem",
            "idempotency_key": "admin-tx-2",
        },
    )

    auth_override(player)
    forbidden = await client.get("/api/v1/points/transactions")
    assert forbidden.status_code == 403

    auth_override(admin)
    filtered = await client.get("/api/v1/points/transactions?reason=shop.redeem")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["transactions"][0]["amount"] == -20


@pytest.mark.asyncio
async def test_award_requires_non_blank_idempotency_key(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_8@example.com", username="adminp8")
    player = await create_user(email="player_points_8@example.com", username="playerp8")
    participant_id = await _create_participant(client, auth_override, player, "idem-required")

    auth_override(admin)
    response = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 10,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "   ",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "idempotency_key must not be blank"


@pytest.mark.asyncio
async def test_idempotency_note_mismatch_returns_409(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_9@example.com", username="adminp9")
    player = await create_user(email="player_points_9@example.com", username="playerp9")
    participant_id = await _create_participant(client, auth_override, player, "idem-note")

    auth_override(admin)
    first = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 20,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "idem-note-1",
            "note": "note-a",
        },
    )
    assert first.status_code == 201

    conflicting = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 20,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "idem-note-1",
            "note": "note-b",
        },
    )
    assert conflicting.status_code == 409


@pytest.mark.asyncio
async def test_rebuild_leaderboard_cache_endpoint(client, auth_override, create_user, redis_override):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_10@example.com", username="adminp10")
    player = await create_user(email="player_points_10@example.com", username="playerp10")
    participant_id = await _create_participant(client, auth_override, player, "rebuild-me")

    auth_override(admin)
    award = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 33,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "rebuild-1",
        },
    )
    assert award.status_code == 201

    await redis_override.delete(keys.leaderboard())
    rebuild = await client.post("/api/v1/points/leaderboard/cache/rebuild")
    assert rebuild.status_code == 200
    assert rebuild.json()["total_ranked"] == 1
    assert await redis_override.zcard(keys.leaderboard()) == 1


@pytest.mark.asyncio
async def test_admin_transactions_rejects_naive_datetimes(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_11@example.com", username="adminp11")
    auth_override(admin)
    response = await client.get("/api/v1/points/transactions?start_at=2026-04-10T10:00:00")
    assert response.status_code == 400
    assert response.json()["detail"] == "start_at must be timezone-aware"


@pytest.mark.asyncio
async def test_outbox_retries_after_transient_publish_failure(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_13@example.com", username="adminp13")
    player = await create_user(email="player_points_13@example.com", username="playerp13")
    participant_id = await _create_participant(client, auth_override, player, "outbox-retry")

    auth_override(admin)
    redis_override.fail_publish = True
    first = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 25,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "outbox-fail-1",
        },
    )
    assert first.status_code == 201

    redis_override.fail_publish = False
    await asyncio.sleep(2.1)
    drain = await client.post("/api/v1/points/outbox/drain?limit=200")
    assert drain.status_code == 200
    assert drain.json()["sent"] >= 1


@pytest.mark.asyncio
async def test_award_requires_admin_role(client, auth_override, create_user, redis_override):
    player = await create_user(email="player_points_14@example.com", username="playerp14")
    participant_id = await _create_participant(client, auth_override, player, "award-admin-only")

    auth_override(player)
    response = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 10,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "non-admin-award-1",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_award_validation_and_missing_participant_paths(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_15@example.com", username="adminp15")
    player = await create_user(email="player_points_15@example.com", username="playerp15")
    participant_id = await _create_participant(client, auth_override, player, "validation-cases")

    auth_override(admin)
    zero_amount = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 0,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "zero-amount-1",
        },
    )
    assert zero_amount.status_code == 400
    assert zero_amount.json()["detail"] == "amount must be non-zero"

    bad_reason = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 10,
            "reason": "invalidreason",
            "idempotency_key": "bad-reason-1",
        },
    )
    assert bad_reason.status_code == 400
    assert "namespaced code" in bad_reason.json()["detail"]

    missing_participant = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(uuid.uuid4()),
            "amount": 10,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "missing-participant-1",
        },
    )
    assert missing_participant.status_code == 404
    assert missing_participant.json()["detail"] == "Participant not found"


@pytest.mark.asyncio
async def test_idempotency_conflict_when_same_key_used_by_different_admin_actor(
    client, auth_override, create_user, redis_override
):
    admin_a = await create_user(role_name=ROLE_ADMIN, email="admin_points_16a@example.com", username="adminp16a")
    admin_b = await create_user(role_name=ROLE_ADMIN, email="admin_points_16b@example.com", username="adminp16b")
    player = await create_user(email="player_points_16@example.com", username="playerp16")
    participant_id = await _create_participant(client, auth_override, player, "idem-admin-actor")

    payload = {
        "participant_id": str(participant_id),
        "amount": 15,
        "reason": "zone.lock_hunt.complete",
        "idempotency_key": "shared-idem-actor-1",
    }

    auth_override(admin_a)
    first = await client.post("/api/v1/points/award", json=payload)
    assert first.status_code == 201

    auth_override(admin_b)
    second = await client.post("/api/v1/points/award", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "idempotency_key already exists for a different payload"


@pytest.mark.asyncio
async def test_transactions_range_validation_paths(client, auth_override, create_user, redis_override):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_17@example.com", username="adminp17")
    auth_override(admin)

    bad_amount_range = await client.get("/api/v1/points/transactions?min_amount=100&max_amount=50")
    assert bad_amount_range.status_code == 400
    assert bad_amount_range.json()["detail"] == "min_amount cannot exceed max_amount"

    bad_time_range = await client.get(
        "/api/v1/points/transactions?start_at=2026-04-10T11:00:00Z&end_at=2026-04-10T10:00:00Z"
    )
    assert bad_time_range.status_code == 400
    assert bad_time_range.json()["detail"] == "start_at cannot exceed end_at"


@pytest.mark.asyncio
async def test_spend_exact_balance_to_zero_is_allowed(client, auth_override, create_user, redis_override):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_18@example.com", username="adminp18")
    player = await create_user(email="player_points_18@example.com", username="playerp18")
    participant_id = await _create_participant(client, auth_override, player, "exact-zero")

    auth_override(admin)
    earn = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 50,
            "reason": "schedule.session.attend",
            "idempotency_key": "exact-zero-earn-1",
        },
    )
    assert earn.status_code == 201

    spend = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": -50,
            "reason": "shop.redeem",
            "idempotency_key": "exact-zero-spend-1",
        },
    )
    assert spend.status_code == 201
    assert spend.json()["resulting_balance"] == 0

    auth_override(player)
    me = await client.get("/api/v1/points/me")
    assert me.status_code == 200
    assert me.json()["balance"] == 0


@pytest.mark.asyncio
async def test_outbox_drain_requires_admin_role(client, auth_override, create_user, redis_override):
    player = await create_user(email="player_points_19@example.com", username="playerp19")
    auth_override(player)
    response = await client.post("/api/v1/points/outbox/drain?limit=200")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_leaderboard_requires_authentication(client, create_user, redis_override):
    response = await client.get("/api/v1/points/leaderboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_leaderboard_falls_back_to_db_when_cache_errors(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_20@example.com", username="adminp20")
    player = await create_user(email="player_points_20@example.com", username="playerp20")
    participant_id = await _create_participant(client, auth_override, player, "cache-fallback")

    auth_override(admin)
    award = await client.post(
        "/api/v1/points/award",
        json={
            "participant_id": str(participant_id),
            "amount": 22,
            "reason": "zone.lock_hunt.complete",
            "idempotency_key": "cache-fallback-award-1",
        },
    )
    assert award.status_code == 201

    redis_override.fail_zcard = True
    auth_override(player)
    board = await client.get("/api/v1/points/leaderboard?skip=0&limit=10")
    assert board.status_code == 200
    assert any(entry["participant_id"] == str(participant_id) for entry in board.json()["entries"])


@pytest.mark.asyncio
async def test_rebuild_leaderboard_cache_handles_empty_dataset(
    client, auth_override, create_user, redis_override
):
    admin = await create_user(role_name=ROLE_ADMIN, email="admin_points_21@example.com", username="adminp21")
    auth_override(admin)
    rebuild = await client.post("/api/v1/points/leaderboard/cache/rebuild")
    assert rebuild.status_code == 200
    assert rebuild.json()["total_ranked"] == 0
