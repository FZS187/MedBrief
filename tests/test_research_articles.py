import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, patch

from scraping.research import articles, indexes


FIXTURES = Path(__file__).parent / "fixtures" / "research"


def page_fixture():
    return json.loads((FIXTURES / "article.json").read_text(encoding="utf-8"))


def saved_index(root, run="run1", query="diabetes documentation", urls=None):
    urls = urls or ["https://example.org/article"]
    index = indexes.make_index(query, {"receipt": {"status": "observed"},
        "results": [{"title": f"Article {i}", "url": url}
                    for i, url in enumerate(urls, 1)]}, 20)
    return indexes.save_index(root / "diabetes" / run / "searches", index)


class QualityTests(unittest.TestCase):
    def test_markdown_retains_headings_links_and_references(self):
        result = articles.prepare_article(page_fixture())
        self.assertEqual(result["status"], "success")
        self.assertIn("## References", result["body"])
        self.assertIn("[Original](https://example.org/source)", result["body"])
        self.assertEqual(result["format"], "markdown")

    def test_failures_empty_captcha_login_and_pdf_are_not_articles(self):
        variations = [
            {"receipt": {"status": "failed", "failure": {"code": "TIMEOUT"}}},
            {"main_text": "", "text": "", "content": ""},
            {"title": "Verify you are human", "main_text": "Please complete the CAPTCHA"},
            {"title": "Sign in", "main_text": "Sign in to continue"},
            {"content_type": "application/pdf"},
            {"content_type": "application/json"},
            {"receipt": {"status": "observed", "http_status": 403}},
        ]
        for changes in variations:
            page = page_fixture() | changes
            with self.subTest(changes=changes):
                result = articles.prepare_article(page)
                self.assertIn(result["status"], ["failed", "unsupported"])
                self.assertFalse(result["body"])

    def test_short_or_unstructured_body_requires_review(self):
        short = page_fixture() | {"main_text": "Short extract."}
        self.assertEqual(articles.prepare_article(short)["status"], "partial")
        plain = page_fixture() | {"content_type": "text/html"}
        result = articles.prepare_article(plain)
        self.assertEqual(result["format"], "plain_text")
        self.assertEqual(result["status"], "partial")

    @unittest.skipUnless(importlib.util.find_spec("trafilatura"), "Requires main extraction dependency")
    def test_html_extraction_preserves_table_list_and_reference(self):
        page = page_fixture() | {"content_type": "text/html",
            "content": (FIXTURES / "article.html").read_text(encoding="utf-8")}
        result = articles.prepare_article(page)
        self.assertEqual(result["status"], "success")
        self.assertIn("Document date", result["body"])
        self.assertIn("Original report", result["body"])
        self.assertIn("https://example.org/source", result["body"])
        self.assertNotIn("Unrelated navigation", result["body"])
        self.assertNotIn("Unrelated footer", result["body"])


class ScrapeTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_id_makes_no_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = saved_index(Path(directory))
            with patch("scraping.research.articles.read_page", new_callable=AsyncMock) as read:
                with self.assertRaises(ValueError):
                    await articles.scrape_selected(object(), path, [1, 99])
                read.assert_not_awaited()

    async def test_writes_article_provenance_report_and_skips_success_on_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = saved_index(Path(directory))
            with patch("scraping.research.articles.read_page", new_callable=AsyncMock,
                       return_value=page_fixture()) as read:
                report = await articles.scrape_selected(object(), path, [1, 1])
                again = await articles.scrape_selected(object(), path, [1])
            self.assertEqual(read.await_count, 1)
            item = report["items"][0]
            self.assertEqual(item["status"], "success")
            self.assertEqual(again["items"][0]["status"], "success")
            article = Path(directory) / "diabetes" / item["file"]
            text = article.read_text(encoding="utf-8")
            self.assertIn("https://example.org/article", text)
            self.assertIn("diabetes documentation", text)
            self.assertIn("fixture-trace", text)
            self.assertIn("## References", text)
            disk = json.loads((path.parent.parent / "scrape_status.json").read_text(encoding="utf-8"))
            self.assertEqual(disk["items"][0]["status"], "success")

    async def test_one_failure_does_not_stop_other_urls_and_report_is_incremental(self):
        with tempfile.TemporaryDirectory() as directory:
            path = saved_index(Path(directory), urls=[f"https://example.org/{i}" for i in range(3)])
            calls = 0

            async def read(web, url):
                nonlocal calls
                if calls:
                    disk = json.loads((path.parent.parent / "scrape_status.json").read_text(encoding="utf-8"))
                    self.assertEqual(len(disk["items"]), calls)
                calls += 1
                if calls == 2:
                    raise RuntimeError("offline")
                return page_fixture() | {"url": url}

            with patch("scraping.research.articles.read_page", side_effect=read), \
                 patch("scraping.research.articles.asyncio.sleep", new_callable=AsyncMock) as sleep:
                report = await articles.scrape_selected(object(), path, [1, 2, 3])
            self.assertEqual([r["status"] for r in report["items"]], ["success", "failed", "success"])
            self.assertEqual(sleep.await_count, 2)

    async def test_same_url_across_runs_is_reused_with_all_query_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = saved_index(root, "run1", "first query")
            second = saved_index(root, "run2", "second query")
            with patch("scraping.research.articles.read_page", new_callable=AsyncMock,
                       return_value=page_fixture()) as read:
                await articles.scrape_selected(object(), first, [1])
                report = await articles.scrape_selected(object(), second, [1])
            self.assertEqual(read.await_count, 1)
            refs = report["items"][0]["references"]
            self.assertEqual({r["query"] for r in refs}, {"first query", "second query"})
            article = root / "diabetes" / report["items"][0]["file"]
            self.assertIn("second query", article.read_text(encoding="utf-8"))

    async def test_partial_saved_separately_and_retried_only_when_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = saved_index(Path(directory))
            with patch("scraping.research.articles.read_page", new_callable=AsyncMock,
                       side_effect=[page_fixture() | {"main_text": "Short extract."}, page_fixture()]) as read:
                report = await articles.scrape_selected(object(), path, [1])
                self.assertEqual(report["items"][0]["status"], "partial")
                partial = Path(directory) / "diabetes" / report["items"][0]["file"]
                self.assertTrue(partial.name.endswith(".partial.md"))
                await articles.scrape_selected(object(), path, [])
                self.assertEqual(read.await_count, 1)
                report = await articles.scrape_selected(object(), path, [1])
                self.assertEqual(report["items"][0]["status"], "success")
