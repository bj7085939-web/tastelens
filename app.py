#!/usr/bin/env python3
"""
TasteLens — recommendations with receipts.

Pipeline:
  1. Resolve   : the user's taste seeds (a film, a book, an artist…)
                 are resolved to Qloo entity IDs via GET /search.
  2. Recommend : GET /v2/insights is called in parallel domains
                 (movie / book / artist / podcast / place / destination)
                 with the seed IDs as `signal.interests.entities` and
                 `feature.explainability=true`, so every recommendation
                 carries an affinity score AND a per-seed contribution
                 breakdown.
  3. Brief     : a deterministic composer turns the merged, ranked
                 results into a weekend culture briefing where every
                 factual sentence cites its evidence entry [n].
  4. Audit     : the CiteLens citation checker (ported from the
                 nebius-citelens project) walks every sentence of the
                 briefing and flags any sentence without a valid
                 citation — unsupported claims stay visible.

Modes:
  * LIVE — QLOO_API_KEY is set; the real Qloo Taste AI API is called
    against https://hackathon.api.qloo.com.
  * DEMO — no key; a clearly-labelled mock client (mock_data.py)
    serves hand-authored stand-in data so the full pipeline, UI and
    audit run end to end. The UI shows a MOCK DATA banner. Mock data
    is never presented as real Qloo output.

Zero third-party dependencies: Python 3.10+ standard library only.
Run:  python3 app.py            (http://127.0.0.1:8000)
Env:  QLOO_API_KEY, QLOO_BASE_URL, PORT
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from qloo_client import QlooClient, QlooError, DEFAULT_BASE_URL  # noqa: E402
from mock_data import MockQloo  # noqa: E402

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

class Config:
    def __init__(self, env: dict | None = None):
        env = os.environ if env is None else env
        self.qloo_api_key = env.get("QLOO_API_KEY", "").strip()
        self.qloo_base_url = env.get("QLOO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.port = int(env.get("PORT", "8000"))

    @property
    def live(self) -> bool:
        return bool(self.qloo_api_key)


def make_client(cfg: Config, transport=None):
    """Real QlooClient in live mode, MockQloo otherwise."""
    if cfg.live:
        kwargs = {"transport": transport} if transport else {}
        return QlooClient(cfg.qloo_api_key, cfg.qloo_base_url, **kwargs)
    return MockQloo()


# --------------------------------------------------------------------------
# Citation audit (ported from CiteLens, nebius-citelens/app.py)
# --------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\x22])")
_REF_RE = re.compile(r"\[(\d+)\]")


def split_sentences(text: str) -> list[str]:
    parts = _SENT_SPLIT.split(text.strip())
    return [p.strip() for p in parts if p and p.strip()]


def verify_citations(answer: str, n_sources: int) -> dict:
    """Split the briefing into sentences and check each for citations."""
    segments = []
    for sent in split_sentences(answer):
        refs = sorted({int(m) for m in _REF_RE.findall(sent)
                       if 1 <= int(m) <= n_sources})
        segments.append({"text": sent, "refs": refs, "cited": bool(refs)})
    cited = sum(1 for s in segments if s["cited"])
    return {
        "segments": segments,
        "sentences": len(segments),
        "cited": cited,
        "coverage": (cited / len(segments)) if segments else 0.0,
    }


# --------------------------------------------------------------------------
# Recommendation pipeline
# --------------------------------------------------------------------------

TARGET_TYPES = ["movie", "book", "artist", "podcast", "place", "destination"]
TYPE_LABELS = {
    "movie": "Watch", "book": "Read", "artist": "Listen",
    "podcast": "Listen (podcast)", "place": "Go", "destination": "Travel",
}
PER_TYPE = 3       # recommendations kept per domain
FETCH_TAKE = 6     # candidates fetched per domain before dedupe/trim


def resolve_seeds(seed_inputs: list[dict], client) -> tuple[list[dict], list[str]]:
    """Resolve user-typed seed names to entities. Returns (seeds, misses)."""
    seeds, misses = [], []
    for item in seed_inputs:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        types = [item["type"]] if item.get("type") else None
        hits = client.search_entities(name, types=types, take=3)
        if hits:
            seeds.append(hits[0])
        else:
            misses.append(name)
    return seeds, misses


def gather_recommendations(seeds: list[dict], client,
                           target_types: list[str],
                           location: str | None = None) -> tuple[dict, list[str]]:
    """One insights call per target domain; merge, dedupe, rank."""
    seed_ids = [s["entity_id"] for s in seeds]
    seed_names = {s["name"].lower() for s in seeds}
    domains: dict[str, list[dict]] = {}
    errors: list[str] = []
    for ttype in target_types:
        try:
            recs = client.get_insights(
                ttype, seed_ids, take=FETCH_TAKE,
                location_query=location if ttype == "place" else None)
        except QlooError as exc:
            errors.append(f"{ttype}: {exc}")
            continue
        kept = []
        seen = set()
        for r in recs:
            key = r["entity_id"] or r["name"].lower()
            if r["entity_id"] in seed_ids or r["name"].lower() in seed_names:
                continue  # never recommend the seeds back to the user
            if key in seen:
                continue
            seen.add(key)
            kept.append(r)
        kept.sort(key=lambda r: -(r["affinity"] or 0))
        domains[ttype] = kept[:PER_TYPE]
    return domains, errors


def _aff(rec: dict) -> float:
    return rec["affinity"] if rec.get("affinity") is not None else 0.0


def build_evidence(domains: dict, seeds: list[dict], mode: str) -> tuple[list[dict], dict]:
    """Number every recommendation as an evidence entry [n].

    Returns (evidence_list, ref_of) where ref_of maps id(rec) -> n.
    The evidence for a recommendation is its Qloo taste-graph record:
    the affinity score plus the explainability breakdown of which of
    the user's seeds drove it. In DEMO mode the entry is labelled MOCK.
    """
    seed_name_by_id = {s["entity_id"]: s["name"] for s in seeds}
    evidence, ref_of = [], {}
    for ttype, recs in domains.items():
        for r in recs:
            n = len(evidence) + 1
            drivers = sorted(
                ((seed_name_by_id.get(sid, sid), score)
                 for sid, score in (r.get("explainability") or {}).items()),
                key=lambda t: -t[1])
            driver_text = ", ".join(f"{name} {score:.2f}" for name, score in drivers[:3])
            origin = ("MOCK Qloo response (demo data)" if mode == "demo"
                      else "Qloo Insights API response")
            detail = (f"Affinity {_aff(r):.2f} for {r['name']} "
                      f"({ttype}) — {origin}.")
            if driver_text:
                detail += f" Seed contributions: {driver_text}."
            evidence.append({"id": n, "kind": "qloo-insights",
                             "title": f"{r['name']} — taste-graph record",
                             "detail": detail})
            ref_of[id(r)] = n
    return evidence, ref_of


def _driver_phrase(rec: dict, seeds: list[dict]) -> str:
    name_by_id = {s["entity_id"]: s["name"] for s in seeds}
    drivers = sorted((rec.get("explainability") or {}).items(), key=lambda t: -t[1])
    if not drivers:
        return "surfaced by the taste graph from your combined seeds"
    top_name = name_by_id.get(drivers[0][0], "your seeds")
    return f"driven mostly by your seed {top_name}"


SENT_LABELS = {
    "movie": "your next movie night", "book": "your reading list",
    "artist": "your playlist", "podcast": "your podcast queue",
    "place": "a place to go", "destination": "a trip worth taking",
}


def compose_briefing(seeds: list[dict], domains: dict, evidence: list[dict],
                     ref_of: dict) -> str:
    """Deterministic briefing composer — every factual sentence cited."""
    flat = [r for recs in domains.values() for r in recs]
    if not flat:
        return "No recommendations came back for those seeds."
    seed_list = ", ".join(s["name"] for s in seeds)
    top = max(flat, key=_aff)
    sentences = [
        f"Built from your seeds — {seed_list} — the single strongest match is "
        f"{top['name']}, at a taste-graph affinity of {_aff(top):.2f} "
        f"[{ref_of[id(top)]}]."
    ]
    for ttype, recs in domains.items():
        for r in recs:
            sentences.append(
                f"For {SENT_LABELS.get(ttype, ttype)}, {r['name']} "
                f"scores {_aff(r):.2f}, {_driver_phrase(r, seeds)} "
                f"[{ref_of[id(r)]}].")
    return " ".join(sentences)


def build_briefing(seed_inputs: list[dict], cfg: Config, client,
                    target_types: list[str] | None = None,
                    location: str | None = None) -> dict:
    mode = "live" if cfg.live else "demo"
    target_types = target_types or TARGET_TYPES
    seeds, misses = resolve_seeds(seed_inputs, client)
    if not seeds:
        return {"mode": mode, "error": "none of the seeds could be resolved",
                "unresolved": misses}
    domains, errors = gather_recommendations(seeds, client, target_types, location)
    evidence, ref_of = build_evidence(domains, seeds, mode)
    text = compose_briefing(seeds, domains, evidence, ref_of)
    check = verify_citations(text, len(evidence))
    out_domains = []
    for ttype, recs in domains.items():
        out_domains.append({
            "type": ttype,
            "label": TYPE_LABELS.get(ttype, ttype),
            "recommendations": [{
                "name": r["name"],
                "entity_id": r["entity_id"],
                "affinity": r["affinity"],
                "popularity": r["popularity"],
                "description": r["description"],
                "explainability": r.get("explainability") or {},
                "evidence_ref": ref_of[id(r)],
            } for r in recs],
        })
    return {
        "mode": mode,
        "mock": mode == "demo",
        "seeds": [{"name": s["name"], "type": s["type"],
                   "entity_id": s["entity_id"]} for s in seeds],
        "unresolved": misses,
        "domains": out_domains,
        "briefing": text,
        "segments": check["segments"],
        "stats": {k: check[k] for k in ("sentences", "cited", "coverage")},
        "evidence": evidence,
        "errors": errors,
    }


# --------------------------------------------------------------------------
# HTTP server
# --------------------------------------------------------------------------

def load_presets() -> list[dict]:
    p = ROOT / "data" / "presets.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def make_handler(cfg: Config, client):
    presets = load_presets()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep stdout clean
            pass

        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: dict):
            self._send(code, json.dumps(obj).encode("utf-8"),
                       "application/json; charset=utf-8")

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/health":
                return self._json(200, {"ok": True, "live": cfg.live,
                                        "mode": "live" if cfg.live else "demo",
                                        "mock": not cfg.live})
            if path == "/api/presets":
                return self._json(200, {"presets": presets})
            rel = "static/index.html" if path == "/" else path.lstrip("/")
            target = (ROOT / rel).resolve()
            if target.is_file() and str(target).startswith(str(ROOT)):
                ctype = {".html": "text/html; charset=utf-8",
                         ".css": "text/css", ".js": "text/javascript",
                         ".json": "application/json"}.get(
                             target.suffix, "application/octet-stream")
                return self._send(200, target.read_bytes(), ctype)
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path.split("?")[0] != "/api/briefing":
                return self._json(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                seeds = body.get("seeds") or []
                if not isinstance(seeds, list) or not seeds:
                    return self._json(400, {"error": "seeds list is required"})
                types = body.get("types") or None
                location = (body.get("location") or "").strip() or None
                result = build_briefing(seeds, cfg, client,
                                        target_types=types, location=location)
                if "error" in result:
                    return self._json(422, result)
                return self._json(200, result)
            except Exception as exc:  # surface, never crash the server
                return self._json(502, {"error": f"{type(exc).__name__}: {exc}"})

    return Handler


def main():
    cfg = Config()
    client = make_client(cfg)
    mode = "LIVE (Qloo API)" if cfg.live else "DEMO (mock data — no QLOO_API_KEY)"
    print(f"TasteLens on http://127.0.0.1:{cfg.port}  mode={mode}", file=sys.stderr)
    ThreadingHTTPServer(("127.0.0.1", cfg.port),
                        make_handler(cfg, client)).serve_forever()


if __name__ == "__main__":
    main()
