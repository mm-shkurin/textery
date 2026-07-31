"""The HTTP statuses the AI-edit scenarios name, in one place.

Scenario 1.1 and 1.2 both assert on `200`, `201`, `202` and `404`. They were spelled
as raw literals in one Statements file and as named constants in the other, which is
two spellings of one concept — a rename in either file would have left the other
silently disagreeing.
"""

OK_STATUS = 200
CREATED_STATUS = 201
ACCEPTED_STATUS = 202
NOT_FOUND_STATUS = 404
