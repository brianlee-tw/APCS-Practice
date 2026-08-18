# Anonymous Analytics Endpoint Contract

Status: **ADAPTER READY / PROVIDER DISABLED**

The static site keeps full diagnostic events locally for debugging, but remote analytics is deliberately narrower. A provider is enabled only by setting the HTTPS URL in the `apcs-analytics-endpoint` meta tag.

## Remote transport

- Method: `POST`
- Content-Type: `text/plain;charset=UTF-8`
- Credentials: omitted
- Referrer: omitted
- Body: JSON text
- Failure mode: fail-open for the learning experience; analytics errors must never block the quiz

## Allowed remote events

- `landing_view`
- `quiz_start`
- `quiz_complete`
- `result_view`
- `product_interest`
- `share_click`
- `quiz_restart`

`quiz_answer` is intentionally **local only**. Individual answers must not be uploaded by the v1 adapter.

## Allowed payload

Base fields:

- `schemaVersion`
- `sessionId` — random, sessionStorage-scoped; not a permanent user identifier
- `name`
- `at`
- `page`
- `source`
- `medium`
- `campaign`
- `content`

Optional funnel fields:

- `quizVersion`
- `totalQuestions`
- `elapsedSec`
- `weakest`
- `productId`

The adapter intentionally excludes exact overall score, individual answers, name, school, email, phone, account identifiers, user-agent, and client IP from its application payload.

## Provider acceptance gate

Before setting a real endpoint:

1. Use a separate APCS project/data boundary; do not write into Health Companion databases.
2. Validate event names and field allowlists server-side; never trust the browser payload.
3. Add rate limiting / abuse controls.
4. Do not expose service-role or secret credentials in the static site.
5. Define retention (initial recommendation: 30 days for raw launch events, then aggregate/delete).
6. Review provider-level logging, especially IP and request-log retention.
7. Update `privacy.html` with the actual provider, fields, purpose, and retention before enabling it.
8. Verify with synthetic events before directing real traffic.

## Why no persistent visitor ID

The first 100-user experiment needs aggregate conversion rates, not cross-site identity or long-term behavioral profiles. A session-scoped random ID is sufficient to detect basic funnel sequences while reducing privacy surface.
