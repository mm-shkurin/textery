"""Expected values and page instrumentation for story 18, scenario 2.1.

Constants only, no behaviour: the assertions that consume these live in
`auto_editor_transition_statements.py`, which was split at the 200-line cap. Same split the
generating-state DSL took for the same reason (`generating_state_locators.py`).
"""

# The editor reached by auto-transition names the type the user picked — and nothing else.
#
# Deliberately NOT `manual_editor_statements.EXPECTED_DOKLAD_BREADCRUMB` ("Доклад · Ручной
# режим"), even though the same locator carries both. That constant belongs to the path where
# the user chose the manual mode. This scenario's user chose `doklad` and then typed a topic;
# a "Ручной режим" chip here would state, on screen, a choice they never made.
#
# The mode chip is currently hardcoded in `ManualEditorBreadcrumb.tsx`, so this value is a
# decision this test makes rather than one it reads off the build — which is the point:
# `GenerationHeading.tsx` already reached the same conclusion for the composer breadcrumb
# ("Story 18 removed the mode modal ... there is no mode to name and the chip would be a
# constant label decorating a choice the user never makes") and dropped its chip. The editor
# arrived at by the same modeless flow owes the user the same honesty. Green makes the mode
# chip conditional; the manual path keeps its own constant and its own assertion.
#
# CONCRETELY OWED BY GREEN, and it is two deletions in `ManualEditorBreadcrumb.tsx`, not one:
# the hardcoded mode chip AND the `me-breadcrumb-sep` separator beside it. Today that component
# renders "Доклад · Ручной режим"; drop only the chip and this equality fails on "Доклад ·".
EXPECTED_AUTO_EDITOR_BREADCRUMB = "Доклад"

# Deliberately NOT the shared WAIT_TIMEOUT_SECONDS (5s, tuned for a DOM change that is already
# decided). This wait spans a whole server round trip chain that must all complete before the
# editor can exist: the create POST, the first status poll (the poll interval is 5s on its own),
# the conversion POST, and then the ManualEditor lazy chunk — Tiptap + ProseMirror, the largest
# bundle in the app, fetched at this exact moment. Five seconds would fail on a healthy build.
AUTO_TRANSITION_TIMEOUT_SECONDS = 30

# The acceptance stack runs GENERATION_PROVIDER=fake, whose `generate` returns one canned string
# (backend/adapters/generation_provider/src/provider/fake_provider.py, FAKE_DOKLAD_TEXT). This is
# that string verbatim, INCLUDING its blank-line block separation — the transcription is exact,
# not normalized.
#
# The blank lines are pinned deliberately, and this is the scenario's decision to make rather
# than one deferred to the layers below it. The editor's document is `inline*`
# (`Document.extend({ content: 'inline*' })` in useManualEditorInstance.ts), so it has no
# paragraph node: `HardBreakNode` is, by its own comment, "the ONLY node that can represent a
# break". A `\n\n` in the generated text therefore has exactly one faithful representation in
# this editor — two consecutive hard breaks — which Selenium's rendered `.text` reports back as
# the blank line below. The green phase's conversion must produce that; anything that collapses
# the breaks turns a structured doklad into one run-on paragraph, and this test is what says so.
#
# UNOBSERVED PREDICTION — green-selenium must CHARACTERIZE this, not assume it. The blank lines
# above were derived ANALYTICALLY from the `inline*` schema and `HardBreakNode`; they have never
# been read off a running browser. The assertion compares them against Selenium's
# browser-normalised innerText over rendered `<br>`s, and Tiptap appends its own
# `ProseMirror-trailingBreak` nodes — neither of which the derivation accounts for. So a
# CORRECT conversion may still produce a whitespace-mismatched `.text`, and the failure message
# would name the conversion, making "change the product until it matches" the cheapest path to
# green. It is the wrong path. Rule for green-selenium: OBSERVE the actual `.text` first; if the
# only difference is whitespace/blank-line count, that is a TEST-SIDE correction to this
# constant, not product feedback. A difference in the WORDS is product feedback.
#
# DRIFT RISK — this is a hand transcription of `FAKE_DOKLAD_TEXT` in
# `backend/adapters/generation_provider/src/provider/fake_provider.py`. Byte-identical today,
# tied by nothing, and it crosses a lane boundary: whoever edits that constant works in the
# backend worktree and will never see this file. Scenario 1.2 solved the analogous problem by
# naming the tying test in its locators file; the equivalent tie here is owed and does not exist
# yet, so until it does, a change to the fake provider surfaces here as an unrecognisable
# "the editor opened with the wrong text".
#
# And the constant is only correct if the fake provider is the one answering: `runtime.py`
# defaults `GENERATION_PROVIDER` to `"gigachat"` when the variable is UNSET, so a stack started
# without `backend/.env` runs the real provider and fails this equality with a message naming
# the conversion — a misattributed failure whose real cause is a missing env file.
EXPECTED_GENERATED_TEXT = (
    "Введение\n\n"
    "Данный доклад посвящён теме, указанной пользователем. В работе рассматриваются "
    "ключевые аспекты предмета исследования, приводится анализ существующих подходов "
    "и формулируются основные выводы.\n\n"
    "Основная часть\n\n"
    "Тема раскрывается последовательно: сначала даётся общая характеристика вопроса, "
    "затем разбираются частные случаи и практические примеры, подтверждающие "
    "теоретические положения.\n\n"
    "Заключение\n\n"
    "В результате проведённого анализа можно сделать вывод о значимости рассмотренной "
    "темы и наметить направления для дальнейшего изучения."
)

# Records every OS-originated event on the page, capture-phase so nothing can stop it before it
# is counted, and `isTrusted` so the script's own bookkeeping cannot pad the list.
ARM_INTERACTION_WATCH_SCRIPT = """
window.__acceptanceUserEvents = [];
['click', 'pointerdown', 'keydown'].forEach(function (name) {
  document.addEventListener(name, function (event) {
    if (event.isTrusted) { window.__acceptanceUserEvents.push(name); }
  }, true);
});
return true;
"""

READ_INTERACTION_WATCH_SCRIPT = "return window.__acceptanceUserEvents;"
