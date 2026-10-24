#!/usr/bin/env python3
"""TasteLens LIVE smoke test — run AFTER the Qloo key lands in .env.

Reads QLOO_API_KEY from .env (same directory as app.py) or the
environment. NEVER prints the key. Prints only non-secret summaries:
HTTP status, result counts, whether affinity / explainability are
present, and the raw shape keys of the first entity (so normaliser
gaps can be spotted without dumping payloads).

Raw response samples are saved to a PRIVATE directory OUTSIDE the
repo (never commit it, never push it — per the plan, Qloo response
data must not be stored in a public repository):
    ~/workspace/money-project/fastlane/work/qloo-tastelens-private/

Usage:
    python3 live_smoke.py            # preset 1 end to end + endpoint probes
    python3 live_smoke.py --all      # all 3 presets end to end
    python3 live_smoke.py --no-save  # print summaries only, save nothing
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIVATE = Path.home() / "workspace" / "money-project" / "fastlane" / "work" / "qloo-tastelens-private"
sys.path.insert(0, str(ROOT))

from app import build_briefing, Config  # noqa: E402
from qloo_client import QlooClient, DEFAULT_BASE_URL  # noqa: E402


def load_env_file() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def raw_get(client: QlooClient, path: str, params: dict):
    """Raw GET returning (status, parsed_json_or_error_string)."""
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    url = f"{client.base_url}{path}" + (f"?{qs}" if qs else "")
    req = urllib.request.Request(url, method="GET")
    req.add_header("X-Api-Key", client.api_key)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            body = ""
        return exc.code, {"_http_error": body}
    except Exception as exc:  # noqa: BLE001 — summary only, no key
        return 0, {"_transport_error": type(exc).__name__}


def shape_of(payload) -> dict:
    """Non-secret shape summary of a Qloo payload."""
    if not isinstance(payload, dict):
        return {"top": type(payload).__name__}
    results = payload.get("results") if isinstance(payload.get("results"), dict) else payload
    items = results.get("entities") or results.get("results") or []
    first = items[0] if items else None
    info = {"top_keys": sorted(payload.keys())[:12],
            "results_keys": sorted(results.keys())[:12] if isinstance(results, dict) else [],
            "n_entities": len(items)}
    if isinstance(first, dict):
        info["first_entity_keys"] = sorted(first.keys())[:15]
        q = first.get("query") if isinstance(first.get("query"), dict) else {}
        info["first_query_keys"] = sorted(q.keys())[:15]
        expl = q.get("explainability")
        info["explainability_type"] = type(expl).__name__
        if isinstance(expl, dict):
            info["explainability_top_keys"] = sorted(expl.keys())[:8]
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    import os
    key = os.environ.get("QLOO_API_KEY", "").strip() or load_env_file().get("QLOO_API_KEY", "").strip()
    if not key:
        print("ABORT: no QLOO_API_KEY in environment or .env — refusing to run.")
        return 2
    print(f"key present: yes (length {len(key)} chars — value never printed)")
    client = QlooClient(key, DEFAULT_BASE_URL)
    if not args.no_save:
        PRIVATE.mkdir(parents=True, exist_ok=True)

    # --- Endpoint probes (one call each) -------------------------------
    probes = [
        ("search", "/search", {"query": "Inception", "take": 3}),
        ("tags", "/v2/tags", {"query": "jazz", "take": 3}),
    ]
    for name, path, params in probes:
        status, payload = raw_get(client, path, params)
        print(f"[probe:{name}] HTTP {status}  shape={json.dumps(shape_of(payload))}")
        if not args.no_save and status == 200:
            (PRIVATE / f"probe-{name}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Insights probe with a resolved seed ---------------------------
    seeds = client.search_entities("Inception", types=["movie"], take=3)
    print(f"[search:Inception] resolved {len(seeds)}: "
          f"{[(s['name'], s['type']) for s in seeds]}")
    if seeds:
        status, payload = raw_get(client, "/v2/insights", {
            "filter.type": "urn:entity:movie",
            "signal.interests.entities": seeds[0]["entity_id"],
            "feature.explainability": "true", "take": 5})
        print(f"[probe:insights] HTTP {status}  shape={json.dumps(shape_of(payload))}")
        if not args.no_save and status == 200:
            (PRIVATE / "probe-insights.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        recs = client.get_insights("movie", [seeds[0]["entity_id"]], take=5)
        n_aff = sum(1 for r in recs if r["affinity"] is not None)
        n_expl = sum(1 for r in recs if r["explainability"])
        print(f"[normalised:insights] {len(recs)} recs, affinity present {n_aff}, "
              f"explainability non-empty {n_expl}")
        for r in recs[:3]:
            print(f"    - {r['name']} affinity={r['affinity']} "
                  f"drivers={list(r['explainability'].items())[:3]}")

    # --- Full pipeline per preset --------------------------------------
    presets = json.loads((ROOT / "data" / "presets.json").read_text(encoding="utf-8"))
    if not args.all:
        presets = presets[:1]
    cfg = Config(env={"QLOO_API_KEY": key, "QLOO_BASE_URL": DEFAULT_BASE_URL})
    for preset in presets:
        out = build_briefing(preset["seeds"], cfg, client)
        stats = out.get("stats", {})
        n_recs = sum(len(d["recommendations"]) for d in out.get("domains", []))
        n_aff = sum(1 for d in out.get("domains", [])
                    for r in d["recommendations"] if r["affinity"] is not None)
        n_expl = sum(1 for d in out.get("domains", [])
                     for r in d["recommendations"] if r["explainability"])
        print(f"[preset:{preset['id']}] mode={out.get('mode')} "
              f"seeds={[s['name'] for s in out.get('seeds', [])]} "
              f"unresolved={out.get('unresolved')} recs={n_recs} "
              f"affinity={n_aff} explainability={n_expl} "
              f"coverage={stats.get('coverage')} errors={out.get('errors')}")
        if not args.no_save:
            safe = {k: v for k, v in out.items()}  # normalised output only
            (PRIVATE / f"briefing-{preset['id']}.json").write_text(
                json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"private samples dir: {PRIVATE} (NEVER commit or push this directory)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
