# TasteLens — local self-check log

Date: 2026-10-23 (CST). Environment: this VM, Python 3.12, no
QLOO_API_KEY configured → DEMO mode (as designed; key request is a
separate parallel task).

## Unit tests

```
$ python3 -m unittest discover -s tests
Ran 20 tests in 0.010s — OK
```

Suites: client request construction (base URL locked to
hackathon.api.qloo.com, `X-Api-Key` header only, insights/search
query params, location passthrough), response normalisation
(incl. nested explainability shapes, empty payloads), mock pipeline
(mode labelling, seed resolution, per-domain cap of 3, affinity
ordering, seeds never recommended back, evidence completeness +
MOCK labelling, explainability ⊆ user seed IDs, briefing citation
coverage = 1.0), all 3 presets end to end, config/client selection,
verifier uncited-flag behaviour.

One failure was found and fixed during this check: explainability
scores nested under a signal-name group were not extracted;
`qloo_client._extract_scores` now recurses (flat / {"score": …} /
grouped shapes all covered by tests).

## Live server smoke test (local instance, port 8931, DEMO mode)

- `GET /api/health` → `{"ok": true, "live": false, "mode": "demo", "mock": true}`
- `GET /` → serves the UI (title "TasteLens — recommendations with receipts")
- `GET /api/presets` → 3 presets (paris-reverie, tokyo-softly, rainy-day)
- `POST /api/briefing` preset 1 (Amélie / Radiohead / Norwegian Wood):
  6 domains × 3 recommendations = 18 picks, 18 evidence entries,
  briefing 19 sentences, citation coverage **1.0**, no errors.
  Top pick: Chungking Express, affinity 0.92, evidence [1] marked
  "MOCK Qloo response (demo data)".
- Preset 2 (Lost in Translation / Nujabes / Kyoto): coverage 1.0,
  18 recommendations, no errors.
- Preset 3 (In the Mood for Love / Portishead / Kafka on the Shore,
  location "Tokyo"): coverage 1.0, 18 recommendations, no errors.
- Unknown seed ("Some Obscure Zine"): resolves via the mock
  synthesis path, coverage 1.0 — the demo never dead-ends.

Local check instance was shut down after verification; nothing is
deployed yet (deployment is a submit-time step, see
SUBMISSION-PLAN.md).

## Honesty notes

- No real Qloo API call has been made from this codebase yet — the
  key had not arrived. All demo output above is mock data and is
  labelled as such in API responses, evidence entries and the UI.
- Client behaviour follows the official developer guide + Insights
  deep-dive + Search reference as read on 2026-10-23; payload
  normalisation is defensive and must be re-verified against real
  responses when the key lands (SUBMISSION-PLAN checklist item 3).
