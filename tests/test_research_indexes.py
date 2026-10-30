import json
from datetime import datetime, timedelta
import tempfile
import unittest #enables run and check results of tests
from pathlib import Path 
from unittest.mock import AsyncMock, patch #enables exchange of web calls with controlled answers during the tests
from scraping.research import indexes

#first we group all tests in one class
class IndexTests(unittest.TestCase): #with this parameter we get methods for checks later
    def test_normalizes_urls_without_losing_query_parameters(self):
        #we epect them to return equal
        self.assertEqual( 
            indexes.canonical_url("HTTPS://Example.ORG:443/a?x=1#part"), 
            "https://example.org/a?x=1",
        )
        #we expect them to return not equal
        self.assertNotEqual(indexes.canonical_url("https://example.org/a?x=1"),
                            indexes.canonical_url("https://example.org/a?x=2"))

#test for make_index function, first we remove duplicates, and then we give IDs 
    def test_deduplicates_before_limiting_and_assigning_ids(self):
        results = [{"title": "First", "url": "https://EXAMPLE.org/a#one"},
                   {"title": "Duplicate", "url": "https://example.org/a#two"}] #first we give two same urls
        results += [{"title": str(i), "url": f"https://example.org/{i}"} #herere we give 25 different, random urls
                    for i in range(25)]
        index = indexes.make_index("test query", {"results": results,
            "receipt": {"status": "observed"}, "source": ["duckduckgo_html"]}, 20)
        self.assertEqual(len(index["results"]), 20)
        self.assertEqual([r["id"] for r in index["results"]], list(range(1, 21)))
        self.assertEqual(index["results"][0]["title"], "First")

#function for recognising what part didnt work when i get "no results" message
    def test_empty_failed_and_partial_are_distinct(self):
        #three types of case we get:empty, partial and failed
        cases = [({"status": "observed"}, [], None, "empty"),
                 ({"status": "failed", "failure": {"code": "RATE_LIMITED"}},
                  [], None, "failed"),
                 ({"status": "observed"}, [{"url": "https://example.org/a"}],
                  "partial", "partial")]
        for receipt, results, coverage, expected in cases:
            with self.subTest(expected=expected):
                index = indexes.make_index("query", {"results": results,
                    "receipt": receipt, "coverage": coverage}, 20)
                self.assertEqual(index["status"], expected)
        failed = indexes.make_index("q", {"receipt": {"status": "failed",
            "failure": {"code": "TIMEOUT", "message": "timed out"}}}, 20)
        self.assertIn("TIMEOUT", failed["error"])


    def test_index_preserves_metadata_and_original_results(self):
        response = {"results": [{"title": "Documentation reference",
            "url": "https://EXAMPLE.org/article#sources", "snippet": "Public overview"}],
            "source": "duckduckgo_html", "receipt": {"status": "observed"}}

        index = indexes.make_index("diabetes documentation", response, 20)

        # The index keeps enough information to review where each link came from.
        self.assertEqual(index["query"], "diabetes documentation")
        self.assertEqual(index["source"], "duckduckgo_html")
        self.assertEqual(index["status"], "success")
        self.assertIsNone(index["error"])
        self.assertEqual(index["results"], [{"id": 1,
            "title": "Documentation reference",
            "url": "https://EXAMPLE.org/article#sources", "snippet": "Public overview"}])
        self.assertEqual(datetime.fromisoformat(index["searched_at"]).utcoffset(), timedelta(0))

        # Preparing an index must not add IDs to the provider's original response.
        self.assertNotIn("id", response["results"][0])

    def test_invalid_urls_are_reported_without_losing_valid_results(self):
        response = {"receipt": {"status": "observed"}, "results": [
            {"url": "not a URL"}, {"url": "https://example.org:bad/article"},
            {"url": "https://example.org/article"}]}

        index = indexes.make_index("diabetes documentation", response, 20)

        self.assertEqual(index["status"], "partial")
        self.assertIn("Invalid result URL", index["error"])
        self.assertEqual(index["results"], [{"id": 1, "title": "https://example.org/article",
            "url": "https://example.org/article", "snippet": ""}])

        # A response containing only invalid links is a failure, not an empty search.
        response["results"] = [{"url": "not a URL"}]
        self.assertEqual(indexes.make_index("q", response, 20)["status"], "failed")

    def test_failed_response_with_results_is_partial(self):
        response = {"receipt": {"status": "failed", "failure": {
            "code": "TIMEOUT", "message": "One source timed out"}},
            "results": [{"url": "https://example.org/article"}]}

        index = indexes.make_index("diabetes documentation", response, 20)

        self.assertEqual(index["status"], "partial")
        self.assertEqual(len(index["results"]), 1)
        self.assertIn("TIMEOUT", index["error"])
        self.assertIn("One source timed out", index["error"])

    def test_result_limit_is_positive_and_never_exceeds_twenty(self):
        response = {"receipt": {"status": "observed"}, "results": [
            {"url": f"https://example.org/{i}"} for i in range(25)]}

        self.assertEqual(len(indexes.make_index("q", response, 2)["results"]), 2)
        self.assertEqual(len(indexes.make_index("q", response, 100)["results"]), 20)
        for limit in [0, -1]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                indexes.make_index("q", response, limit)

