# TasteLens — Devpost submission plan (Qloo Agentic Hackathon)

Event facts (from round4 scan, verified against the official rules page
2026-10-23): prize pool **$25,000** (1st $15,000 / 2nd $6,000 / 3rd
$4,000), submission window closes **2026-10-30 23:45 ET =
2026-10-31 11:45 CST**. Judging: technical implementation (depth of
Qloo use), design, potential impact, creativity — equal weight.
Submission itself needs no identity/phone verification; winner payout
paperwork (affidavit + W-8BEN for non-US residents) is post-win only.

**Do not submit from this document alone — submission is executed by
the main controller once the API key is in hand and the LIVE demo is
verified end to end.**

## Materials checklist

- [x] Working codebase (this repo): pipeline + UI + tests, demo mode
      verified locally (see SELF-CHECK.md)
- [ ] Public GitHub repository — push this directory to
      `github.com/bj7085939-web/tastelens` (create at submit time;
      **never commit Qloo response data or the API key** — key lives
      only in the host's env config; per the developer guide, Qloo
      response data must not be stored in a public repository, so any
      judging-period cache stays server-side/private)
- [ ] Live demo URL — Render free tier via `render.yaml`, env var
      `QLOO_API_KEY` set in the dashboard; verify the public URL in a
      logged-out/incognito fetch before claiming it (backend "live"
      ≠ public page works)
- [ ] Demo video — per DEMO.md shot list, < 3:00, public YouTube
      (record in LIVE mode; if the key is too late, keep the MOCK
      banner visible and say so in narration)
- [ ] Devpost project page copy — draft below (problem → solution →
      Qloo usage → stack)
- [ ] Built-with tags: python, qloo-api, tavily (only if enrichment
      ships), html, css, javascript, render
- [ ] Screenshots: landing, briefing with coverage meter, one
      recommendation card zoom (affinity + driven-by), evidence list

## Devpost copy draft

**Tagline**: Recommendations with receipts — a taste agent that shows
its evidence.

**Inspiration**: Agents today are culturally blind and recommenders
are black boxes. Qloo's taste graph knows *what* sits next to what;
nobody shows the user *why*. CiteLens taught us to audit citations
for research answers — TasteLens applies the same discipline to
taste: every recommendation must bring its receipts.

**What it does**: The user names 2–3 beloved cultural entities
(film / book / artist / destination). TasteLens resolves them via
Qloo `/search`, fans out `/v2/insights` calls across six domains
with the seeds as signals and explainability on, merges and ranks
by affinity, and composes a weekend briefing in which every factual
sentence cites the evidence entry for its recommendation — the Qloo
affinity plus the per-seed contribution breakdown. A citation audit
(CiteLens engine) reports coverage and flags anything unsupported.

**How we built it**: Pure Python standard library (zero deps):
`qloo_client.py` implements the documented hackathon surface
(`hackathon.api.qloo.com`, `X-Api-Key` header, GET query params,
no legacy `/recs`); `app.py` runs resolve → recommend → brief →
audit; vanilla JS UI renders briefing, cards and evidence. A
clearly-labelled mock mode let us build and test the whole pipeline
before the manually-issued API key arrived.

**Challenges**: (fill after live integration — e.g. parameter
validity per filter.type, explainability shape, empty-result
domains.)

**Accomplishments**: End-to-end pipeline with 100% citation coverage
on briefings; explainability surfaced per card, not buried in JSON.

**What's next**: Tavily enrichment (a public web source per pick),
location-aware place picks by city, shareable briefing links,
multi-person "group taste" merge for trip planning.

## Submit-day checklist (target: submit 2026-10-29 CST, ~27h buffer)

1. [ ] `QLOO_API_KEY` received (check spam folder of the operator
       mailbox; guide says keys are manually issued within a few
       business days)
2. [ ] Kill rule check: **if no key by 2026-10-28 24:00 CST and
       Discord #api-help has not resolved it — stop this project**
       (per plan; sunk cost stays ≤ ~6h, mock work remains reusable)
3. [ ] Live smoke test: all 3 presets against the real API; save
       private (non-repo) response samples; fix normaliser gaps
       against real payloads (esp. affinity + explainability paths)
4. [ ] Re-run `python3 -m unittest discover -s tests` — all green
5. [ ] Deploy to Render; set `QLOO_API_KEY` in dashboard; open the
       public URL logged-out and run one preset end to end
6. [ ] Record + upload the demo video (DEMO.md); captions on
7. [ ] Push the public repo (no keys, no Qloo response data)
8. [ ] Fill the Devpost form: copy above, repo URL, demo URL, video
       URL, built-with tags, screenshots
9. [ ] Submit, then re-open the project page and confirm the status
       reads **Submitted**; keep the demo alive through the judging
       window (2026-11-02 – 11-05) — daily-ops keep-alive applies
10. [ ] Log the submission (IDs, URLs) into the money-project tracker

## Still missing before this plan can execute

- The Qloo hackathon API key (requested via the official Google form;
  issuance is manual — the one uncontrolled lead time in this plan).
- Live-payload verification of `qloo_client.normalise_entity`
  (affinity / explainability locations are coded defensively against
  the documented shapes but unproven against the real API).
- GitHub repo creation + Render deploy (both are submit-time steps,
  deliberately not done in demo mode).

## Live integration status — 2026-10-24 (key email arrived, retrieval pending)

- Key email (hackathon@qloo.com, "Your Qloo API Access") arrived in
  the operator mailbox 2026-10-24 09:43 CST per the main controller;
  the 2026-10-28 kill rule is lifted.
- BLOCKER: the key itself has NOT been retrieved yet. This
  environment has no live browser and the Gmail connector is not
  connected (status: not_connected, zero accounts), so the mailbox
  cannot be read from here. Retrieval must be delegated as a browser
  task (log into the operator Gmail, open the Qloo mail). The key
  must go straight into the local `.env` (already excluded by
  `.gitignore`) and/or the Render dashboard secret — never into
  chat, reports, memory or git history.
- Verified without the key: hackathon base URL is reachable from
  this VM — a no-key GET to `/search` returns HTTP 401
  "No API key found in request", so live testing should work once
  the key lands. Unit tests re-run 2026-10-24: 20/20 green.
- Ready and waiting for the key: `live_smoke.py` (endpoint probes
  for /search, /v2/tags, /v2/insights + all 3 presets end to end;
  prints non-secret summaries only; raw samples go to the private
  dir `qloo-tastelens-private/` outside the repo, never committed).
  No code change is needed for the mock→live switch: `app.py`
  already selects the real client when QLOO_API_KEY is set, and the
  MOCK banner / MOCK evidence labels disappear automatically in
  live mode (verify on the deployed page, don't assume).
- Also ready: `VIDEO-SCRIPT-LIVE.md` (verbatim LIVE narration,
  < 3:00) and `DEVPOST-PREFILL.md` (copy-ready fields; final Submit
  held for the main controller).
- Still needs browser delegation after the key: GitHub repo
  creation (`gh` is not logged in here), Render deploy + dashboard
  `QLOO_API_KEY` + logged-out public-URL verification, demo video
  recording, Devpost form prefill + final submit.
