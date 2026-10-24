#!/usr/bin/env python3
"""
Qloo Taste AI API client — written against the public Qloo documentation
(Qloo Agentic Hackathon Developer Guide + Insights API Deep Dive +
Search Entities reference, docs.qloo.com, read 2026-10-23).

Facts this client relies on (all from the docs above):
  * Hackathon keys work ONLY against https://hackathon.api.qloo.com
    (staging / production return 401 with a hackathon key).
  * Auth is the `X-Api-Key` request header — never a query param, never
    a Bearer token.
  * Insights is a GET request: parameters go in the query string.
      GET /v2/insights?filter.type=urn:entity:movie
                       &signal.interests.entities=<entity_id>,<entity_id>
                       &take=10
  * `filter.type` is required; supported values include
    urn:entity:artist / book / brand / destination / movie / person /
    place / podcast / tv_show / video_game.
  * `feature.explainability=true` adds a per-result
    `query.explainability` section: which input entities contributed to
    the recommendation, with normalised scores between 0 and 1.
  * Entity lookup by name is GET /search?query=<text>&types=<urn,...>
    (the /search `types` list differs from insights `filter.type`).
  * Tag lookup is GET /v2/tags?query=<text>.
  * Do NOT use /recommendations or /recs (legacy, unsupported).

Responses are normalised defensively: the normalisers read the
documented field names (`results.entities[]` with `entity_id`, `name`,
`type`, `properties`, and a per-entity `query` object carrying
`affinity` / `explainability`) and tolerate the documented alternates,
because the hackathon key was not yet available when this was written.
Nothing here fabricates API data — normalising an empty or unexpected
payload yields empty lists, never invented entities.

Zero third-party dependencies: Python 3.10+ standard library only.
The HTTP transport is injectable so unit tests run fully offline.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error

DEFAULT_BASE_URL = "https://hackathon.api.qloo.com"

# filter.type values documented for /v2/insights.
ENTITY_TYPES = (
    "artist", "book", "brand", "destination", "movie",
    "person", "place", "podcast", "tv_show", "video_game",
)


def urn(entity_type: str) -> str:
    """'movie' -> 'urn:entity:movie' (passes full URNs through)."""
    entity_type = entity_type.strip()
    return entity_type if entity_type.startswith("urn:") else f"urn:entity:{entity_type}"


def short_type(entity_urn: str) -> str:
    """'urn:entity:movie' -> 'movie'."""
    return entity_urn.rsplit(":", 1)[-1] if entity_urn else ""


class QlooError(RuntimeError):
    """Raised for transport/HTTP/parse failures from the Qloo API."""


def http_get_json(url: str, headers: dict, timeout: int = 60) -> dict:
    """GET and parse a JSON body. Raises QlooError on HTTP errors."""
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise QlooError(f"Qloo API HTTP {exc.code} for {url.split('?')[0]}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise QlooError(f"Qloo API unreachable: {exc.reason}") from exc


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_scores(node) -> dict:
    """Recursively pull {entity_id: score} pairs out of an explainability
    object. Tolerates the documented groupings: flat {id: score},
    {id: {"score": s}}, and groups nested under a signal name such as
    "signal.interests.entities" or "entities"."""
    out: dict = {}
    if not isinstance(node, dict):
        return out
    for k, v in node.items():
        if isinstance(v, dict) and "score" in v:
            score = _as_float(v.get("score"))
            if score is not None:
                out[str(k)] = score
        elif isinstance(v, dict):
            out.update(_extract_scores(v))
        else:
            score = _as_float(v)
            if score is not None:
                out[str(k)] = score
    return out


def normalise_entity(raw: dict) -> dict | None:
    """Normalise one Qloo entity object (search or insights flavour)."""
    if not isinstance(raw, dict):
        return None
    entity_id = raw.get("entity_id") or raw.get("id") or ""
    name = raw.get("name") or ""
    if not name and not entity_id:
        return None
    props = raw.get("properties") or {}
    query = raw.get("query") or {}
    affinity = _as_float(query.get("affinity"))
    if affinity is None:
        affinity = _as_float(raw.get("affinity"))
    explain = {}
    expl = query.get("explainability") or raw.get("explainability") or {}
    if isinstance(expl, dict):
        # Documented: normalised 0..1 scores showing which input
        # entities contributed to this recommendation.
        explain = _extract_scores(expl)
    return {
        "entity_id": str(entity_id),
        "name": name,
        "type": short_type(raw.get("type", "")),
        "subtype": raw.get("subtype", ""),
        "popularity": _as_float(props.get("popularity")),
        "description": (props.get("description") or raw.get("description") or "").strip(),
        "image": props.get("image") or "",
        "affinity": affinity,
        "explainability": explain,
    }


def normalise_entities(payload: dict) -> list[dict]:
    """Pull the entity list out of a /search or /v2/insights payload."""
    if not isinstance(payload, dict):
        return []
    results = payload.get("results") if isinstance(payload.get("results"), dict) else payload
    items = results.get("entities") or results.get("results") or []
    out = []
    for raw in items:
        ent = normalise_entity(raw)
        if ent:
            out.append(ent)
    return out


class QlooClient:
    """Thin, testable wrapper over the Qloo Taste AI HTTP API."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL,
                 transport=http_get_json):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    # -- low level ------------------------------------------------------
    def _get(self, path: str, params: dict) -> dict:
        clean = {k: v for k, v in params.items() if v not in (None, "", [])}
        qs = urllib.parse.urlencode(clean, doseq=True)
        url = f"{self.base_url}{path}" + (f"?{qs}" if qs else "")
        return self.transport(url, {"X-Api-Key": self.api_key})

    # -- documented endpoints ------------------------------------------
    def search_entities(self, query: str, types: list[str] | None = None,
                        take: int = 5) -> list[dict]:
        """GET /search — resolve a human name to Qloo entity IDs."""
        params: dict = {"query": query, "take": take}
        if types:
            params["types"] = ",".join(urn(t) for t in types)
        return normalise_entities(self._get("/search", params))

    def search_tags(self, query: str, take: int = 5) -> list[dict]:
        """GET /v2/tags — find valid taste-tag IDs by keyword."""
        raw = self._get("/v2/tags", {"query": query, "take": take})
        results = raw.get("results") if isinstance(raw.get("results"), dict) else raw
        tags = results.get("tags") or results.get("entities") or []
        out = []
        for t in tags:
            if isinstance(t, dict):
                out.append({"tag_id": t.get("id") or t.get("tag_id") or "",
                            "name": t.get("name", "")})
        return out

    def get_insights(self, entity_type: str, signal_entity_ids: list[str],
                     take: int = 10, signal_tags: list[str] | None = None,
                     location_query: str | None = None,
                     explainability: bool = True) -> list[dict]:
        """GET /v2/insights — cross-domain affinity recommendations.

        Signals: the user's seed entity IDs (signal.interests.entities).
        Explainability is on by default so every recommendation can show
        which seed drove it — the core of TasteLens' "receipts".
        """
        params: dict = {
            "filter.type": urn(entity_type),
            "signal.interests.entities": ",".join(signal_entity_ids),
            "take": take,
        }
        if signal_tags:
            params["signal.interests.tags"] = ",".join(signal_tags)
        if location_query:
            params["filter.location.query"] = location_query
        if explainability:
            params["feature.explainability"] = "true"
        return normalise_entities(self._get("/v2/insights", params))
