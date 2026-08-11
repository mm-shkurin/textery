# Story 19: AI chat editing of an existing document (SSE, revisions, rollback) — Frontend Progress

Bootstrapped from the test spec on 2026-08-08. Owns: Frontend Scenarios only. Backend,
Integration, Security, Load and Infrastructure scenarios live in `progress-backend.md` —
never edited from this session. Narrative, decisions and the Spec checklist live in
`progress.md`; `ProductSpecification/stories.md` is the cross-file rollup.

The UI test spec is split across three files (see the Decisions section of `progress.md`);
each file gets its own section below, and scenario numbers are unique within their file,
not across the story. 35 scenarios total (10 + 12 + 13).

Nothing is implemented yet: no AI-chat component, hook, API client or Selenium test exists
under `frontend/src` or `acceptance/tests/frontend`.

## Frontend Scenarios (02_UI_Tests.md)

### 0.1 A document that cannot be loaded blocks the chat panel with a way out
- [x] red-selenium — one test, three Statements assertions. Predicted and got
      `TimeoutException` in `_wait_for_visible` on `[data-testid='document-not-found']`.
      `/test-review` landed five fixes: the way-out link now asserts its `href` resolves to
      `{app_url}/documents` **and** that the link is a descendant of the blocker (caption-only
      would have passed a `<span>` or an `href="#"`); the chat-panel absence check moved to the
      prefix locator `[data-testid^='ai-chat']` because the exact `ai-chat-panel` testid exists
      nowhere and nothing forces scenario 1.1 to choose that name — the check was permanently
      vacuous; the `driver.get` justification was re-argued from the durable reason (a
      not-found document is unreachable by clicking your own documents list, by construction)
      rather than from a documents list that does not exist yet; and the skip reason now says
      the route itself is absent. Absence stays `find_elements`-based on purpose — a
      non-visibility check would pass a rendered-but-hidden editor.
      **Work unit closed 2026-08-09:** `/refactor` and both review passes ran over `3ec4798a`.
      Refactor migrated the two duplicated `_assert_absent` idioms
      (`manual_editor_statements.py:74`, `mode_modal_statements.py:41`) onto the base class and
      dropped a dead local in `chat_workspace_statements.py:72` that was failing ruff. Selenium
      did not execute — the stack is down; evidence is collection (35 collected, 0 errors),
      ruff clean, and import resolution.
      **Follow-ups surfaced (non-gating, act on them in `red-frontend`/`green-frontend`):**
      (a) `MANUAL_EDITOR = [data-testid='manual-editor']` is vacuous the same way the chat-panel
      locator was — that testid belongs to the Story 5/18 manual editor, and nothing forces the
      new `/documents/:id` editor to reuse it; widen it or pin it once green names its root.
      (b) In `assert_documents_list_link_is_offered` the descendant check searches inside the
      blocker while the text/href checks search the whole document, so a chrome link and a
      blocker `href="#"` can satisfy them jointly — assert a single match, or run text/href
      against the element found under `blocker`.
      (c) The route is only ever opened with a random UUID, so nothing proves the blocker is
      *conditional*: green can render it unconditionally and stay green. Owe a counter-case
      (own document opens the editor, blocker absent) and a foreign-document case.
      (d) The class is `@pytest.mark.skip` with no gate that fails on a lingering skip — verify
      the un-skip actually happened at `green-selenium`.
      (e) Pre-existing, out of unit: 10 `unused import: pytest` ruff errors across 9 frontend
      and 1 backend test files; `LOADING_SKELETON`/`SOON_BADGE` use class-based selectors,
      which `frontend-rules.md:45` forbids.
      **Harness quirk:** `pytest -m frontend` defaults `app_url` to port 5173 while
      `FRONTEND_PORT=80` lives in `infra/.env` — export it first (`set -a; . ../infra/.env`),
      or the run dies with `ERR_CONNECTION_REFUSED`, which looks nothing like a red test.
- [x] red-frontend — two cases, one branch, in
      `frontend/src/features/aiChat/components/__tests__/DocumentEditorPage.notFound.test.tsx`.
      Predicted and got `TestingLibraryElementError: Unable to find an element by:
      [data-testid="document-not-found"]` on the failure case and `AssertionError: expected null
      not to be null` on the success case. The success case is what closes follow-up (c): an
      unconditional blocker now fails. `/test-review` landed six fixes — the biggest is that
      `manual-editor` had no positive counterpart anywhere for this route, so the absence check
      was vacuous exactly as follow-up (a) said; the success case now *requires* that testid to
      render, proving the same constant live in one branch and absent in the other. The chat
      locators are deliberately asymmetric: absence uses the prefix `[data-testid^='ai-chat']`
      (un-slippable), presence uses the exact `ai-chat-panel` — `not.toBeNull()` on a prefix is
      satisfied by any incidental wrapper. Both load calls pinned with
      `toHaveBeenCalledExactlyOnceWith` (an unpinned count passed a component that refetches on
      every render), and the way-out link asserts `tagName === 'A'` before its href (a
      `<span href>` navigates nowhere). `version: 3` is left unasserted on purpose — no UI
      scenario shows it; it travels with edit submissions in scenarios 3.x.
      **Green-frontend scope is three things, not one:** the `/documents/:documentId` route in
      `app/App.tsx`, the blocker, and a `/documents` list for the way-out link to target.
      **Harness note:** `frontend/node_modules` was absent; `npm ci` (273 packages, ~2 min) is
      needed before the suite runs — an empty `node_modules` looks like a broken config.
      `/refactor` found NO ACTION (141/7/28 lines, oxlint and tsc clean); no refactor commit.
      It flagged two deferrals for `red-frontend-api`: `loadEditorDocument`/`EditorDocument`
      duplicates `getDocument`/`GetDocumentResult` in `generation/api/documentApi.ts` (same
      shape, same endpoint) — do not land a second document loader without deciding that; and
      `DocumentNotFoundError` belongs beside `VersionConflictError`/`SessionExpiredError` in
      `shared/api/send.ts` once something actually throws it.
      **Review-pass follow-ups for `green-frontend` (verified where noted):**
      (f) **The coverage gate is red on `f1e3f306` — confirmed, `npm run test:coverage` exits 1.**
      Both stubs sit at 0% statements against a 60% per-file floor. This is inherent to a RED
      phase that lands stubs behind a skipped test; green closes it by un-skipping. Do not
      lower the floor or add an exclude. Any CI job running `test:coverage` fails here, and the
      failure looks like a coverage problem rather than an in-flight red phase.
      (g) The success case asserts a live `ai-chat-panel`, which is scenario 1.1's component —
      so green's scope is *four* things, not the three listed above. An empty placeholder div
      named `ai-chat-panel` would satisfy it and reintroduce exactly the incidental-wrapper pass
      the asymmetric locators were chosen to prevent. Decide this before green starts.
      (h) Every rejection currently maps to the blocker. The minimal code passing both cases is
      `try { … } catch { setNotFound(true) }`, which shows "Документ не найден" on a 500, on a
      401, on a dropped connection — and invites the user to re-create a document that exists.
      Owe a case rejecting with a generic `Error` and asserting the blocker is **absent**.
      (i) Both suites assert the way-out link's `href`, neither ever clicks it. `App.tsx:16`
      routes `/*` to `DocumentGenerationFlow`, so `/documents` resolves today and green can ship
      without ever building the list. Owe an App-level case that clicks the link and asserts the
      documents list — not the generation flow — renders.
      (j) `/documents/:documentId` is currently swallowed by that same `/*` catch-all, which
      renders `ManualEditor` — already carrying `data-testid="manual-editor"`, the testid this
      test reuses for the new page root. Sibling routes never mount together so `getByTestId`
      stays unambiguous, but `src/__tests__/App.test.tsx:131,146,150` assert on that testid at
      app level; composing the two editors would break them.
      (k) `toHaveBeenCalledExactlyOnceWith` is proved outside StrictMode while `main.tsx` wraps
      `App` in it, so a naive `useEffect` fetch passes here and double-invokes in dev. The repo
      already has `generation/hooks/__tests__/useDocumentInit.strictMode.test.tsx` for this.
      (l) Nothing fails on a permanently-skipped spec. Green's verification must report these
      two cases as *passed*, not merely "suite green".
- [x] green-frontend — 507 passed / 0 skipped (was 505/2); both notFound cases report *passed*,
      closing follow-up (l). Coverage gate exits 0 again — follow-up (f) resolved with no floor
      lowered and no exclude added.
      `/documents` and `/documents/:documentId` now sit **above** the `/*` catch-all in
      `app/App.tsx`, which was swallowing both into `DocumentGenerationFlow` (follow-up j).
      The load lives in `features/aiChat/hooks/useEditorDocument.ts` with four states —
      `loading | ready | not-found | failed`. Only `error instanceof DocumentNotFoundError`
      reaches `not-found`; every other rejection lands on `failed`, which renders a separate
      "Не удалось загрузить документ" screen. That is follow-up (h) honored in production code,
      but **the test that would keep it honest is still owed** — no case yet rejects with a
      generic `Error` and asserts the blocker is absent, so a later regression to
      `catch { setNotFound(true) }` would pass the suite.
      StrictMode double-fetch (follow-up k) is guarded by a `requestedIdRef` placed **before**
      the fetch. Worth knowing: the existing `useDocumentInit` cancel-flag pattern does not work
      here — it suppresses the second `setState` but not the second fetch, which is exactly what
      `toHaveBeenCalledExactlyOnceWith` measures.
      Follow-up (g) resolved by building `AiChatPanel` honestly rather than as a placeholder
      div: heading plus a notice that chat editing appears here, deliberately **not** the
      mockup's "напишите, что нужно изменить" opener, which would invite typing into a composer
      scenario 1.1 has not built.
      Follow-up (i): `/documents` is now a real route — `DocumentsListRoute` exported from
      `features/history/components/HistoryPage.tsx`, reusing the existing "Мои документы" screen
      and only giving it a URL. It lived in its own `app/DocumentsListRoute.tsx` first, which sat
      at 0% statements and failed the per-file floor; inlining it into `App.tsx` dropped App to
      50%. **The click-through test is still owed** — both suites still only assert the link's
      `href`.
      `EditorDocumentView` renders the document through a read-only Tiptap `EditorContent`
      (`immediatelyRender: true`, so the text is in the first commit) rather than
      `dangerouslySetInnerHTML` — the HTML goes through Tiptap's schema.
      Only test change: removing `describe.skip`. The Selenium test stays skipped for
      `green-selenium`.
      `/refactor` landed two behavior-preserving changes over `70ef65eb`: `EditorDocumentState`
      became a discriminated union (the old shape allowed `status:'ready'` with a null document,
      which produced an unreachable `|| !document` guard in the page), and `LOAD_FAILED_MESSAGE`
      moved from the hook to the component that renders it — it collided by name, with different
      wording, with the constant in `generation/hooks/useDocumentInit.ts`.
      **Pre-existing, out of unit:** `npm run format:check` flags
      `DocumentEditorPage.notFound.test.tsx` — already red at `70ef65eb`, i.e. landed by the RED
      phase.
      **Review-pass follow-ups for `red-frontend-api` / later units (both passes CONCERNS):**
      (m) **Both new routes bypass the auth gate.** Every other authenticated screen sits under
      `DocumentGenerationFlow`, which redirects on `!isAuthenticated` (`DocumentGenerationFlow.tsx:58`
      states the invariant). `/documents` and `/documents/:documentId` are registered as bare routes,
      so a signed-out visitor gets "Мои работы" with owner-scoped calls, or the editor. Owe a
      signed-out case per route.
      (n) **An expired session is reported as a network problem.** `SessionExpiredError` exists
      precisely so callers can separate it (`useDocumentSave.ts:21-34`, `useGeneration.ts:87`,
      `shared/api/send.ts:53` all carve it out); this hook folds it into `failed`, whose copy says
      "Проверьте соединение и обновите страницу" — the same mislabeling this unit argued against,
      displaced one branch over.
      (o) **The `failed` screen is the dead end the blocker refuses to be** — no heading, no link,
      while `DocumentNotFoundBlocker` ships a `Link` on the stated rule that a blocked screen needs
      a navigable exit.
      (p) **`loading` and `failed` have no test**, so the `instanceof` discrimination can regress to
      a bare catch with the suite green. This is follow-up from green's own note, now doubled by both
      passes: reject with a plain `Error`, assert `document-load-failed` present and
      `document-not-found` absent.
      (q) **Route wiring is untested.** The unit test mounts the page in its own `MemoryRouter` and
      never touches `App.tsx`; the acceptance test is still skipped with a now-stale reason. Nothing
      resolves the blocker's `/documents` href against a real route table — the way out could point
      at a 404 and both cases still pass.
      (r) **`/documents` is live ahead of its API**: `loadEditorDocument` is still the RED stub that
      unconditionally throws, so every row click from the list lands on the `failed` screen. Either
      sequence `red/green-frontend-api` before exposing the list route, or pin the navigation.
      (s) Remote: `EditorDocumentView` calls `useEditor({ content })` once — a later `content` change
      (scenarios 3.x, AI-applied edits) will not update the editor.
- [x] red-frontend-api — five cases over `loadEditorDocument` in
      `frontend/src/features/aiChat/api/__tests__/editorDocumentApi.test.ts`. Predicted and got all
      five failing out of the stub's unconditional `throw new Error('Not implemented: …')` — the
      happy path as an unexpected rejection, the 404/foreign/session cases as `expected Error: Not
      implemented… to be an instance of DocumentNotFoundError|SessionExpiredError`, and the 500 case
      on its message assertion (`expected 'Not implemented…' to be 'Внутренняя ошибка'`), since its
      `not.toBeInstanceOf` half passes trivially.
      **The duplication deferral is decided: option (b), the 404 branch lands in `shared/api/send.ts`.**
      Option (a) — a thin wrapper over `getDocument` — is not available: `send` flattens every
      non-401/409 refusal into `new Error(describeFailure(...))`, so by the time `getDocument` returns
      a 404 and a 500 are the same generic `Error` and no wrapper can recover the distinction without
      re-implementing the token attach, the 401 renew-and-replay and the refusal describing — the
      second copy `send.ts`'s own header says gets the carve-out wrong. The branch keys on
      `error_code: 'NOT_FOUND'`, not the bare status, for the same reason as the 409;
      `DocumentNotFoundError` moves to `send.ts` and `editorDocumentApi` re-exports it so the hook's
      and the component test's import path stays valid.
      Follow-up (n) is now pinned by a case: the expired session survives as `SessionExpiredError`,
      and the 500 case is what fails a `catch → not-found` implementation.
      `/test-review` landed nine fixes. The load-bearing ones: the 404 wire body was the *same*
      Russian string the error class hardcodes, so both 404 cases passed for an implementation that
      merely echoes `body.message` into a plain `Error` — the wire now says `'Document not found'`
      while the assertion is on the class constant, which proves the class was constructed. The URL
      matcher was `toContain`, which passed for `/api/v1/documents/doc-1/versions`; the verb was
      unpinned, so the happy path passed for a `POST` that creates a document on every page open;
      the foreign-document case never checked the id reached the wire and was byte-identical to the
      404 one; the session case never verified the renew-and-replay its own comment claims (now
      pinned to `[DOCUMENT_URL, REFRESH_URL]`); and `stubFetch` had no default implementation, so a
      spurious extra call died as an unreadable TypeError inside `httpClient` instead of a named
      failure. Two vacuous negatives (`not.toBeInstanceOf`) were replaced by strict `name`/`message`
      assertions — on the 500 case, `name === 'Error'` also rules out `VersionConflictError`.
      **Note for green:** the file is 199 of its 200 permitted lines — a sixth case needs a split.
      `/refactor` extracted the four-times-repeated `toBeInstanceOf`/`name`/`message` triple into
      `expectErrorIdentity`, which pushed the file to 206 lines and made the split mandatory: the
      test-support layer moved to `__tests__/editorDocumentApiFixtures.ts` (166 + 56 lines), taking
      the support seam rather than splitting by case, which would have duplicated the `describe.skip`
      marker. It also promoted `rejectionOf` from `auth/api/__tests__/loginApiTestUtils.ts` to
      `src/test/rejectionOf.ts` and rewired six files: the inline `promise.catch(e => e)` idiom
      yields the **resolved** value when nothing throws, so a non-rejecting implementation reported
      "expected `{documentId: …}` to be an instance of DocumentNotFoundError" instead of naming the
      real defect. 507 passed / 5 skipped, unchanged; tsc clean.
      **Review-pass follow-ups — both passes CONCERNS, and they agree on the same root: `send.ts` is
      shared by four features, while every case here exercises one caller.** Resolve (t) BEFORE
      writing green — it may change the design decision recorded above.
      (t) **`error_code: 'NOT_FOUND'` is not endpoint-scoped.** `endpoints.md` says all seven
      endpoints share one 404 body — which is exactly why a branch keyed on the code alone also
      fires for `GET /generations/{id}`, the history lists and `PUT /documents/{id}`. Callers then
      receive a type they never narrow: `useDocumentSave.ts` falls through
      `SessionExpiredError`/`VersionConflictError` to "Повторите — текст пока только в редакторе",
      advice that can never succeed while the only copy of the text is the tab; `useGeneration.ts:89`
      and `useHistoryList.ts:52` render `error.message` straight through, so a missing *generation*
      says "Документ не найден". This is the 409 comment's own lesson one axis over: the code is
      unambiguous, the error class is not endpoint-neutral. Owe either a scoping mechanism or a case
      pinning that a `NOT_FOUND` 404 on a non-document endpoint keeps its caller's fallback and
      `name === 'Error'`.
      (u) **A 404 with no `error_code` routes the scenario's own Given to `failed`.** `performRequest`
      substitutes `{}` when `res.json()` throws (proxy HTML, empty body), and the live endpoint has
      historically answered `{detail: …}`. Under strict code-keying such a 404 becomes a generic
      `Error` and `useEditorDocument` shows "не удалось загрузить" for a document that is genuinely
      absent. Fail-safe may be the right trade — but nothing states or pins it, so green can widen to
      bare `status === 404` and stay green either way.
      (v) **The only pre-existing 404 case is code-blind.**
      `generation/api/__tests__/documentApi.test.ts:179` stubs `{ detail: … }` with no `error_code`
      and asserts with `rejects.toThrow('Документ не найден')`, which passes for
      `DocumentNotFoundError` too — so it cannot catch `getDocument`'s error type changing under
      `useDocumentInit.ts:71`. Owe a sibling case carrying `error_code`.
      (w) No case in `ManualEditor.saveFailureKinds.test.tsx` asserts the banner when `saveDocument`
      rejects with `DocumentNotFoundError`.
