"""The error codes `POST /api/v1/analytics/events` may answer with.

The only new codes in this story. Both extended auth routes keep exactly the code
set they had (`endpoints.md`: "There is no new `error_code` anywhere in this story
outside `POST /api/v1/analytics/events`"), which is what makes the extension
additive rather than a contract change.

Named constants rather than literals at the raise sites: each one is also a key
in the rest layer's status map, and a typo'd literal there answers 400 for a
code that was meant to be 429 -- silently, since the default is 400.
"""

UNKNOWN_EVENT_NAME = "UNKNOWN_EVENT_NAME"
INVALID_VISITOR_ID = "INVALID_VISITOR_ID"
INVALID_OCCURRENCE_KEY = "INVALID_OCCURRENCE_KEY"
OCCURRENCE_KEY_CONFLICT = "OCCURRENCE_KEY_CONFLICT"
RATE_LIMITED = "RATE_LIMITED"
REQUEST_BODY_TOO_LARGE = "REQUEST_BODY_TOO_LARGE"

# Fixed, input-free messages. This is the product's only tokenless write, so its
# refusals reach anyone who can reach the internet -- echoing the rejected value
# back would make the endpoint a reflector (`03_Security_Tests.md` §3.3), and
# naming which of the two identifiers was malformed tells a prober nothing they
# could act on anyway.
UNKNOWN_EVENT_NAME_MESSAGE = "The event name is not one this endpoint accepts."
INVALID_VISITOR_ID_MESSAGE = "The visitor identifier is not a valid UUID."
INVALID_OCCURRENCE_KEY_MESSAGE = "The occurrence key is not a valid UUID."
OCCURRENCE_KEY_CONFLICT_MESSAGE = "This occurrence key was already used for a different event."
RATE_LIMITED_MESSAGE = "Too many events from this source. Try again shortly."
REQUEST_BODY_TOO_LARGE_MESSAGE = "The request body is too large."
# Shared with `analytics_payload.INVALID_PAYLOAD`, which owns the CODE: the
# domain refuses a payload it cannot store, and the route refuses a body that is
# not JSON at all. Both are "this body is not acceptable" to a client that can
# act on neither distinction, so they answer identically.
INVALID_PAYLOAD_MESSAGE = "The request body is not acceptable."
