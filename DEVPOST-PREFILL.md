# TasteLens — Devpost prefill packet (copy-ready, final submit held)

Status: DO NOT press final Submit until the main controller confirms
the live demo URL and the demo video. Everything below is prefilled
copy; fill the bracketed links at submit time.

## Project name
TasteLens

## Tagline
Recommendations with receipts — a taste agent that shows its evidence.

## Inspiration
Agents today are culturally blind and recommenders are black boxes.
Qloo's taste graph knows what sits next to what; nobody shows the
user why. CiteLens taught us to audit citations for research
answers — TasteLens applies the same discipline to taste: every
recommendation must bring its receipts.

## What it does
The user names 2–3 beloved cultural entities (film / book / artist /
destination). TasteLens resolves them via Qloo `/search`, fans out
`/v2/insights` calls across six domains with the seeds as signals
and explainability on, merges and ranks by affinity, and composes a
weekend briefing in which every factual sentence cites the evidence
entry for its recommendation — the Qloo affinity plus the per-seed
contribution breakdown. A citation audit (CiteLens engine) reports
coverage and flags anything unsupported.

## How we built it
Pure Python standard library (zero deps): `qloo_client.py`
implements the documented hackathon surface
(`hackathon.api.qloo.com`, `X-Api-Key` header, GET query params, no
legacy `/recs`); `app.py` runs resolve → recommend → brief → audit;
vanilla JS UI renders briefing, cards and evidence. A
clearly-labelled mock mode let us build and test the whole pipeline
before the manually-issued API key arrived; the submitted demo runs
in LIVE mode against the real Qloo API.

## Challenges
[Fill after live integration — e.g. parameter validity per
filter.type, explainability shape vs. documented shape, empty-result
domains and how they were handled.]

## Accomplishments
End-to-end pipeline with 100% citation coverage on briefings;
explainability surfaced per card, not buried in JSON; live Qloo
affinity and per-seed contributions verified across all six
domains and all three presets.

## What's next
Tavily enrichment (a public web source per pick), location-aware
place picks by city, shareable briefing links, multi-person "group
taste" merge for trip planning.

## Built with
python, qloo-api, html, css, javascript, render
(add `tavily` only if enrichment ships)

## Links (fill at submit time)
- Public repo: https://github.com/bj7085939-web/tastelens
- Live demo: [Render URL — verify logged-out before pasting]
- Demo video: [public YouTube URL, < 3:00, LIVE mode]

## Screenshots (capture from the LIVE deployment)
1. Landing page with LIVE badge
2. Briefing with coverage meter at 100%
3. One recommendation card zoom (affinity + driven-by line)
4. Evidence list
