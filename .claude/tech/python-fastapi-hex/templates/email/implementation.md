# Email Adapter Implementation Template

## Product Note

Textery's email+password auth (story 7) uses a **mocked** verification code -- no real
mail integration is required for that story (see `.memory-bank/tech-details/backend.md`
and `BriefProductDescription.md`). This template exists for when a real sender is
actually wired (post-MVP); until then the mocked verification adapter just returns/logs
the code instead of sending anything.

## Rules

- Extend `AbstractMailSender` for shared template loading and sending logic
- Implement the port interface defined in usecase (e.g., `VerificationCodeSender`)
- HTML templates live in `src/templates/`
- Use `aiosmtplib` (async SMTP client) for actual sending, once a real sender is needed

## Reference (read before generating)

- Abstract base: `backend/adapters/email/src/service/abstract_mail_sender.py`
- Existing sender: `backend/adapters/email/src/service/verification_code_sender.py`
- Port interfaces: `backend/usecase/src/adapters/`

## Pattern

1. Extend `AbstractMailSender`
2. Implement port interface method (`async def send(...)`)
3. Load HTML template via `self.load_template("template_name.html")`
4. Replace placeholders in template (e.g., `template.replace("{code}", code)`)
5. Call `await self.send_html_email(to, subject, body)` from base class

## HTML Template

- Create in `backend/adapters/email/src/templates/`
- Use `{placeholder}` syntax for dynamic values
- Must be valid HTML with proper encoding

## Key Paths

- Senders: `backend/adapters/email/src/service/`
- Templates: `backend/adapters/email/src/templates/`
- Port interfaces: `backend/usecase/src/adapters/`
