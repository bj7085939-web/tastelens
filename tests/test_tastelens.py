"""Unit tests for TasteLens (no network; transports mocked, demo data local)."""
import json
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as tastelens  # noqa: E402
import qloo_client  # noqa: E402
from mock_data import MockQloo  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _capture_client(payload):
    """QlooClient whose transport records the request and returns payload."""
    seen = {}

    def fake_transport(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return payload

    return qloo_client.QlooClient("ql-test-key", transport=fake_transport), seen


INSIGHTS_PAYLOAD = {
    "results": {"entities": [
        {"entity_id": "e-100", "name": "Chungking Express",
         "type": "urn:entity:movie", "subtype": "urn:entity:movie",
         "properties": {"popularity": 0.85, "description": "Wong Kar-wai."},
         "query": {"affinity": 0.92,
                   "explainability": {"signal.interests.entities": {
                       "seed-1": {"score": 0.62}, "seed-2": 0.24}}}},
        {"entity_id": "e-101", "name": "Midnight in Paris",
         "type": "urn:entity:movie",
         "properties": {"popularity": 0.83},
         "query": {"affinity": 0.84, "explainability": {}}},
    ]},
}


class TestClientRequests(unittest.TestCase):
    def test_insights_request_shape(self):
        client, seen = _capture_client(INSIGHTS_PAYLOAD)
        client.get_insights("movie", ["seed-1", "seed-2"], take=7)
        url = urllib.parse.urlparse(seen["url"])
        self.assertEqual(url.scheme + "://" + url.netloc,
                         "https://hackathon.api.qloo.com")
        self.assertEqual(url.path, "/v2/insights")
        qs = urllib.parse.parse_qs(url.query)
        self.assertEqual(qs["filter.type"], ["urn:entity:movie"])
        self.assertEqual(qs["signal.interests.entities"], ["seed-1,seed-2"])
        self.assertEqual(qs["take"], ["7"])
        self.assertEqual(qs["feature.explainability"], ["true"])
        # Auth: X-Api-Key header only — never a query param, never Bearer.
        self.assertEqual(seen["headers"], {"X-Api-Key": "ql-test-key"})
        self.assertNotIn("api_key", url.query)

    def test_search_request_shape(self):
        client, seen = _capture_client({"results": {"entities": []}})
        client.search_entities("Amélie", types=["movie"], take=3)
        url = urllib.parse.urlparse(seen["url"])
        self.assertEqual(url.path, "/search")
        qs = urllib.parse.parse_qs(url.query)
        self.assertEqual(qs["query"], ["Amélie"])
        self.assertEqual(qs["types"], ["urn:entity:movie"])

    def test_location_only_when_given(self):
        client, seen = _capture_client(INSIGHTS_PAYLOAD)
        client.get_insights("place", ["s1"], location_query="Tokyo")
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(seen["url"]).query)
        self.assertEqual(qs["filter.location.query"], ["Tokyo"])


class TestNormalise(unittest.TestCase):
    def test_insights_payload_normalised(self):
        out = qloo_client.normalise_entities(INSIGHTS_PAYLOAD)
        self.assertEqual(len(out), 2)
        first = out[0]
        self.assertEqual(first["name"], "Chungking Express")
        self.assertEqual(first["type"], "movie")
        self.assertEqual(first["affinity"], 0.92)
        self.assertEqual(first["popularity"], 0.85)
        self.assertEqual(first["explainability"], {"seed-1": 0.62, "seed-2": 0.24})

    def test_empty_payload_yields_empty(self):
        self.assertEqual(qloo_client.normalise_entities({"results": {}}), [])
        self.assertEqual(qloo_client.normalise_entities({}), [])

    def test_urn_helpers(self):
        self.assertEqual(qloo_client.urn("movie"), "urn:entity:movie")
        self.assertEqual(qloo_client.urn("urn:entity:book"), "urn:entity:book")
        self.assertEqual(qloo_client.short_type("urn:entity:tv_show"), "tv_show")