#checks save_index and load_index, JSON have to enable continuation of work, and markdown check of results
    def test_persists_json_and_markdown_with_stable_ids(self):
        index = indexes.make_index("članak", {"results": [
            {"title": "Članak", "url": "https://example.org/a", "snippet": "Opis"}],
            "receipt": {"status": "observed"}}, 20)
        with tempfile.TemporaryDirectory() as directory:
            path = indexes.save_index(Path(directory), index)
            loaded = indexes.load_index(path)
            self.assertEqual(loaded, index)
            markdown = path.with_suffix(".md").read_text(encoding="utf-8")
            self.assertIn("1.", markdown)
            self.assertIn("Članak", markdown)
            self.assertIn("https://example.org/a", markdown)

#
    def test_filenames_are_safe_short_and_collision_resistant(self):
        first = indexes.query_filename("CON: a/b?")
        second = indexes.query_filename("CON: a\\b?")
        self.assertNotEqual(first, second)
        self.assertLess(len(indexes.query_filename("x" * 1000)), 90)
        self.assertNotRegex(first, r'[<>:"/\\|?*]')


    def test_selection_validates_all_ids_before_resolving(self):
        index = {"results": [{"id": 1}, {"id": 2}]}
        self.assertEqual(indexes.select_results(index, [2, 2, 1]),
                         [{"id": 2}, {"id": 1}])
        with self.assertRaises(ValueError):
            indexes.select_results(index, [1, 99])


#for functions written with async def so they can wait web response
class JobsTests(unittest.IsolatedAsyncioTestCase):
    async def test_query_failure_does_not_stop_jobs_and_new_runs_are_separate(self):
        jobs = [{"name": "diabetes", "queries": ["one", "two"],
                 "max_results_per_query": 20}]
        search = AsyncMock(side_effect=[RuntimeError("offline"),
            {"results": [], "receipt": {"status": "observed"}}])
        with tempfile.TemporaryDirectory() as directory:
            with patch("scraping.research.indexes.search_query", search), \
                 patch("scraping.research.indexes.asyncio.sleep", new_callable=AsyncMock) as sleep:
                paths = await indexes.run_jobs(object(), jobs, Path(directory))
                self.assertEqual(len(paths), 2)
                self.assertEqual(indexes.load_index(paths[0])["status"], "failed")
                self.assertEqual(indexes.load_index(paths[1])["status"], "empty")
                sleep.assert_awaited_with(2)
                search.side_effect = None
                search.return_value = {"results": [], "receipt": {"status": "observed"}}
                next_paths = await indexes.run_jobs(object(), jobs, Path(directory))
                self.assertNotEqual(paths[0].parent, next_paths[0].parent)

    async def test_unsafe_job_name_rejected_before_request(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch("scraping.research.indexes.search_query", new_callable=AsyncMock) as search:
            for name in ["../escape", "CON", "a/b"]:
                with self.assertRaises(ValueError):
                    await indexes.run_jobs(object(), [{"name": name, "queries": ["q"],
                        "max_results_per_query": 20}], Path(directory))
            search.assert_not_awaited()