- [x] green-frontend-api — 512 passed / 0 skipped (was 507/5); all five cases report *passed*
      individually. tsc clean.
      **Follow-up (t) changed the design decision before green started: the NOT_FOUND branch is
      OPT-IN per call, not the unconditional branch the 409 mapping is.** `send` grew a fourth
      parameter `refusals: RefusalMapping = {}` and raises `DocumentNotFoundError` only when
      `refusals.notFound` is set; `getDocument` forwards the flag with the same default, so
      `saveDocument`'s conflict-refetch, generation polling and both history lists are byte-for-byte
      unchanged and their tests stayed green untouched. That closes (t) in production code — but the
      test that would keep it honest is **owed**: nothing yet asserts that a `NOT_FOUND` 404 on a
      non-document endpoint still gets its caller's fallback text, so a later widening to a global
      branch would pass the suite. (w) is likewise still open for the same reason.
      (u) is honored and commented: the branch keys on `error_code`, so a 404 with no code (proxy
      HTML, empty body — `performRequest` substitutes `{}`) stays a generic described `Error`. The
      argument for that trade is that the endpoint's own 404 always carries the code, so what falls
      through is a request that never reached the API — and telling that user "документа не
      существует" would send them to delete work that is fine. Still unpinned by a case.
      (r) is closed: `loadEditorDocument` no longer throws unconditionally, so `/documents` stops
      leading every row click to the failure screen.
      `DocumentNotFoundError` moved to `send.ts`; `editorDocumentApi` re-exports rather than
      re-declares it — a second structurally identical class is a second identity and `instanceof`
      would silently go false. `EditorDocument` drops `status`: the editor renders `content` and
      sends `version` back, and nothing in the feature branches on status.
      Only test change: removing `describe.skip`.
      `/refactor` extracted `refusedWith(error, status, code)` — both mapped-refusal guards spelled
      out the same three-conjunct shape, and the opt-in conjunct was buried inside a five-line
      boolean chain. 512 passed, unchanged; tsc clean; `send.ts` 113→111 lines.
      **Review-pass follow-ups (both CONCERNS), for the next units:**
      (x) **The one test that looks like the opt-in guard is a decoy — the property has ZERO
      coverage, not thin coverage.** `generation/api/__tests__/documentApi.test.ts:180-191` stubs a
      404 whose body carries no `error_code`, so the new branch can never fire for it *even if
      `refusals.notFound` were deleted*; and it asserts `rejects.toThrow('Документ не найден')`,
      which is byte-identical to `DocumentNotFoundError`'s own message, so a thrown
      `DocumentNotFoundError` satisfies it too. Dropping the `refusals` parameter entirely would
      leave the whole suite green. This supersedes the softer "still owed" note above: owe a case
      where a caller that passed no `refusals` meets `404 {error_code:'NOT_FOUND'}` and the rejection
      is pinned `name === 'Error'` and NOT `instanceof DocumentNotFoundError`. There is no `send`
      test file at all — `shared/api/__tests__/` holds only `httpClient` tests.
      (y) **The flag is named generically and maps to a document-specific error, in a module three
      features share.** The next caller reading `notFound: true` as "give me a typed 404" — a
      generation poll, a history detail — gets "Документ не найден", the exact sentence this design
      exists to prevent. Either rename to `documentNotFound` or let the mapping carry the error type
      instead of a boolean.
      (z) **`aiChat` now imports `generation`.** `editorDocumentApi.ts:7` pulls `getDocument` from a
      peer feature, which `frontend-rules.md` "Feature Structure" does not allow — `send.ts`
      documents its auth import as an explicit layering carve-out, and this has no equivalent. Two
      live consequences: the editor is bound to generation's wire contract (`GetDocumentResult.status`
      is required), and any reorganisation of the generation feature breaks the editor route. The
      shared read belongs in `shared/api` or a `documents` feature.
      (aa) **`saveDocument`'s 409-recovery refetch reports a load failure during a save.**
      `documentApi.ts:111` calls `getDocument(documentId)` on the default `{}`, so a document deleted
      in another tab makes the save path say "Не удалось загрузить документ" — a load error for an
      action the user never took — and offer a retry that can never succeed while the only copy of
      the text is the tab. Distinct from (t): wrong *operation's* fallback, not wrong type. No case
      in `documentApi.conflict.test.ts` covers a 404 on the refetch leg.
      (ab) **A stale stored document id strands the user at app entry.**
      `generation/hooks/useDocumentInit.ts:58` calls `getDocument(existingDocumentId)` on the default
      and funnels every failure into `onError`, so a definitively-gone id gives a permanently
      un-savable editor that a refresh cannot fix. This commit is what made the distinction available
      (`{ notFound: true }`) and left that call site not taking it — falling through to the
      `createDocument` arm is the recovery that unsticks the user.
- [x] align-design — aligned to `mockups/desktop/01-editor-chat.html` + `editor.css`: the workspace
      became the mockup's grid (`1fr 380px`), the document a 760px card in a scrolling `.ac-doc-wrap`
      pane, and the chat a full-height column divided by a rule rather than a floating card with a
      gap. The chat heading gained the mockup's accent tile (inline SVG — this app has no icon
      package, and it is `aria-hidden` decoration the heading already names).
      **Geometry is copied, colour is not.** The mockup ships its own `theme.css` palette
      (`#1552f0` accent, `#f2f4f7` page) while this app's live tokens are the blue UI-Kit set every
      other screen renders; taking the literals would give story 19 a second accent colour on a
      screen that sits beside story 18's editor. Stated at the top of the stylesheet.
      `/design-review`: **PASS on the placeholder gate** — none of the mockup's payload (`415 слов ·
      версия 7`, `История ИИ`, the `14:02` timestamps, `Осталось правок сегодня: 17 из 20`,
      `7 версий`) reached the component, and the panel still declines the mockup's composer opener.
      Three of its geometry findings were fixed in this unit: `min-height` was `calc(100vh - 150px)`
      copied verbatim, but the 150px is the mockup's topbar + crumbs + format bar and this route
      renders none of that chrome — the workspace stopped 150px short of the viewport with the chat
      column's border ending in mid-air; `.ac-doc-wrap` regained `position: relative` (scenarios
      2/4/5 anchor the state ribbon and the frozen overlay in that pane); and the card shadow became
      a real `--shadow-card` token in `index.css` instead of the file's only raw colour literal.
      **Both review passes then found a real defect in the shipped geometry, fixed in the same work
      unit's second commit:** `min-height: 100vh` does not bound anything. A min-height grid row is
      auto-sized, so it grows to the document, `.ac-doc-wrap`'s `overflow: auto` never has a bound to
      scroll against, the *page* scrolls instead, and `align-items: stretch` makes the chat column as
      tall as the document — on anything longer than a screen the panel's heading scrolls away and
      the composer scenario 1.1 pins to its bottom would land thousands of pixels down. The mockup
      gets away with `min-height` only because its document is a short stub. Now `height: 100vh` with
      `min-height: 0` on both children (a grid item's automatic minimum is its content size, which
      would re-defeat the bound), and the stacked ≤900px case reverts to `height: auto` because two
      panes cannot share one viewport height. That also answers (ae): the composer's pinning needs
      the bounded column, not a `flex: 1` inside an unbounded one.
      (ad) is closed too — the document card regained a `1px solid var(--border-subtle)` border. The
      mockup separates card from ground with the 4%-alpha shadow alone, tuned against its own
      `#f7f8fa`; this app's ground resolves to `--blue-50`, so a white card separated by 4% of black
      is below the 3:1 non-text floor and reads as a blank page. The border is what the palette swap
      costs.
      **Correction:** the `position: relative` rationale said "the mockup anchors the state ribbon
      there". It does not — `editor.css` has no positioned rule at all and `.docnote` is a normal-flow
      block. The declaration stays, for the frozen-editor overlay (3.x) and the selection prompt
      (2.1), but it is this app's decision and not a copied one.
      **Left open, recorded rather than fixed:** (ac) the screen has no topbar/breadcrumb/format
      bar/statusbar at all — a staged deferral to the scenarios that own them, but until then the
      shell reads unfinished; (af) **nothing guards the scrolling model.** jsdom applies no layout,
      so the geometry above can regress silently — the guard belongs in
      `acceptance/tests/frontend/ai_chat/` as a Selenium assertion that with a long document the chat
      panel's rect stays in the viewport and `.ac-doc-wrap` is the element that scrolled
      (`scrollTop > 0` on the pane, `window.scrollY === 0`); (ag) `.ac-doc-wrap`'s `overflow: auto` is
      a new clipping ancestor over the editor, which is exactly the shape scenario 7.9's
      `manual_editor_popover_clip_statements.py` exists for — "a z-index cannot escape an ancestor's
      clip" — and scenario 2.1 puts a positioned prompt inside this pane.
      **The step row was missing from this scenario's list** (every other scenario has one); added
      retroactively. `/test-coverage frontend --focus` over it found **no gap it
      created**: `AiChatPanel.tsx` and `EditorDocumentView.tsx` are 100%/100% with **zero
      branches** between them, and the two CSS files are not instrumented at all. A clean report
      here is not evidence — v8 counts executed statements, and unconditional JSX plus a
      stylesheet cannot produce a gap however wrong they look. The gaps below are the *green*
      units' and were invisible until the filenames were passed explicitly, exactly as
      `carryover.md` predicted of the `git diff HEAD --name-only` focus filter.
- [x] red-frontend (coverage: repeat mount does not refetch) — two cases in
      `frontend/src/features/aiChat/hooks/__tests__/useEditorDocument.strictMode.test.tsx`.
      **The guard already exists and is already correct, so the RED evidence is mutation, not a
      failing main:** with the dedupe line deleted the test predicted and got `AssertionError:
      expected "vi.fn()" to be called once with arguments: [ Array(1) ] … Number of calls: 2`. The
      line was restored immediately and `git diff` on the hook is empty — that mutation is evidence,
      never a commit. This also *proves* React double-invokes effects in this vitest environment
      rather than assuming it; without that, the whole test would pass vacuously.
      `/test-review` found the first version's `rerender()` half vacuous, exactly as the red agent
      flagged: with `[documentId]` unchanged the effect never re-runs, so the guard-deleted run
      reported 2 calls, not 3 — the rerender contributed nothing either way. Instead of deleting it,
      it was redirected at a mutation **nothing in the suite killed**: degrading the guard to
      `if (requestedIdRef.current !== null) return` — "fetch at most once ever, whatever the id" —
      passed all 513 tests. The hook would have silently refused to ever load a second document. The
      second case now kills that, and additionally pins that an id change synchronously clears the
      previous document to `{ status: 'loading' }`, without which the user sees one document's text
      under another document's id for a round trip.
      Two further fixes: the ready state is asserted as the whole `{ status, document }` value rather
      than `status === 'ready'` alone — the guard sits *before* the fetch, so a variant that also
      swallowed the `setState` would leave `ready` reachable with no document behind it — and the
      call list is asserted as an exact ordered array, pinning count and arguments together.
      The exact-count assertion here versus `useDocumentInit.strictMode.test.tsx`'s relational one
      (`new Set(keys).size === 1`) is deliberate: that hook's guarantee survives a doubled effect, so
      a count there would be testing React; here the guarantee *is* "the fetch does not repeat", and
      the count is the specification with no weaker true form.
      Mutation matrix after review: guard deleted → both cases fail; guard keyed `!== null` → case 1
      correctly still passes, case 2 fails; unmutated → both pass. 514 passed / 0 failed; tsc clean.
      `/refactor`: NO ACTION. The `DOCUMENT_ID`/`DOCUMENT` literals are byte-identical to the
      notFound test's, but that is copy-paste rather than coupling — and this file needs a
      contrasting *pair*, so sharing one member would split the pair across modules.
      **Review-pass follow-ups (both CONCERNS):**
      (ah) **The file's load-bearing premise is pinned by nothing.** Case 1's exact count is
      satisfied identically by (a) the guard working against a doubled effect and (b) the effect
      simply not doubling. The mutation proving (a) existed for one local run and no reader can
      reproduce it. The sibling `useDocumentInit.strictMode.test.tsx` declines a count assertion for
      exactly this reason, in a comment: "whether React double-invokes depends on the build". A React
      upgrade, a vitest/jsdom config change or a dropped `StrictMode` wrapper turns case 1
      permanently green-and-vacuous with nothing failing. Owe one assertion anywhere in the suite
      that a *guardless* effect under the same wrapper fires twice — a two-line control hook.
      (ai) By the matrix above, case 1 kills no mutation case 2 does not also kill. Not a defect, but
      its independent reason to exist depends on (ah) being closed.
      (aj) **The sibling step "stale response for old id ignored" is worded for the case the ref
      already handles.** `requestedIdRef` stores an *id*, not a *request*, so A→B→A issues two
      fetches for A and the first, superseded one passes the `!== documentId` check and sets state —
      including a stale `version`, which `editorDocumentApi.ts` documents as travelling back on save.
      Route ping-pong, not the double-invoke, is the source. That step must be re-scoped to: mount A,
      switch to B, switch back to A, resolve A's *first* promise last, assert the second response
      wins — which needs a request token (per-effect flag or monotonic seq) beside the id key.
      (ak) **`EditorDocumentView` has no test file at all, and `useEditor` never re-applies a changed
      `content` prop.** Today that is masked because an id change routes through `loading` and
      unmounts the view; any content update at the *same* id — the entire point of story 19 — is
      dropped silently. Owe: render with X, rerender with Y at the same mount, assert Y is on screen.
      This is (s) confirmed by a second pass and located.
- [x] green-frontend (coverage: repeat mount does not refetch) — **no production change, and that is
      the honest outcome**: the guard already existed and RED proved it load-bearing by mutation
      rather than by a failing main, so there is nothing minimal left to write. Both cases report
      *passed* individually; 514 passed / 0 failed; `git diff` on `useEditorDocument.ts` empty.
      The measurable result is the branch count the step was inserted for: the hook moved from 4/8 to
      **5/8 branches** (50% → 62.5%), the newly-covered arm being the dedupe guard's `return`. Lines
      41-46 remain uncovered — the two stale-response guards, which belong to the re-scoped sibling
      step (aj), and the `'failed'` arm of the `instanceof` ternary, which belongs to scenario 8.8.
