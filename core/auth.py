"""
core/auth.py — PIN verification and signed session-cookie helpers.

PIN storage: PBKDF2-HMAC-SHA256 (200 000 iterations), hex digest.
Cookie:      compact JSON payload + "|" + HMAC-SHA256 hex signature.
             Stores username, display name, and last-activity timestamp.
             The PIN or its hash is never placed in the cookie.
"""
import hashlib
import hmac as _hmac
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .config import BUSINESS_TZ, SESSION_TIMEOUT_MIN

# ── Public constants ──────────────────────────────────────────────────────────

COOKIE_NAME   = "qsr_session"
_PBKDF2_ITERS = 200_000
_REFRESH_SECS = 300  # slide the cookie at most once per 5 min of activity
_REFRESH_KEY  = "_auth_last_refresh"  # session_state key for the refresh guard


# ── Secrets accessors ─────────────────────────────────────────────────────────

def _salt() -> str:
    return str(st.secrets["auth"]["salt"])


def _stored_hashes() -> dict[str, str]:
    """Return {username: pin_hash} from secrets.toml [auth.users]."""
    return {k: str(v) for k, v in st.secrets["auth"]["users"].items()}


# ── PIN hashing (also imported by scripts/hash_pin.py) ───────────────────────

def hash_pin(pin: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256, 200 000 rounds. Returns lowercase hex digest."""
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), _PBKDF2_ITERS)
    return dk.hex()


def verify_pin(username: str, pin: str) -> bool:
    """True if *pin* matches the stored hash for *username*."""
    hashes = _stored_hashes()
    if username not in hashes:
        return False
    return _hmac.compare_digest(hash_pin(pin, _salt()), hashes[username])


# ── Cookie signing ────────────────────────────────────────────────────────────

def _sign(payload: str) -> str:
    return _hmac.new(_salt().encode(), payload.encode(), "sha256").hexdigest()


def make_cookie(username: str, display: str) -> str:
    """Build a signed cookie value with last-activity set to now (Saltillo TZ)."""
    now = datetime.now(ZoneInfo(BUSINESS_TZ)).strftime("%Y-%m-%d %H:%M:%S")
    payload = json.dumps({"u": username, "d": display, "la": now}, separators=(",", ":"))
    return payload + "|" + _sign(payload)


def parse_cookie(raw: str | None) -> dict | None:
    """
    Validate HMAC signature and check inactivity expiry.
    Returns {"username": ..., "display": ...} or None if invalid/expired.
    """
    if not raw or "|" not in raw:
        return None
    try:
        payload, sig = raw.rsplit("|", 1)
        if not _hmac.compare_digest(sig, _sign(payload)):
            return None
        data = json.loads(payload)
        last = datetime.strptime(data["la"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=ZoneInfo(BUSINESS_TZ)
        )
        elapsed = (datetime.now(ZoneInfo(BUSINESS_TZ)) - last).total_seconds()
        if elapsed > SESSION_TIMEOUT_MIN * 60:
            return None
        return {"username": data["u"], "display": data["d"]}
    except Exception:
        return None


# ── Sliding-window refresh guard ──────────────────────────────────────────────

def should_refresh_cookie() -> bool:
    """True if the cookie hasn't been refreshed in the last _REFRESH_SECS seconds."""
    ts = st.session_state.get(_REFRESH_KEY)
    if ts is None:
        return True
    elapsed = (datetime.now(ZoneInfo(BUSINESS_TZ)) - ts).total_seconds()
    return elapsed > _REFRESH_SECS


def mark_cookie_refreshed() -> None:
    """Record 'just refreshed' so we don't re-fire the cookie write this render."""
    st.session_state[_REFRESH_KEY] = datetime.now(ZoneInfo(BUSINESS_TZ))
