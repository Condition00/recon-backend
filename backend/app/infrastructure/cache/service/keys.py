"""
Key namespace constants and builders for Redis.

All keys follow the pattern: recon:{domain}:{entity}:{id}
This prevents collisions and makes debugging/inspection trivial.
"""


def _build(*parts: str) -> str:
    """Join parts into a colon-separated Redis key."""
    return ":".join(parts)


# ── Prefix constants ──────────────────────────────────────────

PREFIX = "recon"


# ── Zone keys ─────────────────────────────────────────────────

def zone_capacity(zone_id: str) -> str:
    """Current occupancy counter for a zone.  Value: int."""
    return _build(PREFIX, "zones", "capacity", zone_id)


def zone_status(zone_id: str) -> str:
    """Traffic-light status for a zone.  Value: red | amber | green."""
    return _build(PREFIX, "zones", "status", zone_id)


def zone_queue(zone_id: str) -> str:
    """Queue position list for a zone.  Type: Redis List."""
    return _build(PREFIX, "zones", "queue", zone_id)


# ── Points / Leaderboard keys ────────────────────────────────

def leaderboard() -> str:
    """Global leaderboard.  Type: Redis Sorted Set (ZADD)."""
    return _build(PREFIX, "points", "leaderboard")


def participant_points(participant_id: str) -> str:
    """Cached total points for a single participant.  Value: int."""
    return _build(PREFIX, "points", "participant", participant_id)


def participant_points_last_activity(participant_id: str) -> str:
    """Cached last ledger activity timestamp (UTC epoch seconds)."""
    return _build(PREFIX, "points", "participant_last_activity", participant_id)


def leaderboard_rebuild_tmp() -> str:
    """Temporary leaderboard key used during atomic cache rebuild."""
    return _build(PREFIX, "points", "leaderboard_tmp")


# ── Announcements keys ───────────────────────────────────────

def announcements_latest() -> str:
    """Cached list of latest announcements.  Value: JSON string."""
    return _build(PREFIX, "announcements", "latest")


# ── Pub/Sub channels ─────────────────────────────────────────

def channel_zone_capacity(zone_id: str) -> str:
    """Pub/Sub channel for zone capacity updates."""
    return _build(PREFIX, "pubsub", "zones", "capacity", zone_id)


def channel_announcements() -> str:
    """Pub/Sub channel for live announcement broadcasts."""
    return _build(PREFIX, "pubsub", "announcements")


def channel_leaderboard() -> str:
    """Pub/Sub channel for leaderboard updates."""
    return _build(PREFIX, "pubsub", "leaderboard")


# ── Generic / custom keys ────────────────────────────────────

def custom(domain: str, entity: str, entity_id: str) -> str:
    """Build an ad-hoc namespaced key: recon:{domain}:{entity}:{id}."""
    return _build(PREFIX, domain, entity, entity_id)