- [x] red-frontend (coverage: a superseded response for the SAME id loses) — re-scoped by
      follow-up (aj): the original wording ("stale response for old id ignored") describes the case
      `requestedIdRef` already handles. The unpinned arm is two outstanding requests for the *same*
      id (A→B→A), where the first response passes the id check and installs a stale `version`.
      One case in `hooks/__tests__/useEditorDocument.supersededResponse.test.tsx` (148 lines).
      **This is a real defect on main, not a mutation exercise** — unlike the previous coverage pair,
      the test fails against the unmodified hook. Predicted and got `AssertionError: expected
      { status: 'ready', document: {… version: 3} } to strictly equal {… version: 9}` — the
      superseded first response for A wins because `requestedIdRef.current` is back to `A` by the
      time it resolves. Every earlier assertion passes on main, which is what proves the premise:
      the hook really does issue `[A], [B], [A]`, so there really are two outstanding requests for
      one id. No StrictMode wrapper — the subject is *which response wins*, and the dedupe guard
      already collapses each double-invoke to one fetch, so StrictMode would leave the call list
      identical while implying the defect is a dev-mode artefact. It is not: three distinct ids
      being requested is plain navigation.
      `/test-review` landed four fixes. The load-bearing one: B's response and A's second response
      were flushed inside **one** `act`, so B lost by microtask ordering rather than by the
      pre-existing old-id guard — deleting that guard failed nothing, and the header comment's claim
      that it was "exercised in the same run" was false. B now resolves alone with its own
      unchanged-state assertion. Also: `toEqual`→`toStrictEqual` throughout (`toEqual` treats a key
      holding `undefined` as absent, so a green widening the state with an `error?` beside a
      stale-but-present document would have passed — exactly this file's bug class); a
      `{ status: 'loading' }` assertion after each `rerender`, without which a hook that stopped
      clearing the previous document on an id change still satisfied the final assertion; and
      `expect(resolvers).toHaveLength(3)`, so a missing resolver dies with a diff rather than a
      `TypeError` inside the fixture. One finding rejected: a redundant per-field `version` assertion
      beside the whole-state `toStrictEqual` — `tdd-rules.md:130` prefers structural comparison, and
      the extra check could only ever fail alongside the one above it.
      514 passed / 0 failed / 1 skipped (the skip is this case).
      **Green needs a per-request token beside the id key** — a monotonic sequence or a per-effect
      flag captured in the effect closure. The id alone cannot separate two outstanding requests.
- [x] green-frontend (coverage: a superseded response for the SAME id loses) — **a real production
      fix, not a mutation exercise**: a monotonic `requestTokenRef` now sits beside `requestedIdRef`,
      the token captured in the effect closure, and both `.then`/`.catch` compare
      `requestTokenRef.current !== requestToken` instead of `requestedIdRef.current !== documentId`.
      The two outstanding fetches for A in the A→B→A ping-pong hold tokens 1 and 3, so only the
      newest may `setState` and the stale `version: 3` no longer travels back on save.
      `requestedIdRef` keeps exactly one job — the pre-fetch StrictMode dedupe guard — and the
      comment claiming it "doubles as the stale-response check" went with the behavior it described.
      The old-id case needs no separate guard: a superseded request is by definition not the newest
      token, so one comparison subsumes both. 515 passed / 0 failed (117 files); the sibling
      `useEditorDocument.strictMode.test.tsx` still passes, which is what proves the dedupe guard
      survived being split off the stale-response check.
      Both pairs target `useEditorDocument.ts` (branches 4/8). **Superseded by the green above for
      the `.then` arm only** — deleting the guard now at `L46` fails the un-skipped
      `supersededResponse` case, so follow-up (k) is closed for that arm and open for the other two.
      What the paragraph below still describes correctly: the dedupe guard (now `L39`) and the
      `.catch` token guard (now `L50`) survive deletion with the suite green — premortem verified the
      `.catch` one by mutation (4 files / 10 tests still pass without it). The two guards written by
      one commit therefore have asymmetric coverage. Original wording, with the stale `L35`/`L41`/
      `L45` numbers, kept below for the reasoning it carries: the
      StrictMode double-fetch proof lives in `useDocumentInit.strictMode.test.tsx` for the *other*
      hook, and `toHaveBeenCalledExactlyOnceWith` here is asserted outside StrictMode, so it
      passes for a hook with no guard at all. The stale-response pair needs a rerender with a new
      `documentId` while the first load is still pending.
      **Deferred, NOT added here — these belong to scenario 8.8** ("The document load has a
      loading state and a distinct failure state"), which owns them: `useEditorDocument.ts:46`
      cond-expr arm 1 (the `'failed'` side of the `instanceof` ternary) and
      `DocumentEditorPage.tsx:27` (the whole `document-load-failed` screen, statement + `if` arm).
      That is follow-ups (h)/(p) — the regression to `catch { setNotFound(true) }` is still
      suite-green — now located precisely rather than merely restated.
      **Both review passes over the rejection RED found this independently and rated it credible**,
      so 8.8 inherits two named cases rather than a restatement. (1) Hook level: reject
      `loadEditorDocument` with a plain `new Error('boom')`, assert `toStrictEqual({ status:
      'failed' })`, kept beside the `DocumentNotFoundError` → `not-found` case so the two are pinned
      as *different*; verify by mutation that the ternary collapsed *either* way fails. Today
      `'failed'` is asserted nowhere under `features/aiChat` — every such assertion in the repo
      belongs to `features/generation` — and every rejection path in this feature uses
      `DocumentNotFoundError`, so the exact regression the hook's header comment argues against is
      held up by prose alone. (2) Component level: a `DocumentEditorPage.loadFailed.test.tsx`
      rejecting generically, asserting the `document-load-failed` panel renders, that no editor /
      `ai-chat-*` node is present, and — the design decision this forces open — that the screen
      offers *some* way out. It currently offers none: prose only, no link, no retry, while the
      sibling `not-found` branch has its anchor pinned down to `tagName === 'A'` and
      `href === '/documents'`. In-SPA retry is impossible by construction anyway
      (`requestedIdRef.current === documentId` means a same-id re-render never re-fetches), so
      recovery needs a remount or a reload — which on a flaky connection hits the same failure.
      Also surfaced, not owned by 8.8: a newest request that never settles leaves the spinner
      forever, because the superseded-but-good response was deliberately dropped and
      `expectPingPongNotRepeated` forbids a recovery re-fetch. `shared/api/send.ts` has no timeout
      or `AbortController` — a request deadline belongs in the transport layer, not this hook.
      And: **ESLint does not run in this repo at all.** `npx eslint` dies with "couldn't find an
      eslint.config.(js|mjs|cjs)" — ESLint 10.8.1 no longer reads `.eslintrc.*` and the config
      migration was never done, so the frontend currently has zero lint coverage.
      Also uncovered and deliberately left alone: `DocumentEditorPage.tsx:20` `documentId ?? ''`
      right arm — reachable only by mounting the page off its route, no user-visible behavior.
- [x] red-frontend (coverage: a superseded *rejection* for the SAME id loses) — **un-skipped and
      suite-green**, per the `42ba5d94` precedent: a case that pins an already-correct guard lands
      unmarked; only a case that genuinely fails against main carries a skip. Proof is by MUTATION —
      deleting the `.catch` guard gives `AssertionError: expected { status: 'not-found' } to strictly
      equal { status: 'ready', document: {…version: 9} }`, exactly as predicted, and it is the *only*
      failure in 118 files, so the new case is the sole exerciser of that arm. Guard restored, hook
      `git diff` empty. 516 passed / 0 failed.
      Adding the case inline took the file to 212 lines, over the 200 cap, so the shared ping-pong
      premise (constants, deferred-load fixture, `startPingPong`, `expectPingPongNotRepeated`) moved
      to `supersededRequestFixture.ts` and each arm got its own file — `vi.mock` is hoisted per file,
      so each case declares its own and passes the mock in. The split was re-verified by mutating the
      *other* arm: deleting the `.then` guard fails `supersededResponse.test.tsx` alone. Each case
      still kills its own arm and only its own arm.
      `/test-review` landed two fixes, both in the fixture: the call-list assertion was the lone
      `toEqual` in files that argue for `toStrictEqual` everywhere (a hook grown a second parameter
      passed as `undefined` would change the call shape silently), and `READY_ON_FRESH` was
      un-annotated, so its `status` inferred as `string` — a typo in the literal would compile and
      both cases would then assert the same wrong thing in lockstep.
      Non-vacuity: this case asserts only that a *superseded* rejection is ignored, so alone an empty
      `.catch` would satisfy it — the positive arm is pinned by `DocumentEditorPage.notFound.test.tsx`
      (rejects with a real `DocumentNotFoundError`, requires the blocker). The pair is complete.
      **Follow-up, not fixed here:** `useEditorDocument.strictMode.test.tsx` uses `toEqual` for all
      four whole-state assertions (L86/101/109/112) — the same looseness these files reject. Committed
      file outside this change's scope; tightening it is its own change.
      Inserted by the premortem over the green above. The `.catch` token guard is the twin of the
      `.then` one and is unexercised — deleting it leaves `src/features/aiChat` green (4 files,
      10 tests). This is the arm that produces the user-visible dead end rather than a
      stale-but-plausible version: A's *first* request rejecting late (502, dropped connection,
      expired session, or a `DocumentNotFoundError` for a since-deleted sibling) overwrites a good
      `ready` with `failed` — or with `not-found`, which per the hook's own comment tells the user
      their document is gone and invites them to re-create one that exists.
      Named case: in `useEditorDocument.supersededResponse.test.tsx`, have `deferredLoads()` also
      capture `reject`; run the ping-pong A→B→A, resolve `resolvers[2]` with `FRESH_DOCUMENT`, then
      call `rejecters[0](new DocumentNotFoundError(...))` and assert `result.current` is still
      `{ status: 'ready', document: FRESH_DOCUMENT }`.
- [x] green-frontend (coverage: a superseded *rejection* for the SAME id loses) — **empty production
      diff, and that is the honest outcome**: the `.catch` token guard already existed and RED proved
      it load-bearing by mutation rather than by a failing main, so nothing minimal was left to
      write. `git status --porcelain` clean; 516 passed / 0 failed / 0 skipped (118 files).
      The measurable result is the branch count the pair was inserted for: `useEditorDocument.ts`
      moved 5/8 → **7/8 (87.5%)**, statements 17/17, functions 4/4, lines 14/14. Per-arm from
      `coverage-final.json`: the dedupe guard (L38) and the `.then` token guard (L45) both arms
      covered, and the newly-fired one is the *taken* arm of the `.catch` token guard (L49) — hit
      exactly once, by this test alone. The two RED cases from `5851340a` together did 5/8 → 7/8.
      **The one arm still uncovered is L50 col 82 — the `'failed'` side of the ternary.** Nothing in
      the repo rejects `loadEditorDocument` with anything but a `DocumentNotFoundError`, so the
      non-404 path the hook's own comment names as its reason for existing has never executed. That
      is scenario 8.8's, per the named cases recorded above.
      **Quirk found — the coverage threshold is global, so a narrowed run lies.** Running with
      `--coverage.include` scoped to this one hook trips `ERROR: Coverage for branches (87.5%) does
      not meet global threshold (89%)`: the repo-wide floor in `frontend/vite.config.ts:46-51` is
      compared against a single-file scope. The unnarrowed run is fine — 89.76% branches (614/684).
      A per-file coverage check on this project must ignore the threshold verdict and read the
      numbers.
- [x] green-selenium — marker removed, test **passed**, no production/Statements/backend change.
      `acceptance/tests/frontend/ai_chat/test_document_not_found_acceptance.py::TestDocumentNotFound
      BlockerAcceptance::test_should_block_with_not_found_and_offer_the_documents_list` — 1 passed in
      269.55s, and passed a second time inside the suite run. The class-level `@pytest.mark.skip`
      plus its 9-line RED comment went, and with them the `import pytest` that existed solely for the
      marker (leaving it would have added an 11th `unused import` to the 10 pre-existing ruff errors
      in follow-up (e)). This closes red-selenium follow-up (d): the un-skip happened and the test
      reports *passed*, not skipped.
      **Environment, not committed:** the compose recreate dropped `textery_s19` — the volume kept
      only the old `textery`, so the backend booted into
      `asyncpg.exceptions.InvalidCatalogNameError: database "textery_s19" does not exist`. Recreated
      it (`CREATE DATABASE textery_s19`) and the backend migrated it on restart; all seven tables are
      present. `infra/.env` is gitignored, so the warning at line 240 of `progress-backend.md` stands
      and now has a second failure mode: not just a fresh checkout, but any
      `docker compose up --build` that recreates postgres.
      **Two failures in the wider frontend suite, verified NOT this unit's** — both reproduce
      identically with this change stashed (`2 failed in 38.89s`), and both belong to Story 5/auth:
      `auth/test_login_submit_disabled_while_in_flight_acceptance.py` (`AssertionError: expected
      submit button to be disabled`, `frontend_form_assertions.py:133`) and
      `auth/test_login_submit_loading_indicator_acceptance.py` (`TimeoutException` in
      `_wait_for_visible`). Symptom on both: the login request settles before the in-flight state can
      be observed. The *register* equivalents pass, so this is the login path's response latency, not
      a shared harness problem. The suite run was stopped at 14% per stop-on-first-failure — 12
      passed, 2 failed, **21 tests did not run**, so there may be more.
      **Review-pass findings. One discharged here, two open:**
      *(discharged)* The Statements file's own re-check obligation fired and nobody noticed. Its
      docstring justified the forbidden in-app-URL `driver.get` with two reasons, and reason (2) —
      "there is no documents-list screen in the app at all, and `App.tsx` has no `/documents/:id`
      route" — became false when `70ef65eb` shipped both routes; `HistoryPage.tsx:95` now opens a
      document by click. The obligation the file wrote for itself was to re-verify reason (1) when
      the list landed. Performed: `listDocuments` returns only the signed-in account's own live
      documents, and the list has no "recently deleted" row and no shared-with-me tab — the two
      shapes that would create a click path to a foreign or absent id. Reason (1) survives, the
      `driver.get` stays legal, and the docstring plus the `DOCUMENTS_LIST_PATH` comment now say so
      instead of the opposite.
      *(open)* **269.55s for one test, unexplained and accepted as green.** Every Selenium wait on
      the path is bounded at `WAIT_TIMEOUT_SECONDS = 5`, the test does one `driver.get`, one live
      session (three HTTP calls) and two `find_elements` absence checks — a worst case near 20-30s
      plus browser startup. Neighbours in the same suite run ~3s each. So ~4 minutes is going
      somewhere unaccounted: Chrome startup, backend password hashing, or the editor route's on-mount
      call. Both passes flagged it independently; at this cost the suite fits no CI budget, and if it
      is the editor mount it is a product latency signal, not a harness one. Nothing bounds a test's
      wall clock, so only a human eye can notice an outlier. Related and named by the premortem:
      `useEditorDocument` has no timeout and no `AbortController`, and `DocumentEditorPage` renders
      the loading message for anything not `ready`/`not-found`/`failed` — so a request that never
      settles never reaches `failed`, and the "try again" screen is unreachable by hang.
      *(open)* **No full frontend acceptance run has completed since the routes landed.** `70ef65eb`
      inserted `/documents` and `/documents/:documentId` *above* the `/*` catch-all in `App.tsx` —
      the change shape that silently re-routes existing scenarios — and the generation-flow tests
      behind that catch-all are among the 21 that did not run. No interception path was found by
      inspection (no existing test appears to use a `/documents*` URL), so severity is low, but the
      verification is absent rather than merely unlikely to matter. Owed: one run without `-x`, with
      the two known-red login tests deselected.
      *(out of trace, flagged not fixed)* `acceptance/statements/frontend/live_auth_session.py:52`
      reads `verification_code` straight out of the `POST /api/v1/auth/register` 201 response body.
      If that is production behaviour rather than a test-only affordance, email verification is
      bypassable by the registrant and by anyone who observes the response. Pre-existing, backend's
      to answer — but the whole frontend acceptance harness depends on it.
- [x] demo — `TestDocumentNotFoundBlockerAcceptance` run headed at 1.2s per wait: **1 passed,
      93 deselected, in 25.39s.** Demo changes (headless off, `--window-size=1280,800`,
      `_demo_delay()` in `_wait_for_visible` and `_assert_absent`) reverted; working tree clean.
      **This closes the open 269s follow-up, and the answer is that the number was never the
      test's.** The same test, *with* ~5 injected seconds of deliberate slow-motion, finishes in
      25s — an order of magnitude under the green-selenium reading. So the ~4 minutes was
      environmental, not the editor route's on-mount call and not a product latency signal: the
      green-selenium run paid for a cold stack (backend had just restarted onto a freshly created
      and freshly migrated `textery_s19`) and first-run chromedriver setup. The review passes were
      right to refuse the number as unexplained, and wrong about where it pointed — worth keeping
      as the shape of the mistake: a wall-clock outlier measured once, on a cold environment,
      reads exactly like a latency defect.
      Two things the demo did NOT do, both deliberate: the skill's stop/restart-backend step was
      skipped, because the stack is shared with the parallel backend session and this test mints
      its own account through `issue_live_session`, so a clean database buys nothing; and
      `FRONTEND_PORT=80` was passed explicitly, since the `app_url` fixture defaults to Vite's 5173
      while the compose route serves on 80.

### 0.2 An account over its daily quota cannot type an instruction
- [x] red-selenium — one test, four Statements calls, in
      `acceptance/tests/frontend/ai_chat/test_over_quota_acceptance.py` with
      `over_quota_statements.py` + `over_quota_session.py`. Predicted and got a failure in the
      **SETUP**, one layer before anything the scenario asserts: `AssertionError: over-quota
      setup: probe 0 expected 202 or 429, got 404: {"detail":"Not Found"}` — `POST
      /api/v1/documents/{id}/ai-edits` is not a registered route (the router file exists,
      no composition root includes it, its seven providers still raise `NotImplementedError`),
      so the quota counter cannot be moved and the Given is unreachable.
      **This test specifies a contract addition green must make:** no endpoint reports quota
      state on document open — `resets_at` lives only in the `429` body of `POST /ai-edits`
      and none of `endpoints.md`'s seven endpoints carry quota fields. Green owes a
      quota-state read the editor route issues on open.
      Navigation is by CLICK, unlike 0.1: this document exists and belongs to the signed-in
      user, so the Given's own verb is performed by clicking its row. The single `driver.get`
      is of the LIST `/documents`, on the bookmarkable-entry-point exception — with the same
      re-check obligation 0.1 carries, due when scenario 7.2 adds a link to it.
      `/test-review` landed nine fixes over 15 findings. The load-bearing one: the setup
      accepted `{done, error, cancelled}` as terminal, so an environment failing every edit
      would refund every charge, exhaust all 25 probes and report **a quota configured too
      high** — exactly backwards; only `done` is accepted now, `error`/`cancelled` fail loudly
      with the body. The session module also hand-rolled `httpx`, URLs, headers and status
      codes, duplicating three methods of `acceptance/clients/application/document_edit_client.py`
      — it now delegates to `DocumentEditClient` and keeps only quota-spending *policy*.
      Further: `resets_at` went from a truthiness check to a parsed, offset-aware instant
      bounded to `now < t <= now + 24h` (the raw wire string is still what travels to the UI
      assertion, so `data-resets-at` stays byte-exact); the 202 probe pins `status == "queued"`
      (a replay's current status would mean the probe charged nothing); the row check asserts
      `data-document-id` identity, not just arity; the revisions panel asserts exactly one
      `data-revision-number='1'` row rather than a container (an empty panel is "displayed");
      the prefix `startswith` hint match became exact equality against a new
      `ai-chat-quota-reset-hint-lead` element — the countdown tail is unpinnable, which is a
      reason to **split the element**, not to loosen; and the panel-opening click moved out of
      an `assert_*` method into `open_the_revisions_panel`.
      Rejected: pinning `DAILY_EDIT_QUOTA` as a literal (no quota value is declared anywhere
      in the repo — it is env-configured; the server's own 429 is the strictest available
      proof), asserting the 429's `error_code` (no literal exists in specs or backend tests;
      inventing one defines a backend contract value a parallel session must honor), and
      asserting all seven `DocumentResponse` fields (re-tests Story 5 from a Story 19 file).
      **Deferred to `/refactor` on purpose:** `_sign_in_as` is now a third copy (also
      `chat_workspace_statements.py:51`) and belongs on the shared base class.
      Evidence: ruff clean on all four files, `--collect-only` 2 collected / 0 errors, the
      test reports **1 skipped** (RED marker in place, un-skip is green-selenium's), and the
      RED state was re-verified live against the running backend — same failure, same place,
      but now *past* document creation and past the new `document_type`/`version` assertion,
      which proves the client delegation works end to end.
      **All three files sit at or within a line or two of the 200-line cap** — the next
      addition to `over_quota_session.py` (exactly 200) forces a split.
- [x] red-frontend — four cases in
      `frontend/src/features/aiChat/components/__tests__/DocumentEditorPage.overQuota.test.tsx`
      (194 lines) plus the RED stub `features/aiChat/api/editQuotaApi.ts`. Predicted and got all
      four as `TestingLibraryElementError`, byte-identical messages: `Unable to find an element by:
      [data-testid="ai-chat-message-input"]` (cases 1 and 4), `…"ai-chat-quota-reset-hint"`
      (case 2), `…"ai-chat-revisions-toggle"` (case 3). The dumped DOM shows the `ai-chat-panel`
      aside resolved, so the route, the load and the `ready` branch all ran — the failure is
      strictly the missing composer inside the panel, not a vacuous pass against an unrendered tree.
      **The contract addition this specifies:** `loadEditQuota(): Promise<{ exhausted: boolean;
      resetsAt: string | null }>` — **account-scoped, no `documentId`**. The daily limit belongs to
      the account; threading a document id through invites a per-document reading of a limit that
      is not per-document. The wire mapping and the endpoint belong to `red-frontend-api`.
      **Follow-up (an) is closed by a case rather than by convention.** `RESETS_AT_WIRE =
      '2026-08-11T00:00:00+03:00'` is deliberately non-canonical — a Moscow offset, no fractional
      seconds — and `data-resets-at` must carry it byte for byte. Any `new Date(…).toISOString()`
      on the path rewrites it to `2026-08-10T21:00:00.000Z` and fails. The decision: the hint
      renders the wire string verbatim into the attribute, and the human-facing countdown is a
      separate element's job. That is what makes the Selenium layer's cross-serialization
      byte-equality safe instead of fragile.
      All six testids are byte-identical to `over_quota_statements.py`, so the two layers cannot
      drift into specifying different UIs.
      **The fourth case is the one the acceptance test structurally cannot write:** spending a real
      day's quota only ever exercises the exhausted branch, so a composer disabled for everybody —
      or one with no quota read behind it at all — would pass Selenium. That is the 0.1
      unconditional-blocker lesson applied before it can happen.
      `/test-review` landed five fixes. The two load-bearing ones: **the account-scoping argued at
      length in the stub was unenforceable** — nothing failed if green passed a `documentId` — and
      is now held by `toHaveBeenCalledExactlyOnceWith()` with zero arguments; and **the counts were
      proved outside StrictMode** while `main.tsx` wraps `App` in it, which is follow-up (k) one
      fetch over — `renderEditorFor` now renders under `<StrictMode>`, so the counts are honest
      from day one instead of being discovered later. Also: both loads are now pinned with
      `toHaveBeenCalledExactlyOnceWith` in all four cases (two cases pinned nothing, and the
      document load was pinned nowhere, so a page refetching on every render passed);
      `EditQuotaState` is imported rather than re-declared as an inline literal (a rename in the
      stub would have left this file green against a module it no longer agreed with); and
      `toBeInTheDocument()` after `findByTestId` — a no-op, since `findBy*` already throws — became
      `toBeVisible()`, the one place this layer was strictly weaker than Selenium's `is_displayed()`.
      Rejected: pinning the revisions panel's rows (scenario 1.3 owns `GET /revisions`; the Selenium
      layer carries that strictness) and asserting a countdown sibling (no testid for it exists in
      `over_quota_statements.py`, and inventing one breaks testid parity between the layers).
      Evidence: 516 passed / 0 failed / 4 skipped (119 files); tsc, oxlint and prettier clean on
      both files; RED re-verified by temporarily un-skipping all four — same messages byte for
      byte, and the StrictMode change does not move the failure point.
      **Green inherits three things:** the file is 194 of 200 lines, so a fifth case forces a
      split; the quota read needs its own pre-fetch StrictMode guard (a ref before the fetch — the
      `useDocumentInit` cancel-flag pattern suppresses the second `setState`, not the second
      request); and the coverage gate is red on this commit exactly as follow-up (f) was on 0.1
      (`editQuotaApi.ts` at 0% behind four skipped tests, against the 60% per-file floor) — green
      closes it by un-skipping, with no floor lowered and no exclude added.
      **Deliberately not pulled forward:** `useEditorDocument`'s `loading`/`failed` states and the
      quota read's own loading/failure states (scenario 8.8), and the revisions panel's contents.
      "Remains usable" is asserted here as: the toggle is enabled over quota, the panel is closed
      before the click and open after it. **Green must not read that gap as licence to ship an
      empty panel** — `green-selenium` will not pass on one.
- [x] green-frontend — four new files, two modified. `hooks/useEditQuota.ts` (35 lines) does the
      one-per-mount account-scoped read; its StrictMode guard is a `useRef` set **before** the
      `loadEditQuota()` call, not the `useDocumentInit` cancel-flag — that flag suppresses the
      second `setState`, not the second request, which is exactly what
      `toHaveBeenCalledExactlyOnceWith` measures. A failed read resolves to `null` ("not yet
      known") so a dead endpoint cannot take the route down; a distinct `failed` state is 8.8's.
      `components/AiChatComposer.tsx` (58) gives input and send one shared
      `disabled={quota.exhausted}`, and `QuotaResetHint` writes `data-resets-at={resetsAt}`
      straight from the wire string — **no `Date` anywhere on the path**, with the lead in its own
      `ai-chat-quota-reset-hint-lead` span so the countdown tail can land later without loosening
      the assertion. `components/AiChatRevisions.tsx` (34) keeps the toggle and panel **outside**
      the quota branch — its enabled state is never conditioned on quota — and the panel ships an
      empty-state notice rather than an empty container, per the red phase's warning that
      `green-selenium` will not pass on one. `AiChatPanel.css` is a new file rather than an append
      to `DocumentEditorPage.css`, which sits at 190/200.
      **The judgement call:** `AiChatPanel` takes `quota: EditQuotaState | null` and **withholds**
      the composer while `null`, showing a notice instead. Rendering it live-then-dead a tick later
      would invite the user to start typing an instruction that was never going to be accepted.
      `editQuotaApi.ts`'s type became a discriminated union
      (`{exhausted:false;resetsAt:null} | {exhausted:true;resetsAt:string}`); the body still
      throws and the endpoint remains `red-frontend-api`'s — the seam the tests pin (zero
      arguments) is unchanged.
      Evidence: the four cases un-skipped and passing (the only edit was removing `it.skip` and
      its `// RED:` comment — diffed to confirm no assertion moved); full frontend suite
      **520 passed / 0 failed / 0 skipped** (119 files); tsc, oxlint and prettier clean.
      **One test change outside the un-skip, named on purpose:** `DocumentEditorPage.notFound.test.tsx`
      gains an 11-line `vi.mock` of `../../api/editQuotaApi` resolving the within-quota value.
      Unavoidable collateral — adding the quota read to the shared `ready` branch means scenario
      0.1's success case now reaches the real `loadEditQuota`, which throws by design. Setup only;
      no assertion touched.
      **The coverage gate's exit 0 is weaker than it looks:** `editQuotaApi.ts` still reads 0%
      line/function (its one function is mocked in every test) and passes only because the
      per-file floor is evaluated at the `features/aiChat/api` directory = 66.66%. The red phase's
      "un-skipping closes it" is true by aggregation, not because the module became covered —
      `red-frontend-api` is what actually covers it.
- [x] red-frontend-api — six cases in
      `frontend/src/features/aiChat/api/__tests__/editQuotaApi.test.ts` (145 lines), one
      `describe.skip` marker (one function under test — this feature's `editorDocumentApi.test.ts`
      convention). No new fixtures file: `stubFetch` and `expectErrorIdentity` are imported from
      the existing `editorDocumentApiFixtures.ts` rather than copied.
      **THE CONTRACT ADDITION, stated here so the backend session can honour it verbatim:**
      `GET /api/v1/ai-edits/quota` → `200 {"exhausted": bool, "resets_at": string | null}`.
      Account-scoped — **no `document_id` in the path**, matching the zero-argument
      `loadEditQuota()` the component layer already pins with `toHaveBeenCalledExactlyOnceWith()`.
      This closes the gap `red-selenium` and `red-frontend` recorded: none of `endpoints.md`'s
      seven endpoints reports quota state, `resets_at` living only in the 429 body of
      `POST /ai-edits` — i.e. only *after* the user has typed an instruction and been refused,
      which is one attempt too late for a composer that must be dead on arrival.
      Predicted and got all six as the stub's unconditional throw, at three distinct assertion
      sites: two `resolves` cases as `AssertionError: promise rejected "Error: loadEditQuota is
      not implemented y…" instead of resolving`, the bare-await case as `Error: loadEditQuota is
      not implemented yet`, two message cases as `expected 'loadEditQuota is not implemented yet'
      to be '…'`, and the 401 case as `expected Error: loadEditQuota is not implemented y… to be
      an instance of SessionExpiredError`.
      **Two cases guard the discriminated union from the WIRE side**, which is where TypeScript
      cannot: `{exhausted: true, resets_at: null}` must be refused as a load failure (an exhausted
      quota that cannot say when it lifts would render `data-resets-at="null"`), and
      `{exhausted: false, resets_at: <instant>}` must have the instant dropped. The forbidden
      `{exhausted: true, resetsAt: null}` is unrepresentable in the result type; only these two
      cases stop a mapping from casting its way there.
      `resetsAt` byte-equality is pinned by the same non-canonical `'2026-08-11T00:00:00+03:00'`
      the component test uses — a `Date` round trip rewrites it to `'2026-08-10T21:00:00.000Z'`
      and fails here, so the Selenium layer's `data-resets-at` assertion stays safe.
      The happy path also asserts `init.method` and `init.body` are undefined: without them the
      test passes for a POST that returns the quota, i.e. for a client that SPENDS a charge on
      every document open. And the 500 case pins `name === 'Error'`, which rules out a green that
      opts this call into `send`'s `notFound` mapping — a 404 here means the endpoint is missing,
      not that a document is.
      Evidence: full frontend suite **520 passed / 0 failed / 8 skipped** (119 files passed,
      1 skipped); tsc, oxlint and prettier clean. RED re-verified after review by temporarily
      un-skipping: all eight cases fail on `Error: loadEditQuota is not implemented yet`.
      `/test-review` landed six fixes and grew the file from six cases to eight. The load-bearing
      one is a **new case pair for a 200 that never states the quota**: `performRequest` ends with
      `await res.json().catch(() => ({}))` (`httpClient.ts:154`), so a 204, an empty 200 or an HTML
      page served with a 200 all arrive as `{}` — a green written `exhausted: Boolean(body.exhausted)`
      would then answer "the quota has room" for an endpoint that said nothing, and the composer goes
      live, which is the one state this scenario exists to prevent. Reached through the *success*
      path, where none of the three refusal cases look; added as an `it.each` over an empty body and
      a non-boolean `exhausted`, both refusing with the fallback text.
      `expect(loadEditQuota.length).toBe(0)` was vacuous — `Function.prototype.length` stops at the
      first optional parameter, so `loadEditQuota(documentId?: string)`, the exact green its comment
      named, still reported 0. Replaced by `expectTypeOf(...).toEqualTypeOf<() => Promise<EditQuotaState>>()`,
      exact in both directions and a `tsc` gate, so it is the one assertion live while the describe is
      skipped. `expect(quota.exhausted && quota.resetsAt).toBe(...)` computed its actual through a
      boolean branch (a false `exhausted` would report `expected false to be '2026-…'`, naming the
      wrong field) and restated the whole-object assertion; it became a guard on the constant's
      *non-canonicality* — `new Date(RESETS_AT_WIRE).toISOString()` must NOT equal `RESETS_AT_WIRE` —
      because the byte-equality trap is worthless if someone tidies the literal to canonical `Z` form,
      and nothing enforced that. Plus `toEqual`→`toStrictEqual` on every whole-object result assertion
      (`toEqual` treats a key holding `undefined` as absent, so `resets_at: undefined` leaked through
      the very "no wire field survives unrenamed" claim the comments make), the local `wire()` helper
      promoted to a shared `okJson()`, and `QUOTA_URL` / `UNAUTHORIZED_RESPONSE` /
      `SESSION_EXPIRED_MESSAGE` deduped into `editorDocumentApiFixtures.ts`, now consumed by both API
      test files.
      One finding rejected: `RESETS_AT_WIRE` is duplicated with `DocumentEditorPage.overQuota.test.tsx:45`
      and the comment's "the two layers cannot drift" is enforced by nothing — real, but its correct
      home is a shared aiChat test constant reachable from the api *and* component layers, and
      `editorDocumentApiFixtures.ts` is api-only; creating that module is `/refactor` scope. The
      non-canonicality guard above mitigates the actual risk meanwhile.
      **The file is at 191 of 200 lines after `/refactor`** — a ninth case is close to forcing a
      split, the same squeeze the component test hit at 194.
      `/refactor` took the deferred candidate: `RESETS_AT_WIRE` moved to
      `features/aiChat/__tests__/editQuotaWireFixtures.ts` (20 lines) — `aiChat/__tests__/` is the
      one directory both the api and component layers sit below, and `generation/__tests__/` and
      `landing/__tests__/` are the precedent. The comment claiming "the layers cannot drift" is now
      true rather than aspirational: previously a tidy-up canonicalising one copy to
      `2026-08-10T21:00:00.000Z` left both files green while deleting the round-trip trap on one
      side, because the non-canonicality guard only protects the copy it can see. It also extracted
      `requestedUrls(fetchMock)` (six call sites) and renamed `editorDocumentApiFixtures.ts` to
      `aiChatApiFixtures.ts`, which two files now share. 520 passed / 8 skipped; tsc, oxlint,
      prettier clean.
      **Review-pass follow-ups (both CONCERNS) — (al) and (am) are green-frontend-api's, act on them
      before writing the client:**
      (al) **The union guard has a hole a mirror-image green walks straight through.** The only
      exhausted-with-no-instant case sends `{exhausted: true, resets_at: null}`; nothing sends
      `{exhausted: true}` with the key **absent**, and the `it.each` pair does not reach it (both its
      bodies fail at the `exhausted` check first). A green written `if (body.resets_at === null)
      throw` passes all eight and returns `resetsAt: undefined`, i.e. `data-resets-at="undefined"` —
      the identical incident the case exists to prevent, found by the Selenium byte-equality
      assertion. One extra `it.each` row, not a new `it` block, given the line count.
      (am) **`resets_at` is never wire-validated for TYPE.** An epoch number or `''` passes all eight
      cases, a green forwarding `body.resets_at` types it as `string` by declaration only, and the
      Selenium assertion passes *trivially* because both sides carry the same garbage. Same `it.each`.
      (an) **The contract exists in no file the backend session reads.** `GET /api/v1/ai-edits/quota`
      is written only in this file's `QUOTA_URL` and in `progress-frontend.md`; `endpoints.md` still
      lists its original seven endpoints and `progress-backend.md` has no scenario for a quota read.
      Per CLAUDE.md File Ownership the backend session never reads this file. One table row in
      `endpoints.md` is the only artifact that crosses the session boundary — but `endpoints.md` is
      shared, so land it deliberately rather than as a side effect of a frontend unit.
      (ao) **The 401 case has no consumer.** A whole case preserves `SessionExpiredError` identity
      through `loadEditQuota`, and `hooks/useEditQuota.ts` discards it with `.catch(() =>
      setQuota(null))` — `null` means "not yet known", so the composer stays dead on arrival
      permanently and the user is never told they are signed out. `useGeneration.ts:87` and
      `useDocumentSave.ts:34` both branch on the type; this hook is the odd one out. No test
      distinguishes the two rejections at hook or component level.
      (ap) **The eight guards can ship never having run.** If green un-skips nothing the suite still
      reports all-green, and the directory-aggregated coverage floor (`features/aiChat/api` = 66.66%)
      cannot catch it — this story has already recorded that masking once. Green's verification must
      report the eight cases as *passed* individually.
      (aq) Housekeeping, corrected above: the entry's opening sentence said "six cases … 145 lines"
      pre-review. It is eight cases. And the file's header cites `editorDocumentApi.test.ts` as the
      `describe.skip` precedent — that describe is live since its own green phase (its stale comment
      at `:48` is the source of the confusion), so the citation is false and should go at green.
      **Green owes the real client** (`send('/api/v1/ai-edits/quota', {}, 'Не удалось загрузить
      лимит правок')` plus the two union guards) and the backend endpoint behind it; this is also
      the step that actually covers `editQuotaApi.ts`, which `green-frontend` left at 0% behind a
      directory-level coverage aggregate.
- [x] green-frontend-api — **528 passed / 0 failed / 0 skipped** (120 files), up from 520/8; the
      delta is exactly the eight un-skipped cases and nothing regressed. All eight report *passed*
      individually under the verbose reporter, closing follow-up (ap). tsc, oxlint, prettier clean.
      `editQuotaApi.ts` went 0% → **91.66% statements / 90.9% branches / 100% functions**, measured
      on the file rather than the `features/aiChat/api` directory aggregate that masked the zero —
      this is the step `green-frontend` said would actually cover the module.
      One production file, 75 lines: `send<QuotaWire>('/api/v1/ai-edits/quota', {}, 'Не удалось
      загрузить лимит правок')` with **no** `{notFound: true}` — a 404 here means the endpoint is
      missing, not that a document is, and opting in would admit `DocumentNotFoundError` into the
      path the 500 case pins to `name === 'Error'`.
      The wire→union mapping is where the scenario actually lives. `typeof exhausted !== 'boolean'`
      refuses, which is what makes the `{}` that `res.json().catch(() => ({}))` substitutes a load
      failure rather than "the quota has room"; `exhausted: false` returns `resetsAt: null`
      unconditionally, dropping any instant sent alongside room; `exhausted: true` with a missing
      instant refuses; and the surviving string is returned **verbatim**, with no `Date` anywhere on
      the path, which is what keeps the Selenium `data-resets-at` byte-equality assertion safe.
      **(al) and (am) are honored in production but still owed as cases.** The guard refuses an
      absent `exhausted`/`resets_at` key, an epoch number and `''` — but no test drives it, because
      adding cases in a green phase is not this step's job. That `throw` (line 58) is the one
      uncovered line in the file: protected by production code alone, deletable by a future green
      with the suite green. The test file is at 179/200, so both rows still fit as `it.each` rows
      rather than new `it` blocks, as the RED entry anticipated.
      Only test change: removing `describe.skip` and its four-line RED comment — which also carried
      the false `editorDocumentApi.test.ts` precedent citation, so (aq) went with it.
      Still open and untouched here: (an) `endpoints.md` has no row for `GET /api/v1/ai-edits/quota`,
      so the contract crosses no artifact the backend session reads; (ao) `useEditQuota.ts` swallows
      the `SessionExpiredError` this module carefully preserves via `.catch(() => setQuota(null))`,
      so case 7's guarantee has no consumer — the composer stays dead on arrival forever and the
      user is never told they are signed out.
      `/refactor`: **NO ACTION**, and one declined candidate is worth recording. The `resets_at`
      guard (L57) and the `resetsAt === null` guard (L65) collapse into one if the `!exhausted` early
      return is hoisted above them — but that is **not behavior-preserving**: today
      `{exhausted: false, resets_at: 123}` is refused, and after the reorder it would answer "the
      quota has room". No test covers that combination, so the suite would not have caught it.
      Also declined: extracting the three `throw new Error(FALLBACK)` into a `never`-returning
      `refuse()` (a `never` call reads as fall-through where a literal `throw` reads as a stop), and
      wrapping `resetsAt` in a value object (any parsing or normalization *is* the `+03:00` → `Z`
      round trip this module exists to avoid). Consumers checked: `useEditQuota.ts` and
      `AiChatComposer.tsx` branch on the resolved union only — the verbatim-instant rule is restated
      as a comment in both, but the code enforcing it exists once. 528 passed / 0 failed / 0 skipped;
      tsc, oxlint, prettier clean.
      **Review-pass follow-ups (both CONCERNS, and they converge on the same defect):**
      (ar) **The happy path is the strictest branch in the file — fix this before `align-design`.**
      The `resets_at` guard runs *above* the `!exhausted` arm that declares the field dropped, so it
      never gets the chance: `{"exhausted": false}` with the key omitted — the ordinary shape from a
      pydantic model with `exclude_none`, which is the default nobody will think to override — is
      refused as a load failure. `useEditQuota`'s `.catch(() => setQuota(null))` then leaves the
      quota unknown for the whole mount (`requestedRef` blocks any retry), so the composer is dead
      **for every user who has room**, silently, indistinguishable from still-loading. The field is
      tolerated-and-ignored when it is a valid string and fatal when it is not, for a value the
      function has already decided not to read. The scenario's invariant is only *silence must not
      read as room*, which `typeof exhausted !== 'boolean'` delivers alone. Hoisting
      `if (!exhausted) return {...}` above the guard preserves every asserted case and removes the
      failure mode — but it inverts what `{exhausted: false, resets_at: 123}` does, so it needs the
      (al)/(am) rows landed first to say which answer is intended. The defect and the file's one
      uncovered line are the same line.
      (as) **(ao) is no longer pre-existing — this commit is what made it live.** Before it,
      `loadEditQuota` always threw a plain `Error`, so the session path was unreachable; now case 7's
      two-401 renew-and-replay guarantee ships with nothing downstream honoring it. A signed-out user
      gets a permanently disabled composer, no redirect, no message, and no retry after re-auth.
      (at) **(an) is shipping-blocking, not a note.** The endpoint does not exist: every response is a
      404, so on today's backend the composer is dead for 100% of users and it looks exactly like
      loading. The path and body live only in a frontend test comment, this module and two commit
      messages — `endpoints.md` has no row and `progress-backend.md` no scenario. The endpoints.md row
      must also say **`resets_at` is required, send explicit `null`**, which is the hidden
      serialization requirement (ar) currently encodes in a guard nobody can read from the backend.
      (au) Cosmetic, not worth its own unit: `mapQuota` returns any non-empty string verbatim, so
      `"soon"` reaches `data-resets-at` and renders `Invalid Date`. The verbatim rule is a load-bearing
      cross-layer decision; validating the shape here would be the first step back toward a `Date`.
      Also noted: the "Deliberately NOT `{ notFound: true }`" comment sits ~25 lines from the `send`
      call it explains, and an orphan `//` line survives where the stub's comment was spliced.
- [x] align-design — aligned to `mockups/desktop/06-over-quota.html` + `editor.css`. The structural
      change is the mockup's `.composer .box`: input and send now share **one bordered field**
      instead of sitting as siblings, and the box is what carries the disabled treatment. A field
      that stays live-looking around a greyed control reads as "the send broke", not as "you cannot
      type here" — which is the whole claim of this scenario. `.ac-chat-box` copies the mockup's
      literal `12px` radius rather than `--radius-md` (10px): the box is the panel's largest control
      and the mockup rounds it past its own `--radius-md` too. The textarea lost its border and
      padding to become the field's interior, and the send moved into a `.ac-chat-box-row` that
      pushes it right with `margin-left: auto` — the old `align-self: flex-end` had nothing
      meaningful to align against once the box became the composer's only child.
      **Two documented deviations.** The row's `margin-top` is 10px, not the mockup's 26px: that 26px
      is the gap under a one-line `.ph` div, while a real 3-row `textarea` already occupies the
      height. And the disabled send takes `--bg-card-muted` where the disabled box takes `--bg-page`,
      whereas the mockup renders both on one `--bg-sunken` — here the dead control sits *inside* the
      dead field, and one shared surface would dissolve the button's edge into it.
      **The quota hint took the warn treatment**, matching `.docnote-warn`'s geometry exactly
      (`--radius-md`, `12px 16px`, `13.5px`, flex/centre) — a limit that stops the user is not a
      keyboard tip, so the mockup's muted `.keys` line was not the right analogue. The amber is
      derived from the app's own `--warning` through `color-mix`, never the mockup's `#fff7ed` /
      `#fed7aa` / `#c2410c` literals, per the palette rationale in `DocumentEditorPage.css`'s header.
      `--bg-sunken` has no counterpart in `index.css`; `--bg-page` is this app's sunken surface.
      `/design-review`: **PASS on the placeholder gate** — none of the mockup's payload reached the
      component (`415 слов · версия 27`, `Осталось правок сегодня: 0 из 20`, `20 из 20`, `27 версий`,
      the `17:48` stamps, `История ИИ`, the whole `.msgs` conversation, and — the one most likely to
      slip — the mockup's own `.ph` copy `Лимит исчерпан — обновится в 00:00 МСК`, which carries a
      wall-clock literal where the component carries `data-resets-at` from the API). Two of its minor
      findings were fixed in this unit: the undocumented two-surface divergence above is now
      commented, and an inert `gap: 10px` on the hint was dropped (single child until the mockup's
      gauge glyph lands). Its third stands recorded: `color-mix` against the fixed `--neutral-000`
      rather than a surface token is safe only while `index.css` defines no dark palette.
      `/test-coverage frontend --focus` (filenames passed explicitly): `AiChatComposer.tsx`
      **100% statements / 100% branches (4/4) / 100% functions**, and 4/4 is the load-bearing number —
      both arms of the hint ternary *and* both arms of the new `ac-chat-box--disabled` className
      execute, so the box's live form is exercised too, not only the dead one. No steps owed.
      **What that clean report does not prove, stated rather than dressed up:** the box wrapper and
      its row are unconditional JSX, so rendering the component at all marks them covered — a wrapper
      nested wrongly, carrying the wrong class, or wrapping the wrong children reports identically.
      And `AiChatPanel.css` is not instrumented at all, so **zero** of this unit's styling work was
      verified by coverage. The correctness claim rests on the mockup comparison and on the Selenium
      layer. Worth recording against `carryover.md`: the `git diff HEAD --name-only` focus filter
      *did* list both files this time — one observation, not yet a reason to trust it.
      **Still absent, with their owners:** the `.msgs` transcript and `.time` stamps (the send/response
      scenarios); the `27 версий` count and revision rows (scenario 1.3, per `AiChatRevisions.tsx`'s
      own comment); the `.docnote-warn` band over the *document*, deliberately not ported since the
      panel states the limit once; the `Осталось правок сегодня: 0 из 20` counter, which needs
      `used`/`limit` off a quota API that 0.2 does not surface; the `.keys` line, unclaimed by any
      scenario; and the send/gauge icons — this app has no icon package, and `SparkMark` in
      `AiChatPanel.tsx` is the inline-SVG precedent if they are ever wanted.
      `/refactor` landed two changes over `cb15a798`. The send moved from `--accent`/`--text-inverse`
      to `--btn-primary-bg`/`--btn-primary-fg` — this is the app's *fourth* primary button and the
      other three all resolve through the pair `index.css:36-37` exists to keep from diverging;
      appearance-preservation was verified by alias identity (both pairs bottom out in `--blue-700`
      / `--neutral-000`, and there is one `:root` with no theme block that could split them). And
      `quota.exhausted`, restated four times, became one `const disabled` with the box's className a
      modifier-only template literal — the box, the input and the send now read the same fact from
      one place and cannot drift into disagreeing about which state they are in. 528 passed;
      tsc, oxlint, prettier clean; 69 / 127 lines.
      **Review-pass follow-ups — both CONCERNS, nine findings, and they land in the colour and
      interaction layer, which is exactly what neither jsdom nor coverage touches. The commit
      message's own "proves nothing about the stylesheet" is what these are.**
      (av) **The dead field is painted in the app's accent-emphasis tint — the one direction a dead
      field must not go.** `--bg-page` is `var(--blue-50)` and `--accent-soft` is *also* `var(--blue-50)`:
      the same colour, and the exact value the quota hint carried before this diff. The mockup's
      `--bg-sunken` is `#f7f8fa`, 2% off its white surface — a barely-there recession. So the reasoning
      recorded above ("`--bg-page` is this app's sunken surface") is where it goes wrong: `--bg-page`
      is the *page* colour. The over-quota box reads as highlighted, not recessed.
      (aw) **The documented two-surface deviation buys 1.16:1 and delivers nothing.** Disabled send
      `--bg-card-muted` `#d2e2f2` on the disabled box `#e3f2ff`; the button carries no border, so the
      edge the comment argues for is dissolved anyway — and both are blues, so the same comment's
      "the mockup greys the control" describes a treatment this code does not apply.
      (ax) **The disabled field's boundary is invisible**: `--border-subtle` `#d5e6f7` on `#e3f2ff` is
      1.11:1 against WCAG 1.4.11's 3:1 for a component boundary. (av)+(aw)+(ax) are ONE fix and must
      travel together — today the only screen this scenario ships collapses into a flat pale-blue
      rectangle with neither field edge nor button edge distinguishable. The mockup's equivalent pair
      reads only because it sits on white.
      (ay) **The band silently stops being a band on Safari < 16.2.** `color-mix()` sits in both the
      `background` and inside the `border` shorthand with no preceding fallback and no `@supports`;
      it is parse-time invalid where unsupported, so the *whole declaration* drops — background and
      border together — and the hint degrades to ordinary prose. There is no `browserslist` and no
      `build.cssTarget`, and esbuild does not downlevel it. One fallback declaration per property.
      (az) **`display: flex` on the hint will glue the countdown to the lead.** The component's own
      comment says a wall-clock tail is coming into this element; under flex a whitespace-only
      anonymous run between two child boxes is not a flex item, so the separating space vanishes and
      there is no `gap` to replace it (the `gap` was dropped this unit as inert). The flex does no
      work today either — `align-items: center` on one full-width item is a no-op. Drop it or gap it.
      (ba) **The visible field is larger than the clickable field** — and this one jsdom *can* catch.
      Before the diff every pixel inside the border focused the textarea; now the 14px ring and the
      whole row strip are dead, `.ac-chat-box` is a plain div with no `<label>` and no handler, and
      nothing anywhere focuses the input. `green-selenium` will not catch it either: `sendKeys` on a
      located element bypasses the click path. Owe a case that clicks the box and asserts
      `document.activeElement` is `ai-chat-message-input`.
      (bb) **No focus affordance on the thing that is now the field.** The border moved onto the box,
      nothing styles `:focus-within`, and the input never sets `outline: none` — so the UA ring draws
      14px *inside* the visible edge, a double edge, and the field itself never reacts. Both existing
      text inputs in the app pair `outline: none` with a `:focus` border-colour change.
      (bc) **The new `::placeholder` rule fails AA**: `--text-muted` `#797d81` on white is 4.15:1, and
      the placeholder is the only text saying what the field is for. `AuthForm.css:79` uses
      `--neutral-900` at `opacity: .7` instead; this diverges without a note.
      (bd) Guarding rather than merely fixing (av)–(ax) needs a computed-style or contrast assertion
      that exists nowhere in this suite. Worth deciding deliberately — by default it will not happen,
      and `green-selenium` as written in this repo (presence + attribute) would not have caught any
      of the nine.
- [S] green-selenium — **SKIPPED 2026-08-11: blocked on backend, re-verified live at HEAD.**
      `backend/application/src/app/main.py:116-119` still includes only `generation`, `auth`, `oauth`
      and `document` — `document_edit_router` is not registered — and `grep -rn quota
      backend/adapters/rest/src/router/` is still empty. Unblocking is backend-session work; per
      CLAUDE.md File Ownership this session writes neither `backend/` nor `progress-backend.md`.
      Un-skip this step (and `demo` below) once the backend registers the router and ships
      `GET /api/v1/ai-edits/quota`. Original blocker record follows.
      **BLOCKED on the backend, not started.** The step is remove-marker-only, so
      it may not be attempted against a stack that provably cannot serve it; the stack was not
      started and the marker was not touched. Both blockers named in the test's own RED comment are
      still live, verified at `f8acfebb`:
      1. **The AI-edit routes are unregistered.** `document_edit_router` exists
         (`backend/adapters/rest/src/router/document_edit/document_edit_router.py`, prefix
         `/api/v1/documents`, with `POST /{document_id}/ai-edits` and the stream route) but
         `backend/application/src/app/main.py:116-119` includes only `generation`, `auth`, `oauth`
         and `document`. So the setup probe still gets the `404 {"detail":"Not Found"}` its comment
         records, and the quota counter cannot be moved — the Given is unreachable.
      2. **`GET /api/v1/ai-edits/quota` does not exist at all.** `grep` over `backend/` finds the
         `ai_edits` table, its migration and its model, and no quota route anywhere. This is
         follow-up (at): the contract the frontend now calls lives only in frontend files, so on
         today's backend every editor open 404s and the composer is dead for 100% of users while
         looking exactly like it is still loading.
      **Unblocking is backend-session work** (a row in the shared `endpoints.md`, then a backend
      scenario), and per CLAUDE.md File Ownership this session does not write `progress-backend.md`
      or `backend/`. The frontend side of scenario 0.2 is complete through `align-design`.
- [S] demo — skipped with `green-selenium` above: a demo replays the Selenium test, which cannot run
      while the routes it drives are unregistered. Un-skip together.

### 1.1 The editor and chat panel render side by side with an empty history
- [x] red-selenium — one test,
      `acceptance/tests/frontend/ai_chat/test_empty_chat_panel_acceptance.py`, landed skipped.
      Predicted `TimeoutException` inside `_chat_panel_descendant` on
      `[data-testid='ai-chat-message-list']` — the **second** Then. Neither
      `ai-chat-message-list` nor `ai-chat-empty-state` exists anywhere under `frontend/src`
      (grep confirms). The first Then already passes (`EditorDocumentView` renders stored
      content, both document routes registered). Executable evidence only: 1 test collected,
      3 in the directory, 96 across `acceptance/`, 0 import errors, ruff clean.
      **The brief was stale and the correction matters:** `AiChatComposer.tsx` already exists
      — 0.2's green built it, input and send both `disabled={quota.exhausted}`. So the
      enabled-input Then is not red for want of a component; it is red because `AiChatPanel`
      withholds the composer until quota resolves, and `loadEditQuota` reads the unregistered
      `GET /api/v1/ai-edits/quota`, so `useEditQuota` stays `null` and nothing renders.
      **Unlike 0.2, this test's setup is NOT blocked** — it touches only `POST /documents` and
      `PUT /documents/{id}`, both registered. When Docker returns, run it for real before
      `green-selenium`: it should produce exactly the predicted `TimeoutException`, upgrading
      the RED evidence from prediction to observation. `save_document` (PUT) was added to
      `document_edit_client.py` for the Given — `POST /documents` creates an *empty*
      document, so without a write "the content is shown in the editor" asserts emptiness
      against emptiness.
      0.2's sign-in / row-click / panel-descendant helpers were extracted to
      `editor_route_statements.py` (an `EditorAccount` Protocol keeps the base ignorant of
      each scenario's extra fields) rather than copied; `over_quota_statements.py` 200→130.
      `/test-review` landed six fixes. The load-bearing one is the story's own recurring
      failure mode, found again: `_chat_panel_descendant` **claimed** panel scope in its
      docstring while waiting on a whole-document condition — a same-named element visible
      anywhere else satisfied the wait while the panel held none, and the `len(matches) == 1`
      assert then ran unsynchronised and failed with 0 rather than naming the scope. Now a
      panel-scoped poll filtered by `is_displayed()`, so a rendered-but-hidden element can no
      longer stand in for a visible one. Also: `is_enabled()` had no visibility companion on
      the input, the send control or 0.2's revisions toggle — `is_enabled()` is `True` for a
      `display:none` input, so "the message input is enabled" passed on a composer nobody can
      reach; `manual-editor` is carried by *both* story 5's `ManualEditor.tsx:158` and story
      19's `EditorDocumentView.tsx:31`, so a document-scoped text equality would read
      whichever came first in the DOM — pinned with an explicit count of 1; the fixed
      paragraph text stopped travelling through the test class (the Statements layer owns the
      constant); and the unique title sent to `POST /documents` was never verified, though it
      is the only field distinguishing this document from the account's others.
      **Verified explicitly that the shared-base extraction did not weaken 0.2:** all four of
      its assertions (row count, `data-document-id` identity, `_assert_url_path`,
      `len(matches) == 1`) are present verbatim in the base at lines 78/85/91/119. Net effect
      on 0.2 is two assertions *stronger*, zero weaker.
      One rejected finding worth recording: a shared `_assert_composer_enabled(driver,
      expected: bool)` across 1.1 and 0.2 — a boolean-flag assertion helper makes the
      assertion's meaning depend on an argument, and it would couple 0.2's committed
      assertions to 1.1's.
      **Pre-existing, out of unit:** `ruff check .` over `acceptance/` reports 10 `F401`
      unused-`pytest` imports in untouched files (1 backend, 8 frontend/auth, 2
      frontend/generation) — the suite lints red until someone clears them. This is
      follow-up (e) from scenario 0.1, still open.
      `/refactor`: **NO ACTION.** It judged the deferred duplication finding (the three-step
      open sequence) and rejected it on merit: the sign-in and row-click halves are already
      *in* the base, so what remains per scenario is a factory call plus two named base calls,
      and the factory is the single most important fact in each Given — hiding it behind a
      callable makes the reader chase a function object to learn which account a scenario
      opens. A wrapper would add four lines to the base to remove one from each of two
      callers.
      **All three agents independently found the same defect in this unit's own setup, and it
      was fixed in the follow-up commit — the RED prediction recorded above was wrong.**
      `_create_empty_document` asserted `body["title"]`, but `create_document`'s third
      argument is the `Idempotency-Key` **header**, not a title: `CreateDocumentRequestDto`
      accepts `document_type` alone and `DocumentResponseDto` carries no `title` field. It
      raises `KeyError: 'title'` unconditionally, in the Given, before any Then — so against a
      live stack this test would have failed in setup, not with the predicted
      `TimeoutException`. The irony is that the line came *from* a `/test-review` fix ("the
      unique title was sent but never asserted"): it was never sent as a title, the reviewer
      read an idempotency key as one. The sibling `over_quota_session` passes the same string
      in the same slot and correctly asserts only `(document_type, version)`. The docstring
      rationale went with it — the row is pinned by `data-document-id`, not by a title.
      Also fixed in the same commit, because the extraction is what introduced it: the
      panel-scoped poll captured `panel` **once** and then polled `panel.find_elements`, while
      `WebDriverWait` ignores only `NoSuchElementException` by default. This panel re-renders
      under the test's own feet — `AiChatPanel` swaps its notice for the composer when the
      quota read settles — so a swap mid-poll raises `StaleElementReferenceException` straight
      out of `.until()` and the scenario dies with a driver error instead of the scoped
      timeout the helper exists to produce. The panel is now re-resolved inside the lambda and
      both exceptions are ignored. This one is on 0.2's committed path too.
      **Review-pass follow-ups (both CONCERNS), for `red-frontend`/`green-frontend` and
      `green-selenium`:**
      (be) **`data-document-id` exists nowhere under `frontend/src`, and the extraction spread
      the dependency.** `editor_route_statements.py` requires it on the row;
      `HistoryPage.tsx:90-97` renders a `<button>` carrying only
      `data-testid="history-document-row"`. So the Given of 0.2 *and* 1.1 — and every future
      scenario built on `EditorRouteStatements` — fails at the click, again not with the
      predicted timeout. `HistoryPage.test.tsx` asserts row text and click behavior but never
      the attribute, so the frontend suite stays green while the acceptance base is
      un-runnable. Owe a `HistoryPage` case pinning the attribute to the fixture's
      `documentId`. **Fix this before the stack comes back**, or the first real run reports
      two scenarios failing for a reason none of their prose predicts.
      (bf) **Every assertion in this scenario is satisfied by a chat panel that can never show
      a message.** The document is pristine by construction, so an `ai-chat-message-list` that
      renders nothing under any condition and an unconditional `ai-chat-empty-state` are
      green here — and scenario 1.2 (restored history) is unwritten. Owe an `AiChatPanel` case
      with a non-empty history mock asserting `ai-chat-empty-state` is null *and* at least one
      `ai-chat-message-*` row renders inside the list.
      (bg) **The cheapest green for "the message input is enabled" turns a failed quota read
      into permission to type.** `AiChatPanel.tsx:39` withholds the composer while
      `quota === null`, and `useEditQuota.ts:31` collapses a *rejected* read into that same
      `null`; flipping that branch satisfies this Then and silently converts "quota unknown"
      into "typing allowed" — users burn instructions that all bounce off a server-side 429.
      `DocumentEditorPage.overQuota.test.tsx` only ever `mockResolvedValue`s, so the catch
      branch has no test observing the resulting UI. Owe a `mockRejectedValue` case.
      (bh) **The "no messages" check is an unsynchronised negative** — `assert not messages`
      runs the instant the list becomes visible, so once 1.2 introduces an async history read
      it passes for the wrong reason on any document. The base's own `_assert_absent` docstring
      warns about exactly this. Needs a positive anchor (a settled marker on the list); the
      empty-state assertion that follows only accidentally orders it.
      (bi) **`save_document` in the Given may write a baseline revision holding empty content.**
      `endpoints.md:53-55`: a document with no history gets a baseline revision on its first
      mutation, holding the *pre-mutation* content — which here is empty. Whether a manual PUT
      counts is unresolved, and 1.1 never opens the revisions panel. Owe an assertion that
      `GET /documents/{id}/revisions` is empty for the pristine document — it either confirms
      the Given's name or exposes that rollback would offer a blank page.
      (bj) Low: `assert_the_document_content_is_shown_in_the_editor` passes the *locator* to
      `_assert_element_text_equals`, which re-resolves document-wide, so the `len(editors) == 1`
      assert above it is advisory rather than load-bearing. Pass `editors[0]`.
- [x] red-frontend — four cases across three new files plus one added to `HistoryPage.test.tsx`.
      Three fail genuinely and land skipped; the fourth lands **un-skipped** on this story's
      `42ba5d94` precedent, since it pins an already-correct guard and only a mutation can
      redden it.
      Predicted and got, per case: `TestingLibraryElementError: Unable to find an element by:
      [data-testid="ai-chat-message-list"]` in both `DocumentEditorPage.emptyChat.test.tsx:121`
      and `AiChatPanel.history.test.tsx:44`; `Expected the element to have attribute:
      data-document-id="doc-1" / Received: null` at `HistoryPage.test.tsx:86`; and — under
      mutation only — `AssertionError: expected <textarea …> to be null` for the quota case.
      **Three review-pass follow-ups from the Selenium unit are closed here**, which is the
      point of the unit: (bf) `AiChatPanel.history.test.tsx` renders a non-empty history and
      requires the empty state to be *absent* while message rows are present — without it,
      an `ai-chat-message-list` that renders nothing under any condition and an unconditional
      `ai-chat-empty-state` satisfy the whole scenario, because 1.1's document is pristine by
      construction; (bg) `DocumentEditorPage.quotaReadFailed.test.tsx` pins that a *rejected*
      quota read withholds the composer rather than becoming permission to type; (be)
      `HistoryPage.test.tsx` now requires `data-document-id` on the row — the attribute the
      acceptance base needs and that exists nowhere under `frontend/src`, so this unblocks the
      Given of both 0.2 and 1.1 at the click step.
      **`/test-review` found the un-skipped case vacuous, and this is the finding of the unit.**
      Mutation-tested as instructed, it killed only 1 of 3 mutants: deleting `useEditQuota`'s
      `.catch` **survived**, and deleting the `act(reject)` block entirely **survived**. Root
      cause: a rejected read and an in-flight read render an identical panel — `useEditQuota`
      collapses both to `null` — so every assertion in the file was satisfied by the *pending*
      state. The file's whole stated purpose was untested; it was testing the loading screen.
      Fixed with a settlement barrier (`await expect(quotaRead).rejects.toThrow(...)` before the
      DOM assertions, so a test that stops firing the rejection hangs rather than passes), an
      `unhandledRejection` listener asserted empty at the end — which is what actually pins the
      `.catch`, since our own `.rejects` handler attaches to the base promise and not to the
      derived `.then` chain the escape travels — and `toHaveBeenCalledExactlyOnceWith` on both
      reads, which the file had omitted while both its siblings pin them. All three mutants now
      die. `process` is reached through a locally-typed `globalThis` destructure: this app has
      no `@types/node` and adding one would be a build-config change riding in on a test review.
      Second fix: `toHaveLength(HISTORY.length)` in the history case agreed with itself under any
      edit to the fixture — replaced with a literal `EXPECTED_ROW_COUNT = 2`.
      Rejected findings worth keeping: `screen.findByTestId(MANUAL_EDITOR)` *looks* like the
      container-scope violation this story keeps hitting, but `findByTestId` throws on multiple
      matches, so it enforces the same uniqueness the acceptance layer spells out as
      `EXPECTED_MANUAL_EDITOR_COUNT = 1` (needed because story 5's `ManualEditor.tsx:158` shares
      the testid). `toContain` on row text stays: the mockup renders each `.msg` with a `.mark`
      glyph and a sibling `.time`, so exact `textContent` equality would forbid markup the
      mockup already specifies and force scenario 1.2 to edit a 1.1 test. `ChatMessage.role` and
      `.messageId` stay unasserted — pinning them means inventing `data-message-role`/
      `data-message-id`, which is **scenario 1.2's** spec; deferred to a named sequenced owner,
      not to "later".
      **The third Then got no case of its own, deliberately:** `DocumentEditorPage.overQuota
      .test.tsx:173` already asserts input and send enabled through this same page for a
      within-quota account (verified line by line). What 1.1 genuinely adds there is the
      failed-read guard, which is the un-skipped file.
      RED plumbing audited and inert: `AiChatPanel.tsx` is `+14/-0` — an exported `ChatMessage`
      interface and a `messages` prop **not destructured** by the body, no list, no empty state,
      no branch; `DocumentEditorPage.tsx` passes `messages={[]}`. Both skipped describes were
      un-skipped temporarily and fail with the predicted locator error, not a crash.
      529 passed / 0 failed / 3 skipped (121 files passed, 2 skipped); tsc, prettier and oxlint
      clean. The 3 skips are exactly this unit's three RED markers.
      **Green's scope is four things:** `ai-chat-message-list` (always rendered), a
      **conditional** `ai-chat-empty-state` carrying the exact sentence `Документ готов.
      Напишите, что нужно изменить — я поправлю текст и сохраню новую версию.`, message rows
      under the `ai-chat-message*` prefix, and `data-document-id` on the row button at
      `HistoryPage.tsx:90-97`.
      Untouched by this unit and still open from the Selenium one: (bh) the unsynchronised
      negative in `empty_chat_panel_statements.py`, (bi) the baseline-revision question, (bj)
      the re-resolving locator. Follow-up (ak) was not pulled in — it did not fall out of any
      case here and belongs to the AI-applied-edit scenarios.
      `/refactor`: **NO ACTION**, with three duplication candidates found and each rejected on
      merit. The one with teeth: `ANY_MESSAGE = '[data-testid^="ai-chat-message"]'` is used
      asymmetrically across the two chat files — `history` asserts presence, which goes loudly
      red if the prefix stops matching, while `emptyChat` asserts emptiness, which goes
      *silently vacuous*. Extraction was still rejected because the actual source of truth for
      these names is `empty_chat_panel_statements.py`, which TypeScript cannot import, so a
      shared TS constant would sync the two TS copies with each other and not with the layer
      that defines them — drift resistance against the wrong axis. Also rejected: sharing the
      render/mock harness with `overQuota.test.tsx`, because `vi.mock` is hoisted per file and
      cannot move into a support module — a shared harness would leave the mocks behind and
      fail at runtime with "not a mock" rather than at compile time.
      **Two review-pass findings were fixed in the follow-up commit**, both being this unit's
      own defects: the progress file listed `green-frontend` **twice** (the edit added a `[~]`
      line while the scenario's original `[ ]` line was still below it), which would have made
      `/continue` run a second green pass with no red ahead of it against an
      already-implemented scenario; and `ChatMessage`'s comment claimed the tests read all
      three of its fields when they read only `text`, in the very file scenario 1.2 inherits.
      **Review-pass follow-ups (both CONCERNS), for `green-frontend` and later:**
      (bk) **Nothing pins that a row's `data-document-id` and the id its own `onClick` passes
      are the same document.** Every `HistoryPage` case uses the single-item `DOC` fixture and
      `findByTestId`, which throws on multiple matches, so the file structurally cannot hold a
      multi-row case as written; the acceptance base cannot cover it either
      (`EXPECTED_DOCUMENT_ROW_COUNT = 1`, then `rows[0]`). With exactly one row, a green that
      sources the attribute from a different expression than the click handler is green at both
      layers — and the user-visible failure is the AI rewriting a document they never opened.
      Needs `findAllByTestId` and two rows, asserting per row that the attribute equals the id
      that row's click passes.
      (bl) **The unit layer never checks the composer is *visible*, and the omission is
      justified by a case that does not check it either.** `emptyChat.test.tsx:34-38` defers the
      third Then to `overQuota.test.tsx:173`, but that case is `findByTestId` + `toBeEnabled` —
      absence and the `disabled` property, never visibility. The acceptance layer explicitly
      refuses to accept that as sufficient, in `assert_the_message_input_is_enabled`'s own
      comment. So the two layers are not duplicates: the unit layer asserts strictly less, and
      the composer is the one element in the panel whose visibility nothing under `frontend/src`
      checks. If green's new list/empty-state markup collapses or overlaps the composer box,
      529 vitest cases stay green and only the blocked Selenium scenario would catch it. Same
      gap, smaller, in `AiChatPanel.history.test.tsx:44`: the list is taken with `getByTestId`
      and only `querySelectorAll`ed, so a `display:none` list satisfies the non-empty case.
      (bm) **The passing quota test cements the loading notice as the correct answer to a
      failure.** `useEditQuota` collapses rejection to `null` with a once-per-mount ref — no
      retry, no error state — and `quotaReadFailed.test.tsx` now asserts `CHAT_PANEL_NOTICE`
      ("Проверяем дневной лимит правок…") is visible, framed in-file as "the positive anchor".
      Scenario 8.8, which the hook's own comment names as owner of the failure screen, cannot
      ship an error message or a retry without turning this test red. A deferral a test forbids
      is not a deferral: mark the anchor provisional in the file, or the endpoint 500ing leaves
      every user staring at "checking your daily limit" forever with nothing saying it failed.
      (bn) **After green there will be three independent copies of the empty-state sentence**
      (component, vitest, `empty_chat_panel_statements.py`) and only the first two can be
      mechanically tied. This file breaks its own pattern: `quotaReadFailed.test.tsx` *imports*
      `CHAT_PANEL_NOTICE` from `AiChatPanel`, while `emptyChat.test.tsx` hardcodes the sentence.
      Green should export `CHAT_EMPTY_STATE_TEXT` and have the test import it. The
      frontend↔acceptance copy stays uncheckable by construction; the frontend↔vitest one need
      not be. Verified byte-identical today — the drift is future, not present.
      (bo) **Nothing mechanically requires the three skips to disappear at green.** Un-skipping
      is a manual edit in three places across three files; vitest does not fail on a non-zero
      skip count and there is no `allowOnly`-style gate in `vitest.config.ts`. A green that
      satisfies two and forgets the third reports "passed, 1 skipped", which reads as normal.
      Green's verification must pin `0 skipped` explicitly, not diff a count against a
      paragraph. (This is follow-up (l) from `green-frontend` 0.1, recurring — it is now a
      pattern, not an incident.)
      Rated REMOTE and not owed: `DocumentEditorPage.tsx` passes a literal `messages={[]}`, so
      the conditional branch is exercised only by a direct panel render, never through the page.
      Scenario 1.2 owns the read and its page-level tests would redden on a forgotten
      thread-through.
- [x] green-frontend — 532 passed / 0 failed / **0 skipped** (was 529/3); tsc, prettier and
      oxlint clean. (bo) honored explicitly: vitest printed no skipped bucket at all across
      the whole `frontend/src` suite, so all three un-skips demonstrably landed rather than
      two of them landing and the count reading as normal.
      An internal `AiChatHistory` renders `ai-chat-message-list` **unconditionally** — it is
      where messages go, and a region that appears only once a message exists would have to be
      built twice — with `ai-chat-empty-state` as the conditional half, present only at
      `messages.length === 0`. Rows carry `text` alone, keyed by `messageId`; ordering and the
      per-side split stay scenario 1.2's.
      (bk) closed by construction rather than by a test: the attribute and the `onClick` read
      the **same `d.documentId`, in the same `items.map` callback, three lines apart** — no
      index, no memoised outer value, no second expression to diverge through. The single-row
      fixture that made the divergence invisible is unchanged; what changed is that there is
      now nothing to diverge. A comment on the line says why.
      (bn) partially closed: `CHAT_EMPTY_STATE_TEXT` is exported from `AiChatPanel.tsx` beside
      `CHAT_PANEL_NOTICE`. **Rewiring `emptyChat.test.tsx`'s `EXPECTED_EMPTY_STATE_TEXT` to
      import it is OWED** — changing a test's imports is beyond "remove the skip marker", so
      green declined it rather than widening its own licence. Until that lands the copies are:
      component (exported), vitest (hardcoded), `empty_chat_panel_statements.py` (Python,
      unshareable by construction). Two is the floor; three was avoidable.
      (bl) answered in CSS and **guarded by nothing executable, stated plainly**: `.ac-chat` is
      a flex column and the new history takes `flex: 1; min-height: 0; overflow-y: auto`, so a
      populated list scrolls inside itself instead of pushing `.ac-chat-composer` (which keeps
      its `margin-top: auto`) out of the column. jsdom applies no layout, so no vitest case can
      catch a regression here, and no Selenium case asserts composer visibility against a
      **non-empty** conversation either — the only composer-visibility assertion in the repo is
      the acceptance layer's, against a pristine document with an empty list. The first real
      guard would be a Selenium case with a populated conversation. This is the same shape as
      (af) from `align-design` 0.2: a scrolling model no jsdom test can see.
      `/refactor`: **NO ACTION.** Its sharpest rejection is worth keeping: `.ac-chat-empty` and
      `.ac-chat-message` share three declarations and differ only in `color`, but scenario 1.2
      owns the per-side split, which gives `.ac-chat-message` its own background, alignment and
      max-width while the empty state is a single centred paragraph that gets none of that —
      merging now creates a coupling the very next scenario has to unpick. `AiChatPanel.tsx` at
      94 lines stays one file: `frontend-rules.md` keeps a helper used by one view in that
      view's file.
      **Fixed in the follow-up commit** — the `ChatMessage` comment written by the previous unit
      now contradicted the code it sits above. It said scenario 1.1 reads `text` and NOTHING
      ELSE; green keys every row by `messageId`. The comment now separates the two axes it was
      conflating: read-by-an-assertion (`text` alone) versus read-by-the-code (`messageId`, as
      the React key, pinned by nothing).
      **Review-pass follow-ups (both CONCERNS), for scenarios 1.2 / 1.3 and later:**
      (bp) **"Empty" and "unknown" are the same value, so a failed history read renders the
      empty state.** `messages` is a non-nullable `ChatMessage[]` and `AiChatHistory` branches
      on `length === 0` alone, so there is no representable third state. On a 500 the panel says
      "Документ готов. Напишите, что нужно изменить…" to a user whose earlier instruction *did*
      land — they retype it, burn a quota unit and stack a second AI revision on a document that
      already has one. Scenario 1.3 owns the fetch-error state but now has to *widen a shipped
      prop type* to have anywhere to put it, and `emptyChat.test.tsx` asserts the empty state on
      a page whose history read is not mocked at all — so "unknown → empty state" is the path
      the suite currently rewards. Distinct from the recorded REMOTE about `messages={[]}`:
      that is 1.2 forgetting to thread the read through; this is the type and branch shipped
      here making the failure silent. Cheapest fix: `messages: ChatMessage[] | null` plus a case
      asserting the `null` state renders neither rows nor the empty state.
      (bq) **The populated case never asserts the composer is still present, and that half is
      not a layout problem.** `AiChatPanel.history.test.tsx` asserts panel, absent empty state
      and two rows — never `ai-chat-message-input`. An implementation rendering the history
      *instead of* the composer whenever a conversation exists passes it, passes the pristine
      page-level test (composer asserted there, empty history) and passes acceptance (pristine
      by construction). (bl) covers *visibility*, which jsdom cannot see; presence in the DOM it
      can. One assertion in the existing populated test closes it.
      (br) **Duplicate or absent `messageId` silently drops rows.** Green keys rows by it and no
      test pins uniqueness; both fixtures use distinct `m-1`/`m-2`. Streamed assistant turns
      before persistence assigns an id, or a wire field actually named `id`, make React reuse or
      drop rows with every layer green. Owe a two-message case sharing one id asserting both
      texts still render — or key by index and let 1.2 introduce the id key with its own guard.
      Related and undocumented until now: every row carries the same
      `data-testid="ai-chat-message"`, so `getByTestId` on a populated list throws; both current
      layers happen to use `querySelectorAll`, and 1.2 will trip it.
      (bs) **The new scroll container never scrolls to the newest turn.** `.ac-chat-history` has
      `overflow-y: auto` and nothing anywhere under `frontend/src` calls `scrollIntoView` or
      sets `scrollTop` (zero hits). On a dozen turns the panel shows the *oldest* messages and
      the user reports "the AI didn't respond". Unlike (bl)/(af) this one **does** have an
      executable guard available before Selenium — jsdom can spy on `scrollIntoView` even though
      it cannot verify the layout.
      (bt) **The most frequently-updating region in the app has no live semantics**, against
      this repo's own tested convention: `AuthLoadingIndicator.tsx` uses
      `<output aria-live="polite">` and `LoginForm.test.tsx:133` / `RegisterForm.test.tsx:41`
      assert it. `.ac-chat-history` is a bare `<div>` with no `role`, no `aria-live` and no
      accessible name; rows are bare `<p>`. A screen-reader user hears nothing when a reply
      arrives and re-sends. Sits beside the open accessibility follow-ups (av)–(bc).
      (bu) **`.ac-chat-history` is the only shrinkable sibling in the column, so the conversation
      can collapse to zero height.** `min-height: 0` is what lets the composer stay put; it is
      also what lets the history shrink to nothing. The head is not fixed — `AiChatRevisions`
      renders its panel *inline inside* `.ac-chat-head` — so opening revisions grows the head,
      and with `.ac-chat-quota-hint` on a short viewport the history absorbs all of it, showing
      no messages and no scrollbar while `.ac-chat`'s own `overflow: auto` never fires. Symptom
      is the *messages* vanishing, not the composer, so it is a different failure from (bl). No
      `min-height` floor.
- [x] red-frontend-api — nine cases over `loadChatMessages` in
      `api/__tests__/chatMessagesApi.test.ts`, covering `GET /api/v1/documents/{id}/messages`
      (`endpoints.md:9`). All nine fail against the stub's unconditional
      `Not implemented: loadChatMessages(<id>)`: the two happy paths as
      `promise rejected … instead of resolving`, the four page-guard cases on
      `expected 'Not implemented…' to be 'Не удалось загрузить историю чата'`, the 404 on
      `… to be 'Document not found'`, and the session case one assertion earlier on
      `… to be an instance of SessionExpiredError`. The two `resolves` cases fail **at the
      matcher**, not inside `httpClient` — no fetch was reached, so nothing passed vacuously.
      **Decisions this unit made, each pinned by a case rather than only argued:**
      The messages read deliberately does **not** opt into `refusals.notFound`. The page's
      *document* read already opts in and owns the not-found blocker; a 404 reaching the
      history read while the document loaded fine is the history endpoint failing — scenario
      1.3's panel — and `DocumentNotFoundError` there would blank the whole editor over a
      broken sidebar. The `send.ts` opt-in design from `green-frontend-api` 0.1 is untouched.
      **That closes (x), and `/test-review` verified it by mutation rather than by argument:**
      deleting the `refusals.notFound &&` conjunct in `send.ts` — making the mapping
      unconditional for every caller — fails **exactly one case in 540**, this file's
      `keeps the shared 404 as a described generic failure`, with
      `AssertionError: expected 'DocumentNotFoundError' to be 'Error'`. This is the only case
      anywhere holding the opt-in guard, which previously had zero coverage.
      **Correction, caught by the review pass: (x) is closed CONDITIONALLY on green un-skipping,
      and the commit message states it unconditionally.** The mutation run necessarily had the
      block un-skipped (540 cases, not the 532 this commit reports). As of `e3804d36` the case
      sits inside `describe.skip`, so deleting `refusals.notFound &&` from `send.ts:110` still
      leaves the suite green — exactly the condition (x) describes. Nothing is wrong with the
      test; the record was overstated. Treat (x) as closed at `green-frontend-api`, not here.
      **(bp)'s client half is closed:** a 200 that does not carry a page — `{}` from
      `res.json().catch(() => ({}))`, or a non-list `items` — **rejects** rather than mapping
      to an empty conversation. An empty-defaulting client is precisely what would make a
      failed read render "Документ готов…". Widening `messages` to `ChatMessage[] | null`
      stays 1.3's.
      **(bn) closed:** `emptyChat.test.tsx` now imports `CHAT_EMPTY_STATE_TEXT` from
      `AiChatPanel` instead of retyping it. Three copies down to two; the Python acceptance
      copy is unshareable by construction.
      `/test-review` landed three fixes plus the mutation verification. The load-bearing one is
      in the **shared** helper: `expectErrorIdentity` asserted `toBeInstanceOf(Error)`, which is
      true of every thrown error, so on the four generic-failure cases the entire discriminating
      load fell on `name` — and `name` reads `'Error'` for a subclass only by accident of that
      subclass assigning `this.name`. Now also `expect(error.constructor).toBe(type)`. Verified
      by mutation: with a green throwing `class ChatHistoryError extends Error {}` and no `name`
      assignment, 5 refusal cases fail with the check and **4 of those 5 passed without it** — a
      green inventing a nameless error subclass would have walked through this file *and* both
      sibling api test files. Also: `toEqual`→`toStrictEqual` on both `requestedUrls` lists
      (`requestedUrls` returns `unknown[]`, so `toEqual` tolerates holes and array-likes); and a
      **ninth case added** because `next_cursor` had no type guard — `nextCursor: string | null`
      is a promise the module's own exported type makes, and a green written as
      `body.next_cursor ?? null` passed all eight existing cases while typing an arbitrary value
      `string` by declaration alone. Scenario 1.2 is the first to send the cursor back and would
      interpolate `[object Object]` into a query string.
      Rejected findings worth keeping: no 500 case, because in `send.ts` a 500 reaches
      `new Error(describeFailure(...))` by a strict *subset* of the 404 case's path — the 404
      case exercises that same final line having additionally traversed the notFound branch
      without firing it, so it is strictly stronger, not merely equivalent. No verb pin on the
      404 case: the request is fully constructed before any response arrives, so no branch lets
      a 404 alter the verb of a request already sent.
      Other pins: the URL is `toBe` with **no query string** — `limit` has a server-side default
      and `cursor` is absent on the first page, so a client spelling either out states a policy
      the contract owns; the return is a `ChatMessagePage`, not a bare array, because the
      endpoint is keyset-paginated by contract and an array asserts "this is the whole
      conversation"; `nextCursor: null` comes from an **absent** key, pinned with
      `toStrictEqual`; and the 404 case sends `doc-gone`, not `doc-1`, so path interpolation is
      pinned — every other case would pass for a hardcoded path.
      (z) not repeated: the module imports only `shared/api/send`, no peer-feature import.
      532 passed / 0 failed / **9 skipped**; tsc, prettier, oxlint clean. The 9 skips are this
      unit's single `describe.skip` and nothing else.
      **Owed to green or `/refactor`:** the duplicate `ChatMessage` (this api module vs
      `AiChatPanel`) is held only by a compile-time `expectTypeOf<ChatMessage>()
      .toEqualTypeOf<PanelChatMessage>()` gate — moving a shipped production type is beyond a
      RED phase's licence, so consolidation is owed. **Note the file is 192 of 200 lines: a
      tenth case forces a split.** Green must also report **0 skipped** explicitly, per (bo).
      **Recorded, not fixed:** `emptyChat.test.tsx:103` carries a stale `// RED:` comment
      claiming neither `ai-chat-message-list` nor `ai-chat-empty-state` exists anywhere under
      `frontend/src`. Both exist at `AiChatPanel.tsx:64,66` and the test passes — narrative in a
      file greened by a prior unit, not an assertion defect, but it will mislead the next
      reader. And `editorDocumentApi.test.ts:93,103,123,139` still use `toEqual` on
      `requestedUrls` — same looseness as fix 2, but committed green tests outside this unit's
      file set.
      `/refactor` landed two changes over `e3804d36`. The file was **201 lines, over the hard
      limit** — the three chat-specific support declarations moved into `aiChatApiFixtures.ts`
      (151→176), the same support seam `editorDocumentApiFixtures.ts` took, so all nine cases
      and the single `describe.skip` stay in one file and no `vi.mock` block is duplicated
      (190 lines now). And the OWED `ChatMessage` duplication was consolidated: one declaration
      in `chatMessagesApi.ts` — the api layer is where the wire rename lands — with
      `AiChatPanel.tsx` importing it exactly as it already imports `EditQuotaState` from
      `../api/editQuotaApi`, so this is the feature's existing direction rather than a new one
      (panel 96→84 lines). The `expectTypeOf` gate was **re-anchored, not dropped**: with one
      declaration a type-to-type comparison is tautological, so it now pins the panel's *prop*
      (`ComponentProps<typeof AiChatPanel>['messages']`), which catches the same divergence the
      two-copy version existed to catch. Verified by mutation — widening the prop with an
      optional `at?: string` fails the build with `TS2344`.
      **Toolchain finding worth acting on repo-wide: `npx tsc --noEmit` is a NO-OP here.**
      `frontend/tsconfig.json` is `{"files": [], "references": [...]}`, so a bare
      `tsc --noEmit` compiles zero files and exits 0. Every type-level claim ever "verified"
      with that command was verified by nothing; the real check is `npm run typecheck`
      (`tsc -b`). Every `expectTypeOf` in this feature is enforced only under `tsc -b`.
      Pressure point for green: `aiChatApiFixtures.ts` is at 176 lines with ~24 left, and
      `green-frontend-api` will likely add wire fixtures there.
      **Review-pass follow-ups (both CONCERNS):**
      (bv) **A 404 on the history read after a successful document read is the wrong diagnosis,
      and the spec says so in its own words.** This unit's header argues a history 404 means
      "the history endpoint failing", but `api-specs/documents_messages_list.yaml` documents its
      404 as *"No document with this id FOR THIS OWNER — byte-identical for absent and foreign;
      never 403."* There is no documented 404 on this endpoint meaning "history is broken". The
      rationale holds for the *concurrent* case (both reads in flight, document read
      authoritative) and fails for the *sequential* one: a document deleted in another tab after
      the document read resolved gives a live, editable editor beside a broken sidebar, with
      every save failing and nothing telling the user the document is gone. Owe a page-level
      case in 1.3 or 8.8 that a messages-404 arriving after a successful document load reaches
      the not-found blocker — which makes this file's ownership claim executable rather than
      argued.
      (bw) **A truncated conversation is indistinguishable from a complete one at the call
      site.** `documents_messages_list.yaml` fixes order oldest-first with `limit` defaulting to
      50, and the URL is pinned with no query string — so page one is the *oldest* 50. The one
      case producing a non-null cursor asserts only that the string is carried; `messages` is a
      plain array and a consumer that never reads `nextCursor` type-checks cleanly. The user
      sees a conversation stopping mid-history, re-sends the instruction that already ran, and
      pays a second quota unit and a second revision. Either make incompleteness unrepresentable
      (`{ complete: true } | { complete: false, nextCursor }`) or owe an explicit 1.2 case that
      a first page with a cursor triggers a follow-up fetch.
      (bx) **One unknown row loses the whole conversation, and the blast radius is unmeasured.**
      Both shape-guard cases stub `items` containing exactly one row, which is the bad one, so
      nothing states whether a bad row *among good ones* drops that row or rejects the page —
      and rejecting is the only behavior the file demonstrates, so it is what green will ship.
      When the backend adds a third message kind (a system notice, a tool marker, an
      `edit_id`-only placeholder for a failed edit), every user holding one loses their entire
      history to a deterministic, unrecoverable failure. Owe `items: [MESSAGE_WIRE, badRow]`
      asserting which policy holds. Also missing from the same table: `text: 42` (the current
      case covers only an *absent* key, so `typeof m.text !== 'undefined'` passes while `{}`
      reaches React as `[object Object]`) and a non-string `message_id`, which becomes a React
      key.
      (by) The 404 case pins `'Document not found'` — **English, in an all-Russian UI**.
      `describeFailure` prefers `body.message` over the fallback, so that is the sentence this
      client hands 1.3's panel. Declining the `refusals.notFound` mapping also declined the
      *localization* the mapping carried, which is not addressed anywhere; 1.3 will render it or
      override it. Nothing asserts UI strings are Russian.
      (bz) Minor: the second happy path drops the `stubFetch` return, so unlike the first it
      pins neither call count nor URL. Effectively guarded only because there is one stubbed
      response and a second call would hit the default throw — the asymmetry looks unintentional.
- [x] green-frontend-api — **541 passed / 0 failed / 0 skipped** (124 files), up from 532/9;
      all nine cases report *passed* individually. `npm run typecheck` (`tsc -b`), prettier and
      oxlint clean. (bo) honored by absence *and* arithmetic: the `skipped` line is gone from
      the summary entirely, and 532 + 9 = 541.
      `loadChatMessages` is 97 lines over `send`, modelled on the sibling `editQuotaApi.ts`:
      `GET /api/v1/documents/${documentId}/messages`, no query string, `{}` options, fallback
      `'Не удалось загрузить историю чата'`, **no `refusals` argument**. `mapPage` refuses a
      non-array `items`; `mapMessage` refuses a non-object row, a non-string `message_id`/`text`
      and a `role` outside the enum; `mapCursor` returns `null` for absent **or** null and
      refuses anything else non-string. All four throw the same fallback-message plain `Error`.
      **(x) is now genuinely closed, and verified by mutation at this step rather than claimed
      at the last one.** Deleting the `refusals.notFound &&` conjunct — at `send.ts:106`, not
      110; the line had moved — gives 1 failed / 8 passed in this file, on
      `keeps the shared 404 as a described generic failure`, with
      `AssertionError: expected [Function DocumentNotFoundError] to be [Function Error]`. Note
      the text differs from the prediction `expected 'DocumentNotFoundError' to be 'Error'`:
      that is `expectErrorIdentity`'s **new constructor check firing one assertion earlier** than
      the `name` check — the same defect caught sooner, which is the fix from the RED unit paying
      off immediately. Restored; `git diff --quiet src/shared/api/send.ts` exits 0.
      **(by) answered, and the answer is worse than the follow-up assumed: the shipped client
      CANNOT produce a Russian message for a history 404 at all.** `describeFailure` returns
      `body.detail ?? body.message` whenever it is a non-blank string and only falls through to
      `` `${fallback} (HTTP 404)` `` when the body carries no usable text — and this endpoint's
      404 always carries `message`. So the Russian fallback is *unreachable* for a real 404;
      whatever the server says, in whatever language, is what reaches 1.3. Opting into
      `{ notFound: true }` is the only lever inside this module and this unit's design rules it
      out. **The consequence for 1.3: it must NOT render `error.message` verbatim** for the
      history panel — it needs its own Russian copy and must treat the thrown `Error` as a
      signal, not as display text. That is the discipline `useGeneration.ts:89` and
      `useHistoryList.ts:52` already get wrong by rendering `error.message` straight through.
      (bz) answered: a double fetch **would** have been caught, though not by the assertion the
      follow-up wanted. `stubFetch`'s default implementation throws
      `'fetch called more times than the test stubbed'` and that case stubs exactly one response,
      so a second call fails as an unexpected rejection rather than on a count. A wrong *URL*
      there still would not be caught — only the first happy path and the 404 case pin that. The
      shipped client issues exactly one `send` call with no retry, proven by the first happy
      path's `toHaveBeenCalledTimes(1)`.
      Only test change: `describe.skip` → `describe`, plus deleting the RED paragraph above it.
      `aiChatApiFixtures.ts` untouched at 176 lines — green added no wire fixtures, so the
      ~24-line headroom the refactor flagged is still there.
      Incidentally resolved: the pre-existing prettier warning on
      `DocumentEditorPage.notFound.test.tsx`, recorded as out-of-unit debt since
      `green-frontend` 0.1, no longer appears.
      `/refactor`: **NO ACTION**, and its rejection is the interesting part. All three api
      modules are now thin `send` wrappers, but what they share is a *pattern* — import `send`,
      a `FALLBACK` const, a wire interface of `?: unknown` keys, a `map*` that throws — not
      shared code: beyond the literal token `throw new Error(FALLBACK)` there is not one
      statement in common, because the guard **is** the fact that distinguishes each endpoint.
      It also rejected sharing `mapCursor` with `historyApi.ts`, and correctly: that module
      declares `next_cursor` as a typed wire field and passes it through unguarded, so unifying
      would add throws to two shipped list endpoints in another feature — a behavior change, not
      a refactor.
      **Two defects in this unit's own shipped code, fixed in the follow-up commit:**
      `mapPage` read `body.items` with no object check. `performRequest` substitutes `{}` only
      when `res.json()` **throws**; a body of literal `null` parses fine and arrives as `null`,
      so that read raised `TypeError: Cannot read properties of null` — an untyped English
      escape past this module's own stated invariant that every refusal is one plain
      `Error(FALLBACK)`, and past the `Error` scenario 1.3 is being told to treat as its signal.
      `mapMessage` already had the row-level check; the page had none. And `ROLES` inferred as
      `string[]` with a cast at the return, so a union that later gained `'system'` would
      compile while the client refused every such row at runtime — and a value added to `ROLES`
      but not the union made the cast an outright lie. Now `readonly ChatMessage['role'][]`
      narrowed by an `isRole` predicate, so either drift is a compile error and the cast is gone.
      **Review-pass follow-ups:**
      (ca) **`typeof === 'string'` admits `''`, which is the exact degenerate value two guards
      exist to stop.** `message_id: ''` passes, and it is the React key — two such rows collide,
      which is the failure the interface comment names, arriving *through* the guard.
      `next_cursor: ''` passes and returns `''`, not `null`: it is falsy, so 1.2's
      `if (page.nextCursor)` reads "last page" while the server said there is more, silently
      truncating a restored conversation. The declared type is kept; the invariant it protects is
      not. `send.ts`'s own `describeFailure` already uses `detail.trim()`, so blank-vs-present is
      a distinction this codebase draws elsewhere. Left for a red step — tightening it is a
      behavior change and needs a failing case first.
      (cb) **Nothing programmatic ties the client's wire keys to
      `api-specs/documents_messages_list.yaml`, and the backend does not exist yet.** Every key
      here was transcribed by hand from a spec no running system has satisfied. Combined with the
      all-or-nothing refusal, one renamed field is not a degraded page — it is a permanent hard
      failure for every user, with 200s in the access log and zero server-side signal. Compounding
      it: all five refusal sites throw an **identical** `Error(FALLBACK)` — no `cause`, no field
      name — and it is the same sentence `send` produces for a transport failure or a 500, so at
      triage the malformed-payload, network and server-error cases are indistinguishable strings.
      Owe a contract test reading the schema, and a distinguishing `cause`.
      (cc) **`loadChatMessages` returns no echo of which document it was for**, and takes no
      `AbortSignal` — the only `AbortController` is `httpClient.ts:90`, created internally for the
      timeout and unreachable from a caller. This is the class the story already paid a full
      red/green pair for in `useEditorDocument` (A→B→A installing a stale `version`), and that fix
      lived entirely in the hook. Scenario 1.2 gets no help: it cannot ask the resolved page "are
      you mine", it must re-derive the whole guard. Either thread a `signal` or return the
      `documentId` on the page.
      (cd) **`documentId` is interpolated unescaped** (no `encodeURIComponent` anywhere under
      `frontend/src`, so this matches `documentApi.ts:75,132` — house style, not a regression).
      Worth naming because the 404 case pins the interpolation as a feature: an empty id yields
      `/api/v1/documents//messages`, whose routed 404 carries no `error_code` and so lands as the
      generic fallback — telling a user the history is broken when the *id* was. Follow-up (ab)
      already has a live stale-stored-id path.
      (ce) Cosmetic, in this file: the comment explaining the absent `refusals` argument sits on
      `const FALLBACK`, 58 lines from the call it justifies, and would be carried off by a rename.
- [x] align-design — aligned the chat panel's history region to `mockups/desktop/01-editor-chat.html`
      + `editor.css`: `.ac-chat-history` took the mockup's flat `20px` padding, and
      `.ac-chat-message` took the `.bubble` geometry (`border-radius: 12px`, `padding: 12px 14px`)
      plus `align-self: flex-start` and `max-width: 88%`. Those last two are not in the mockup's
      rule — its bubble shrink-wraps because it sits in a flex *row*, while ours are block `<p>`s
      in a flex *column*, so without them a row would span the full 380px and have to be undone
      to make either side.
      **Geometry copied, colour not** — same rule as 0.2, and `/design-review` verified no mockup
      literal leaked (`#1e293b`, `#e8effe`, `#f7f8fa` all stayed out).
      **`/design-review`: PASS on the placeholder gate.** It grepped the whole `features/aiChat`
      tree for every value the mockup carries — `версий`, `версия`, `14:0`, `17 из 20`, `415`,
      `Осталось` — and the only hits are inside the CSS header documenting what was *not* ported.
      All six not-ported claims verified against the diff rather than taken on trust: the
      `.history` strip (revisions entry point, 7.x), the three-turn sample conversation, `.time`,
      `.quote`, `.typing`/`.dots`, and the `.msg .mark` avatar tile.
      **Its finding 1 is the one that matters, and it invalidates a design decision 1.2 was about
      to inherit: this app CANNOT express the mockup's per-side fill split.** `--bg-page` and
      `--accent-soft` **both** resolve to `--blue-50` (`index.css:19,47`) — already recorded in
      this same feature at `DocumentEditorPage.css:44-47` — so painting the user's bubble
      `--bg-page` and the assistant's `--accent-soft` paints them identically. There is no sunken
      neutral token: `--bg-page` is the page ground and this panel is `--bg-surface` (white), so
      the fill reads as an *accent* tile, the same blue as `.ac-chat-mark`, not the mockup's
      near-white neutral. The comment claiming a neutral-now/accent-later split was rewritten to
      state the collision instead. **1.2 needs a real second surface before it can split the sides
      at all** — a new token is the honest fix; `--bg-card-muted` is not, that is the
      disabled-control fill and (aw) already measures it at 1.16:1 against its neighbour.
      **Finding 2 fixed rather than recorded:** the bubble shipped `--border-subtle` on
      `--bg-page`, which is the exact pair (ax) measures at **1.11:1** against WCAG 1.4.11's 3:1 —
      a second instance of a failure measured one align-design entry above, on an element (ax)
      does not name. The border was dead weight anyway: the fill already separates the bubble from
      the white panel, and the border is indistinguishable from the fill. Dropped.
      **(bu) closed.** `.ac-chat-history` went from `min-height: 0` to `min-height: 120px`.
      `/design-review` verified the floor does not break the composer's pinning, and corrected the
      mechanism: above the floor `margin-top: auto` is a no-op anyway, because `flex: 1` consumes
      all free space and leaves the auto margin nothing to absorb — the composer is pinned by the
      history's *growth*. Below the floor free space goes negative and auto margins resolve to
      zero rather than misbehaving. It also caught the comment selling one side of the trade: below
      the floor there are **two nested scrollbars** and the head and composer scroll out of view,
      so the input is unreachable until the user scrolls back — worse than a collapsed history for
      someone trying to type. Kept anyway, because the collapsed case is *silent* (no scrollbar, no
      messages, nothing to discover); both sides are now in the comment.
      **(bt) closed.** The region is `role="log" aria-live="polite" aria-label="История переписки с
      ИИ"` (label a module-local const; nothing asserts it). `/design-review` was right that the
      `AuthLoadingIndicator` convention claim was half-accurate: that file argues for `<output>`
      *over* `role="status"` on a div, on the grounds that an implicit role states semantics rather
      than annotating them — and no element carries `role="log"` implicitly, so annotating is
      forced here. The comment now names the departure instead of claiming the convention whole.
      `.ac-chat-empty` deliberately stays **outside** the bubble treatment, and `/design-review`
      judged it correct: in the mockup that sentence is the assistant's first bubble; here it is
      what the panel says when there are no turns. A bubble would render a message with no
      `messageId`, and 1.2 would then have the same sentence appearing as both an empty state and
      never as a real message.
      `/test-coverage frontend --focus` with the filenames passed **explicitly** (the standing
      `carryover.md` quirk — the default `git diff HEAD --name-only` filter has produced four false
      all-clears on this story). `AiChatPanel.tsx` is 8/8 statements, 4/4 branches and
      `AiChatPanel.css` reports `{"total":0}`, confirming stylesheets are not instrumented.
      **That clean report is not evidence and is recorded as such:** this unit added attributes,
      comments and a constant to an already-rendered element, none of which v8 can turn into a
      statement or a branch. Neither test layer asserts `role="log"` or the label, and coverage
      cannot tell you that. Pre-existing gaps it did surface, none newly reachable: the `'failed'`
      arm at `useEditorDocument.ts:50` and the screen it drives at `DocumentEditorPage.tsx:32` (75%
      branch, the feature's weakest file) — that is (h)/(p)/8.8 again, located; `chatMessagesApi.ts`
      lines 63 and 98, the non-object-row and literal-`null`-body refusals, the second of which
      this session just added; and `editQuotaApi.ts:58`, the `resets_at` garbage-value refusal.
      **Review-pass follow-ups for scenario 1.2:**
      (cf) **`role="log"` announces on insert, which is right for one arriving reply and wrong for
      the restore path 1.2 owns** — a whole transcript injected after mount is read out in full.
      1.2 must suppress announcement during initial hydration. Recorded in the component too.
      (cg) **`align-self`/`max-width` are planted where 1.2 will have to move them off.** The
      mockup gets alignment from `.msg` being a flex *row* wrapper with `justify-content`, the
      bubble inside it. Here `.ac-chat-message` is a direct child of the column and carries the
      alignment itself, so the assistant avatar tile has no wrapper to live in — 1.2 introduces the
      row element and both properties migrate up to it.
- [ ] green-selenium
- [ ] demo
- [ ] green-selenium
- [ ] demo

### 1.2 An existing conversation is restored when the document is reopened
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.3 The chat history and the revisions panel each show their own load failure
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.1 Selecting text attaches the excerpt to the next instruction
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.1 Sending an instruction freezes the editor and offers cancellation
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.2 One gesture produces at most one instruction
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.3 A dirty buffer is not silently discarded when an instruction is sent
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.4 Leaving with unsaved content is guarded
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

## Frontend Scenarios (02_UI_Tests_Streaming.md)

### 4.1 Streamed text appears progressively as plain text
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.2 A dropped stream shows a reconnecting state distinct from a stalled one
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.1 A completed edit unfreezes the editor and shows the applied result
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.2 A failed edit reverts the buffer and offers a retry
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.3 Cancelling reverts without presenting a failure
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.4 The client timeout releases the editor rather than freezing it forever
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.5 An unrecognised terminal outcome is treated as a failure, not a success
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.1 Revisions are listed with their number, time and source
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.2 Restoring asks for confirmation and explains that nothing is destroyed
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.3 A superseded response never overwrites the current view
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 7.1 The revisions panel can be opened and closed from the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 7.2 The not-found blocker's link returns to the documents list
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

## Frontend Scenarios (02_UI_Tests_Guards.md)

### 8.1 Selection offsets are sent as code points, not as editor indices
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.2 A retry after a lost response does not create a second edit
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.3 An edited retry carries a new key and is actually executed
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.4 The client timeout releases the server edit, not only the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.5 A stale or post-terminal event is ignored
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.6 An unrecognised non-terminal event does not break the stream
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.7 A failed re-fetch after completion never leaves unsanitised text on screen
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.8 The document load has a loading state and a distinct failure state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.9 A failed restore leaves the pre-restore content in place
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.10 Restoring cannot be double-submitted
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.11 A session expiring with unsaved content does not discard it
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.12 Revision times are shown in the intended day
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.13 Stream reconnection backs off rather than retrying in a tight loop
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
