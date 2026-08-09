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
      **Left open, recorded rather than fixed:** (ac) the screen has no topbar/breadcrumb/format
      bar/statusbar at all — a staged deferral to the scenarios that own them, but until then the
      shell reads unfinished; (ad) the app's `--bg-page` resolves to `--blue-50`, the same value as
      `--accent-soft`, so the white card, the chat and the accent tile all sit on tinted blue
      separated only by a 4%-alpha shadow — a dedicated sunken token would restore the mockup's
      card/ground contrast; (ae) `.ac-chat` has no `flex: 1` region, so the moment scenario 1.1 adds
      the composer it will float up under the header unless the notice is replaced by a `flex: 1`
      message list.
      **The step row was missing from this scenario's list** (every other scenario has one); added
      retroactively. `/test-coverage frontend --focus` over it found **no gap it
      created**: `AiChatPanel.tsx` and `EditorDocumentView.tsx` are 100%/100% with **zero
      branches** between them, and the two CSS files are not instrumented at all. A clean report
      here is not evidence — v8 counts executed statements, and unconditional JSX plus a
      stylesheet cannot produce a gap however wrong they look. The gaps below are the *green*
      units' and were invisible until the filenames were passed explicitly, exactly as
      `carryover.md` predicted of the `git diff HEAD --name-only` focus filter.
- [ ] red-frontend (coverage: repeat mount does not refetch)
- [ ] green-frontend (coverage: repeat mount does not refetch)
- [ ] red-frontend (coverage: stale response for old id ignored)
- [ ] green-frontend (coverage: stale response for old id ignored)
      Both pairs target `useEditorDocument.ts` (branches 4/8). The dedupe guard `L35` and the two
      stale-response guards `L41`/`L45` have their true arms taken by **no** test — all three
      `return`s are deletable with the suite green, which is follow-up (k) still open: the
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
      Also uncovered and deliberately left alone: `DocumentEditorPage.tsx:20` `documentId ?? ''`
      right arm — reachable only by mounting the page off its route, no user-visible behavior.
- [ ] green-selenium
- [ ] demo

### 0.2 An account over its daily quota cannot type an instruction
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.1 The editor and chat panel render side by side with an empty history
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
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