class TestMockPipeline(unittest.TestCase):
    def setUp(self):
        self.cfg = tastelens.Config({})
        self.client = MockQloo()
        self.seeds = [{"name": "Amélie", "type": "movie"},
                      {"name": "Radiohead", "type": "artist"},
                      {"name": "Norwegian Wood", "type": "book"}]
        self.result = tastelens.build_briefing(self.seeds, self.cfg, self.client)

    def test_demo_mode_labelled(self):
        self.assertEqual(self.result["mode"], "demo")
        self.assertTrue(self.result["mock"])

    def test_seeds_resolved(self):
        names = [s["name"] for s in self.result["seeds"]]
        self.assertEqual(names, ["Amélie", "Radiohead", "Norwegian Wood"])
        self.assertEqual(self.result["unresolved"], [])

    def test_all_domains_present_and_capped(self):
        types = [d["type"] for d in self.result["domains"]]
        self.assertEqual(types, tastelens.TARGET_TYPES)
        for d in self.result["domains"]:
            self.assertLessEqual(len(d["recommendations"]), tastelens.PER_TYPE)
            self.assertGreaterEqual(len(d["recommendations"]), 1)

    def test_recommendations_sorted_by_affinity(self):
        for d in self.result["domains"]:
            affs = [r["affinity"] for r in d["recommendations"]]
            self.assertEqual(affs, sorted(affs, reverse=True))

    def test_seeds_never_recommended_back(self):
        seed_names = {"amélie", "radiohead", "norwegian wood"}
        for d in self.result["domains"]:
            for r in d["recommendations"]:
                self.assertNotIn(r["name"].lower(), seed_names)

    def test_every_recommendation_has_evidence(self):
        total = sum(len(d["recommendations"]) for d in self.result["domains"])
        self.assertEqual(len(self.result["evidence"]), total)
        refs = {ev["id"] for ev in self.result["evidence"]}
        for d in self.result["domains"]:
            for r in d["recommendations"]:
                self.assertIn(r["evidence_ref"], refs)

    def test_evidence_is_marked_mock(self):
        for ev in self.result["evidence"]:
            self.assertIn("MOCK", ev["detail"])

    def test_explainability_references_only_user_seeds(self):
        seed_ids = {s["entity_id"] for s in self.result["seeds"]}
        for d in self.result["domains"]:
            for r in d["recommendations"]:
                self.assertTrue(set(r["explainability"]) <= seed_ids,
                                r["name"])

    def test_briefing_fully_cited(self):
        self.assertEqual(self.result["stats"]["coverage"], 1.0,
                         self.result["briefing"])
        self.assertTrue(all(s["cited"] for s in self.result["segments"]))


class TestPresets(unittest.TestCase):
    def test_every_preset_resolves_and_cites(self):
        presets = json.loads((ROOT / "data" / "presets.json").read_text("utf-8"))
        self.assertGreaterEqual(len(presets), 3)
        cfg = tastelens.Config({})
        for p in presets:
            with self.subTest(preset=p["id"]):
                res = tastelens.build_briefing(p["seeds"], cfg, MockQloo())
                self.assertEqual(res["unresolved"], [])
                self.assertEqual(res["stats"]["coverage"], 1.0)


class TestConfigAndClientChoice(unittest.TestCase):
    def test_live_requires_key(self):
        self.assertFalse(tastelens.Config({}).live)
        self.assertTrue(tastelens.Config({"QLOO_API_KEY": "k"}).live)

    def test_client_choice(self):
        self.assertIsInstance(tastelens.make_client(tastelens.Config({})), MockQloo)
        live_client = tastelens.make_client(tastelens.Config({"QLOO_API_KEY": "k"}))
        self.assertIsInstance(live_client, qloo_client.QlooClient)

    def test_unknown_seed_still_resolves_in_demo(self):
        res = tastelens.build_briefing(
            [{"name": "Some Obscure Zine", "type": "book"}],
            tastelens.Config({}), MockQloo())
        self.assertEqual(len(res["seeds"]), 1)
        self.assertEqual(res["stats"]["coverage"], 1.0)


class TestVerifier(unittest.TestCase):
    def test_uncited_flagged(self):
        stats = tastelens.verify_citations("Cited claim [1]. Bare claim here.", 1)
        self.assertEqual(stats["coverage"], 0.5)
        self.assertFalse(stats["segments"][1]["cited"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
