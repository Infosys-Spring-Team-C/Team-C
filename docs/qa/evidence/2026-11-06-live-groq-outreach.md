# Live Groq outreach check — 6 November 2026

Command: `POST /api/v1/outreach/generate` against the Compose stack
(`db`, `api`, `frontend` healthy).

Request: lead `6` (Vanguard Fintech), `tone=consultative`, `length=short`,
`outreach_type=cold_email`, goal "book a discovery call", product
"SalesGenie AI", pain point "manual reporting", `variant=4`.

Response summary:

```json
{
  "id": 34,
  "status": "draft",
  "channel": "Email",
  "subject_line": "Consistent Partner Lead Visibility for Vanguard Fintech",
  "execution": {
    "engine": "external",
    "provider": "groq",
    "model": "openai/gpt-oss-120b",
    "duration_ms": 3200,
    "used_mock": false,
    "fallback_reason": null
  }
}
```

Body (read back from the stored `Outreach_Campaigns` row, not from the console):

```
Hi Noah,

I’m thrilled our pilot delivered results. To support Vanguard’s expansion,
SalesGenie AI can give your partner managers a single, real-time view of lead
quality and next-best actions, turning partner-sourced opportunities into
measurable pipeline.

Would a 15-minute call next week work?
```

Health at the time of the check:

```json
{"ai_backend":"external","ai_provider":"groq","ai_model":"openai/gpt-oss-120b","ai_used_mock":false,"ai_mode":"live-model","ai_status":"ok"}
```

The live model supplied the subject line itself. The adapter also has a tested
fallback that fills a neutral subject from the supplied company name if a model
omits it; the fallback is recorded in `assumptions` so it is never hidden.
