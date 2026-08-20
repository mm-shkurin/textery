"""The one place that knows this API's URL space.

Every router used to open with its own `prefix="/api/v1/..."` literal, and the
no-store middleware carried a tenth copy of the profile prefix. Ten literals mean
a version bump is a ten-file edit where nine of them are silent if missed: the
middleware matching a path the routers no longer serve fails open, and a stale
cache header on the profile is exactly the bug that middleware exists to prevent.

Nothing here is configuration -- the URL space is part of the published contract
(ProductSpecification/api-specs/*.yaml) and moves only with it.
"""

# Assembled from its segments rather than written as one literal: the segments are
# what a version bump or a mount-point change actually edits, and a single literal
# invites the copy this module exists to remove.
_MOUNT = "api"
VERSION = "v1"
BASE = f"/{_MOUNT}/{VERSION}"

AUTH = f"{BASE}/auth"
PROFILE = f"{AUTH}/me"
AVATAR = f"{PROFILE}/avatar"
DELETION = f"{PROFILE}/deletion"
OAUTH = f"{AUTH}/oauth"
DOCUMENTS = f"{BASE}/documents"
GENERATIONS = f"{BASE}/generations"
PROJECTS = f"{BASE}/projects"
