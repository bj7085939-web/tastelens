# TasteLens — recommendations with receipts

Give TasteLens 2–3 things you already love — a film, a book, an artist, a
place — and it asks the **Qloo taste graph** what sits next to them across
every cultural domain, then writes you a weekend briefing where **every
recommendation carries its affinity score and its evidence**. Recommendation
systems are usually a black box ("because you watched…"); TasteLens makes
the receipts the product: each pick shows its Qloo affinity and exactly
which of your seeds drove it, and a citation audit (ported from CiteLens)
verifies that every factual sentence in the briefing cites its evidence.

Built for the **Qloo Agentic Hackathon** (Devpost, $25,000 prize pool,
deadline 2026-10-30 23:45 ET).

## How Qloo is used

| Step | Qloo endpoint | Where |
|---|---|---|
| Resolve the user's seeds (typed names) to entity IDs | `GET /search?query=…&types=…` | `qloo_client.py → search_entities()` |
| Cross-domain recommendations per target type (movie / book / artist / podcast / place / destination) with the seed IDs as `signal.interests.entities` | `GET /v2/insights?filter.type=…` | `qloo_client.py → get_insights()` |
| Per-recommendation "why" — normalised contribution of each seed | `feature.explainability=true` on the same Insights call | parsed in `normalise_entity()` |
| Tag discovery (roadmap / fallback signal source) | `GET /v2/tags` | `qloo_client.py → search_tags()` |

Client facts follow the official Qloo hackathon developer guide:
hackathon keys work **only** against `https://hackathon.api.qloo.com`,
auth is the `X-Api-Key` header, Insights is a GET with query-string
parameters, and the legacy `/recs` / `/recommendations` endpoints are
never touched.

## Pipeline

1. **Resolve** — each seed name is looked up via `/search`.
2. **Recommend** — one `/v2/insights` call per target domain, all seeds
   as signals; results are merged, deduplicated, the seeds themselves
   filtered out, and ranked by affinity (top 3 per domain).
3. **Brief** — a deterministic composer writes the weekend briefing;
   every factual sentence ends with an evidence marker `[n]`.
4. **Audit** — the CiteLens citation checker segments the briefing and
   flags any sentence without a valid citation; the UI shows the
   coverage meter and red-flags gaps instead of hiding them.

## Quickstart

Zero third-party dependencies — Python 3.10+ standard library only.

```bash
# Demo mode (no key): labelled mock data, full pipeline + audit
python3 app.py
# open http://127.0.0.1:8000

# Live mode once the hackathon key arrives:
QLOO_API_KEY=... python3 app.py
```

Demo mode is honest by construction: responses built from
`mock_data.py` are labelled `mode: "demo"` in the API, carry a
**MOCK DATA** banner in the UI, and every evidence entry says
"MOCK Qloo response (demo data)". Mock entities/scores are
hand-authored stand-ins for pipeline development — never real
Qloo output. Server-side caching of real responses for the judging
period is planned per the developer guide (private cache only;
Qloo data is never committed to this repo).

## Tests

```bash
python3 -m unittest discover -s tests   # 20 tests, transports mocked, no network
```

Coverage: client request construction (URL, `X-Api-Key` header, query
params), response normalisation incl. explainability shapes, the full
demo pipeline (seed resolution, per-domain caps, affinity ordering,
no seed self-recommendations, evidence completeness), all presets,
and the citation verifier.

## Layout

```
app.py              server + resolve/recommend/brief/audit pipeline
qloo_client.py      Qloo Taste AI client (documented endpoints only)
mock_data.py        DEMO-mode stand-in data + MockQloo (labelled)
static/             single-page UI (vanilla HTML/CSS/JS)
data/presets.json   3 one-click demo scenarios
tests/              unit tests (mocked transports)
render.yaml         Render free-tier deploy config (key via dashboard)
DEMO.md             demo-video shot list (< 3 min)
SUBMISSION-PLAN.md  Devpost materials + submit checklist
SELF-CHECK.md       local verification log
```

## Provenance

Forked from **CiteLens** (Nebius × NVIDIA hackathon, submitted
2026-10-23): the citation-audit engine, server skeleton, UI shell,
test approach and Render deployment pattern are reused; the domain
layer (Qloo client, taste-graph reasoning, briefing composer) is new.

## License

MIT — see `LICENSE`.
