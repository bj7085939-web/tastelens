#!/usr/bin/env python3
"""
TasteLens DEMO-mode data — clearly-labelled stand-ins for Qloo API
responses, used only until a real QLOO_API_KEY is configured.

HONESTY RULES (do not relax these):
  * Everything in this module is hand-authored illustrative data.
    It is NOT real Qloo output and must never be presented as such.
  * The app labels every response built from this data with
    mode="demo" and a visible "MOCK DATA" notice in the UI.
  * Entity IDs carry a `mock-` prefix so they can never be confused
    with real Qloo entity IDs.
  * Affinity scores below are invented for demonstration of the
    ranking/evidence pipeline only.

The shapes mirror what qloo_client.normalise_entity() produces from a
real API payload, so the pipeline code is identical in both modes.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Seed catalogue: names a user might type, resolvable by mock /search.
# ---------------------------------------------------------------------------

def _ent(slug, name, etype, popularity, description, aliases=()):
    return {
        "entity_id": f"mock-entity-{slug}",
        "name": name,
        "type": etype,
        "subtype": "",
        "popularity": popularity,
        "description": description,
        "image": "",
        "affinity": None,
        "explainability": {},
        "aliases": list(aliases),
    }


SEED_CATALOG = [
    _ent("amelie", "Amélie", "movie", 0.93,
         "Jean-Pierre Jeunet's whimsical 2001 Paris romance.",
         aliases=("le fabuleux destin d'amélie poulain", "amelie")),
    _ent("spirited-away", "Spirited Away", "movie", 0.97,
         "Hayao Miyazaki's 2001 animated fantasy about a bathhouse for spirits.",
         aliases=("sen to chihiro no kamikakushi",)),
    _ent("lost-in-translation", "Lost in Translation", "movie", 0.9,
         "Sofia Coppola's 2003 Tokyo-set story of two strangers adrift.",
         aliases=()),
    _ent("in-the-mood-for-love", "In the Mood for Love", "movie", 0.91,
         "Wong Kar-wai's 2000 Hong Kong romance of restraint and longing.",
         aliases=("fa yeung nin wa",)),
    _ent("norwegian-wood", "Norwegian Wood", "book", 0.88,
         "Haruki Murakami's 1987 novel of love and loss in 1960s Tokyo.",
         aliases=("noruwei no mori",)),
    _ent("kafka-on-the-shore", "Kafka on the Shore", "book", 0.86,
         "Haruki Murakami's 2002 metaphysical novel of a runaway teenager.",
         aliases=()),
    _ent("radiohead", "Radiohead", "artist", 0.95,
         "English rock band known for restless, atmospheric reinvention.",
         aliases=()),
    _ent("nujabes", "Nujabes", "artist", 0.84,
         "Japanese producer who fused jazz samples with hip-hop beats.",
         aliases=("seba jun",)),
    _ent("portishead", "Portishead", "artist", 0.87,
         "Bristol trip-hop pioneers behind the album Dummy.",
         aliases=()),
    _ent("kyoto", "Kyoto", "destination", 0.92,
         "Japan's former imperial capital of temples, gardens and tea houses.",
         aliases=()),
    _ent("tokyo", "Tokyo", "destination", 0.96,
         "Japan's capital: neon wards, quiet shrines and endless side streets.",
         aliases=()),
    _ent("paris", "Paris", "destination", 0.95,
         "France's capital of boulevards, museums and café culture.",
         aliases=()),
]

_CATALOG_BY_ID = {e["entity_id"]: e for e in SEED_CATALOG}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def mock_search(query: str, types: list[str] | None = None, take: int = 5) -> list[dict]:
    """Resolve a name against the mock catalogue (token overlap).

    Unknown names synthesise a clearly-marked placeholder entity so the
    demo pipeline never dead-ends; the placeholder is still mock data.
    """
    q = _tokens(query)
    scored = []
    for ent in SEED_CATALOG:
        hay = _tokens(ent["name"] + " " + " ".join(ent["aliases"]))
        overlap = len(q & hay)
        if overlap:
            scored.append((overlap, ent))
    scored.sort(key=lambda t: -t[0])
    hits = [dict(e) for _, e in scored]
    for h in hits:
        h.pop("aliases", None)
    if types:
        typed = [h for h in hits if h["type"] in types]
        hits = typed or hits
    if not hits:
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") or "unknown"
        hits = [{
            "entity_id": f"mock-entity-{slug}",
            "name": query.strip().title(),
            "type": (types[0] if types else "movie"),
            "subtype": "",
            "popularity": None,
            "description": "",
            "image": "",
            "affinity": None,
            "explainability": {},
            "synthesised": True,
        }]
    return hits[:take]


# ---------------------------------------------------------------------------
# Recommendation pools per target type (mock /v2/insights).
# `drivers` maps seed names -> contribution weight (explainability demo).
# Weights need not sum to 1; MockQloo redistributes unmatched weight.
# ---------------------------------------------------------------------------

def _rec(slug, name, etype, affinity, popularity, description, drivers):
    return {
        "entity_id": f"mock-rec-{slug}",
        "name": name,
        "type": etype,
        "subtype": "",
        "popularity": popularity,
        "description": description,
        "image": "",
        "affinity": affinity,
        "explainability": {},
        "drivers": drivers,
    }


INSIGHT_POOLS: dict[str, list[dict]] = {
    "movie": [
        _rec("chungking-express", "Chungking Express", "movie", 0.92, 0.85,
             "Wong Kar-wai's 1994 diptych of lovelorn Hong Kong policemen.",
             {"In the Mood for Love": 0.62, "Amélie": 0.24, "Lost in Translation": 0.31}),
        _rec("midnight-in-paris", "Midnight in Paris", "movie", 0.84, 0.83,
             "Woody Allen's 2011 time-slip romance through literary Paris.",
             {"Amélie": 0.66, "Norwegian Wood": 0.18}),
        _rec("your-name", "Your Name", "movie", 0.81, 0.9,
             "Makoto Shinkai's 2016 body-swap romance across Tokyo and Itomori.",
             {"Spirited Away": 0.58, "Norwegian Wood": 0.22}),
        _rec("before-sunrise", "Before Sunrise", "movie", 0.79, 0.82,
             "Richard Linklater's 1995 walk-and-talk romance in Vienna.",
             {"Lost in Translation": 0.44, "Amélie": 0.3}),
    ],
    "book": [
        _rec("wind-up-bird", "The Wind-Up Bird Chronicle", "book", 0.9, 0.84,
             "Murakami's 1994 surreal search for a missing cat — and a missing wife.",
             {"Norwegian Wood": 0.61, "Kafka on the Shore": 0.4}),
        _rec("colorless-tsukuru", "Colorless Tsukuru Tazaki and His Years of Pilgrimage",
             "book", 0.85, 0.8,
             "Murakami's 2013 novel of friendship, exile and return.",
             {"Norwegian Wood": 0.55, "Kafka on the Shore": 0.33}),
        _rec("kitchen", "Kitchen", "book", 0.78, 0.72,
             "Banana Yoshimoto's 1988 novella of grief, food and found family.",
             {"Norwegian Wood": 0.38, "Amélie": 0.27}),
        _rec("convenience-store-woman", "Convenience Store Woman", "book", 0.74, 0.78,
             "Sayaka Murata's 2016 deadpan novel about a life arranged around a konbini.",
             {"Kafka on the Shore": 0.3, "Lost in Translation": 0.29}),
    ],
    "artist": [
        _rec("massive-attack", "Massive Attack", "artist", 0.88, 0.86,
             "Bristol trip-hop originators; Blue Lines and Mezzanine defined a sound.",
             {"Portishead": 0.64, "Radiohead": 0.3}),
        _rec("boards-of-canada", "Boards of Canada", "artist", 0.83, 0.78,
             "Scottish duo making nostalgic, tape-warped electronic music.",
             {"Radiohead": 0.47, "Nujabes": 0.26}),
        _rec("joe-hisaishi", "Joe Hisaishi", "artist", 0.82, 0.85,
             "Composer of the Ghibli scores — piano-led, quietly ecstatic.",
             {"Spirited Away": 0.68, "Kyoto": 0.2}),
        _rec("dj-krush", "DJ Krush", "artist", 0.76, 0.7,
             "Japanese turntablist whose moody instrumentals bridge jazz and hip-hop.",
             {"Nujabes": 0.59, "Tokyo": 0.24}),
    ],
    "podcast": [
        _rec("99pi", "99% Invisible", "podcast", 0.8, 0.85,
             "Roman Mars' design-and-architecture storytelling show.",
             {"Kyoto": 0.3, "Amélie": 0.28, "Tokyo": 0.3}),
        _rec("song-exploder", "Song Exploder", "podcast", 0.79, 0.82,
             "Artists take their own songs apart, track by track.",
             {"Radiohead": 0.5, "Portishead": 0.3, "Nujabes": 0.34}),
        _rec("the-memory-palace", "The Memory Palace", "podcast", 0.72, 0.68,
             "Nate DiMeo's short, lyrical vignettes from history's margins.",
             {"Norwegian Wood": 0.35, "In the Mood for Love": 0.3}),
    ],
    "place": [
        _rec("cafe-de-flore", "Café de Flore, Paris", "place", 0.86, 0.88,
             "Saint-Germain institution — coffee, croissants and people-watching.",
             {"Amélie": 0.57, "Paris": 0.4}),
        _rec("shimokitazawa-vinyl", "Shimokitazawa record shops, Tokyo", "place", 0.84, 0.76,
             "A maze of vintage vinyl stores in Tokyo's bohemian quarter.",
             {"Nujabes": 0.52, "Tokyo": 0.42, "Radiohead": 0.3}),
        _rec("fushimi-inari", "Fushimi Inari Taisha, Kyoto", "place", 0.83, 0.9,
             "10,000 vermilion torii gates climbing Mount Inari — go at dawn.",
             {"Kyoto": 0.6, "Spirited Away": 0.35}),
        _rec("yanaka-ginza", "Yanaka Ginza, Tokyo", "place", 0.77, 0.7,
             "Old-town shopping street of snack stalls and temple lanes.",
             {"Tokyo": 0.48, "Lost in Translation": 0.25}),
    ],
    "destination": [
        _rec("lisbon", "Lisbon", "destination", 0.85, 0.89,
             "Trams, miradouros and faded grandeur on the Tagus.",
             {"Amélie": 0.4, "In the Mood for Love": 0.3}),
        _rec("taipei", "Taipei", "destination", 0.8, 0.84,
             "Night markets, tea mountains and a gentler big-city hum.",
             {"Lost in Translation": 0.38, "Norwegian Wood": 0.3}),
        _rec("naoshima", "Naoshima", "destination", 0.79, 0.66,
             "Japan's art island: museums buried in hillsides, a giant pumpkin pier.",
             {"Spirited Away": 0.42, "Kyoto": 0.36}),
        _rec("vienna", "Vienna", "destination", 0.75, 0.87,
             "Coffee-house culture and waltz-era architecture, unhurried.",
             {"Amélie": 0.33, "Kafka on the Shore": 0.2}),
    ],
}


class MockQloo:
    """Drop-in stand-in for qloo_client.QlooClient in DEMO mode.

    Implements the same three methods with the same normalised output
    shapes, backed entirely by the mock data above.
    """

    is_mock = True

    def search_entities(self, query: str, types: list[str] | None = None,
                        take: int = 5) -> list[dict]:
        return mock_search(query, types=types, take=take)

    def search_tags(self, query: str, take: int = 5) -> list[dict]:
        return [{"tag_id": f"mock-tag-{re.sub(r'[^a-z0-9]+', '-', query.lower())}",
                 "name": query}][:take]

    def get_insights(self, entity_type: str, signal_entity_ids: list[str],
                     take: int = 10, signal_tags: list[str] | None = None,
                     location_query: str | None = None,
                     explainability: bool = True) -> list[dict]:
        pool = INSIGHT_POOLS.get(entity_type, [])
        seed_names = {}
        for sid in signal_entity_ids:
            ent = _CATALOG_BY_ID.get(sid)
            seed_names[sid] = ent["name"] if ent else None
        out = []
        for item in pool:
            rec = {k: v for k, v in item.items() if k != "drivers"}
            rec["explainability"] = _explain(item.get("drivers", {}),
                                             signal_entity_ids, seed_names)
            out.append(rec)
        out.sort(key=lambda r: -(r["affinity"] or 0))
        return out[:take]


def _explain(drivers: dict, seed_ids: list[str], seed_names: dict) -> dict:
    """Turn a pool item's name-keyed driver weights into ID-keyed scores.

    Weight attached to seeds that are not in the current signal set is
    redistributed evenly across the actual seeds, so the demo's
    explainability always refers to the user's real inputs.
    """
    if not seed_ids:
        return {}
    matched, leftover = {}, 0.0
    name_to_id = {v: k for k, v in seed_names.items() if v}
    for name, w in drivers.items():
        sid = name_to_id.get(name)
        if sid:
            matched[sid] = matched.get(sid, 0.0) + w
        else:
            leftover += w
    share = leftover / len(seed_ids)
    scores = {sid: round(matched.get(sid, 0.0) + share, 3) for sid in seed_ids}
    return {sid: s for sid, s in scores.items() if s > 0}
