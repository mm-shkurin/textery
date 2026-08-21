> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — UI Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the visitor) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Landing URL | `/` |
| Valid topic | `Влияние искусственного интеллекта на образование` |
| Disabled-card marker | `скоро` pill rendered by `TypeCard` (`.soon-pill`) |
| Progress copy | chat panel (`data-testid="chat-panel"`) shows `ИИ пишет доклад` |
| Field limits | `requirements` ≤ 2000 characters, `extra_wishes` ≤ 2000 characters |

## 1. Disabled Document Types

### TC-01-UI-1.1 — Clicking a "coming soon" document type does nothing

| Field | Value |
|---|---|
| Description | A dimmed card that still fires its handler sends the visitor into a flow this story does not ship — the worst kind of dead end, because it looks like it worked. |
| Preconditions | The visitor has reached the generation form having chosen `доклад`; the not-yet-available types (`эссе`, `сочинение`, `реферат`) are visible with their `скоро` pills. |
| Test data | Cards `эссе`, `сочинение`, `реферат`; expected selection after the clicks: `доклад` |
| Steps | 1. Record the currently selected type.<br>2. Click the `эссе` card.<br>3. Click the `сочинение` card.<br>4. Click the `реферат` card.<br>5. Re-read the selected type and the current screen. |
| Expected result | None of the three clicks changes the screen, opens a modal, or issues a network request; the selected type is still `доклад` after all three; no error or toast appears. |
| Status | Not run |

## 2. Long-Running Pending State

### TC-01-UI-2.1 — The pending view keeps polling if generation takes longer than usual

| Field | Value |
|---|---|
| Description | A client-side timeout shorter than the server's own failure path shows the user an error for a generation that is still running and will succeed. |
| Preconditions | The chat/progress view is open; the poll endpoint returns `{"status": "in_progress", "content": null}` for 3 minutes, then `{"status": "completed", ...}`. |
| Test data | Stub keeps `in_progress` for `180 s`; typical wait is under 60 s; expected copy `ИИ пишет доклад` |
| Steps | 1. Open the chat/progress view for the stubbed generation.<br>2. Watch it for the full 3 minutes, counting poll requests.<br>3. Let the stub flip to `completed` and read the screen. |
| Expected result | The chat panel shows `ИИ пишет доклад` for the whole 3 minutes; polling continues throughout (requests keep arriving, no back-off to zero); no error state, no timeout message and no failed screen is shown at any point before the server itself reports `failed`; the completed content appears once the stub flips. |
| Status | Not run |

## 3. Field-Level Edge Cases

### TC-01-UI-3.1 — The requirements and extra wishes fields show a character counter near the limit

| Field | Value |
|---|---|
| Description | Without a visible counter, the 2000-character limit is discovered as a server `400` after the user has already written past it and cannot see by how much. |
| Preconditions | The visitor is on the generation form with a valid topic entered. |
| Test data | Paste 1900 characters into `requirements`, then type up to 2000; limit `2000` |
| Steps | 1. Paste 1900 characters into the requirements field.<br>2. Read the counter shown near the field.<br>3. Continue typing to exactly 2000 characters.<br>4. Repeat steps 1–3 for the extra wishes field. |
| Expected result | A counter is visible for both fields as the text approaches the limit, showing the used or remaining allowance against `2000` (e.g. `1900 / 2000`, then `2000 / 2000`); it updates as the visitor types; at the limit it makes clear no allowance remains. |
| Status | Not run |
