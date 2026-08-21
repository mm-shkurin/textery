"""Device type and operating system, read off a `User-Agent` header.

A **closed taxonomy**, and an unrecognized agent maps to `None` rather than to a
catch-all bucket (`14_AnalyticsEventTracking.md`, "device type / OS"). A bucket
named `OTHER` reads in a report as a real population; `NULL` reads as "we do not
know", which is the true statement and the one that keeps a broken parser
visible instead of quietly growing a category.

Substring matching over a small ordered table, not a UA-parsing library: the
taxonomy is five OS values and three device types, the ordering carries the only
subtlety there is (every Android agent also says `Linux`; every iPad in desktop
mode says `Macintosh`), and a dependency that ships a new database monthly would
make this classification drift on its own.
"""

from shared import limits

MOBILE = "MOBILE"
TABLET = "TABLET"
DESKTOP = "DESKTOP"

DEVICE_TYPES = (MOBILE, TABLET, DESKTOP)

ANDROID = "ANDROID"
IOS = "IOS"
WINDOWS = "WINDOWS"
MACOS = "MACOS"
LINUX = "LINUX"
OPERATING_SYSTEMS = (ANDROID, IOS, WINDOWS, MACOS, LINUX)

# Order matters and is the whole subtlety: Android agents also carry "Linux",
# and iOS agents also carry "like Mac OS X". First match wins, so the specific
# markers are listed before the general ones they contain.
_OS_MARKERS = (
    ("android", ANDROID),
    ("iphone", IOS),
    ("ipad", IOS),
    ("ipod", IOS),
    ("windows", WINDOWS),
    ("macintosh", MACOS),
    ("mac os x", MACOS),
    ("linux", LINUX),
)

_TABLET_MARKERS = ("ipad", "tablet", "kindle", "playbook")
_MOBILE_MARKERS = ("iphone", "ipod", "windows phone", "mobile")

MAX_USER_AGENT_LENGTH = limits.MAX_USER_AGENT_LENGTH


def device_type_of(user_agent: str | None) -> str | None:
    """`MOBILE`, `TABLET`, `DESKTOP`, or `None` for an agent we cannot read."""
    agent = _readable(user_agent)
    if agent is None:
        return None
    if any(marker in agent for marker in _TABLET_MARKERS):
        return TABLET
    # Checked after tablet, because an Android tablet's agent says "Android"
    # without "Mobile" while an Android phone's says both -- so the phone rule
    # has to be the narrower "mobile" marker rather than the platform name.
    if any(marker in agent for marker in _MOBILE_MARKERS):
        return MOBILE
    # Desktop is claimed only for an agent whose OS this module recognizes: a
    # crawler or a curl script names no platform and stays unknown rather than
    # inflating the desktop population.
    if any(marker in agent for marker, _ in _OS_MARKERS):
        return DESKTOP
    return None


def operating_system_of(user_agent: str | None) -> str | None:
    """The OS the agent claims, or `None` when it claims none this list knows."""
    agent = _readable(user_agent)
    if agent is None:
        return None
    for marker, operating_system in _OS_MARKERS:
        if marker in agent:
            return operating_system
    return None


def _readable(user_agent: str | None) -> str | None:
    """The agent lower-cased, or `None` when there is nothing to classify.

    Bounded before it is scanned: a header is caller-controlled, and an
    unbounded one turns eleven substring searches into an amplification the
    caller chooses the size of (Security §4.3). Past the bound the agent is not
    truncated-and-parsed -- a truncated agent classifies as whatever its prefix
    happens to say -- it is simply unreadable.
    """
    if not user_agent or len(user_agent) > MAX_USER_AGENT_LENGTH:
        return None
    return user_agent.lower()
