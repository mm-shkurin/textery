# Brief Product Description

1. It's **Textery** — a web SaaS platform for generating educational and business texts
   (рефераты, эссе, доклады, сочинения and other formats) by subscription.
2. User describes what they need (topic, requirements, volume, extra wishes), triggers a
   generation, gets an editable document back, and refines it in a built-in rich-text
   editor.
3. Main goal: maximize conversion into a paid subscription and retention through repeated
   use of the generator — the demo also needs to showcase a modern SaaS architecture
   (subscriptions, product analytics, funnels) end to end, not just generation quality.
4. The underlying logic is:
   - Landing → registration (email+password, with the email verification code mocked —
     no real mail integration — plus Yandex ID and VK ID OAuth) → subscription (3 tariffs,
     differing by AI model tier and monthly generation quota; billing fully mocked, no
     real payment provider) → pick one of 4 document types (реферат/эссе/доклад/сочинение)
     → generate via an external LLM API (GigaChat, Sber — superseded the originally planned Anthropic Claude/OpenRouter 2026-07-09, known-debt #11) → edit in the built-in editor
     → save → export to Word/PDF (nice-to-have, not first priority) → browse history →
     come back and repeat.
   - Every step along the way emits a product-analytics event, stored and rolled up into
     funnels (registration funnel, subscription funnel) with CSV export.
   - Built for hundreds of concurrent users, not just a small demo — generation requests
     need to be queued/async rather than handled inline. See `ProductSpecification/ExpectedLoad.md`.

Source material: `.memory-bank/tz.md` (ТЗ) and
`.memory-bank/комплект продуктовой архитектуры.txt` (product/solution architecture draft).
Note: that architecture draft recommends NestJS for backend and Google OAuth — overridden
per this project's actual choices: **Python + FastAPI, Hexagonal Architecture** (see
`.memory-bank/tech-details/backend.md`) and **Yandex ID + VK ID** instead of Google.
