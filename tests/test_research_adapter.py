import importlib.util
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from scraping.research import adapter


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.policy = patch("scraping.research.adapter.free_policy",
                            side_effect=lambda **extra: SimpleNamespace(**(adapter.FREE_POLICY | extra)))
        self.policy.start()
        self.addCleanup(self.policy.stop)

    async def test_search_uses_only_named_free_sources_and_never_reads_articles(self):
        web = SimpleNamespace(search=AsyncMock(side_effect=[
            {"source": "duckduckgo_html", "results": [],
             "receipt": {"status": "failed", "failure": {"code": "RATE_LIMITED"}}},
            {"source": "bing_rss", "results": [{"title": "Public", "url": "https://example.org/a"}],
             "receipt": {"status": "observed"}, "coverage": "returned-results"}]),
            read=AsyncMock())
        with patch("scraping.research.adapter.asyncio.sleep", new_callable=AsyncMock) as sleep:
            found = await adapter.search_query(web, "diabetes documentation", 20)
        self.assertEqual(found["results"][0]["title"], "Public")
        self.assertEqual(found["coverage"], "partial")
        self.assertEqual([c.kwargs["source"] for c in web.search.await_args_list],
                         ["duckduckgo_html", "bing_rss"])
        for call in web.search.await_args_list:
            policy = call.kwargs["policy"]
            self.assertFalse(policy.allow_paid_fallbacks)
            self.assertEqual(policy.provider, "http")
            self.assertTrue(policy.block_private_network)
            self.assertEqual(policy.search_date_reads, 0)
        web.read.assert_not_awaited()
        sleep.assert_awaited_once_with(2)

    async def test_empty_and_failed_sources_stay_distinct(self):
        for state, expected in [("observed", "observed"), ("failed", "failed")]:
            web = SimpleNamespace(search=AsyncMock(return_value={"results": [],
                "receipt": {"status": state, "failure": {"code": "TIMEOUT"} if state == "failed" else None}}))
            with patch("scraping.research.adapter.asyncio.sleep", new_callable=AsyncMock):
                result = await adapter.search_query(web, "q", 20)
            self.assertEqual(result["receipt"]["status"], expected)

    async def test_private_or_non_web_url_never_reaches_provider(self):
        web = SimpleNamespace(read=AsyncMock())
        for url in ["http://127.0.0.1/x", "http://[::1]/", "http://10.0.0.1/",
                    "http://169.254.169.254/", "http://localhost/", "file:///tmp/x",
                    "https://user:pass@example.org/", "https://example.org:bad/"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                await adapter.read_page(web, url)
        web.read.assert_not_awaited()

    async def test_http_only_and_private_final_url_rejected(self):
        web = SimpleNamespace(read=AsyncMock(return_value={"url": "http://127.0.0.1/",
            "receipt": {"status": "observed"}}))
        with self.assertRaises(ValueError):
            await adapter.read_page(web, "https://example.org/a")
        call = web.read.await_args
        self.assertEqual(call.kwargs["provider"], "http")
        policy = call.kwargs["policy"]
        self.assertFalse(policy.allow_paid_fallbacks)
        self.assertFalse(policy.allow_local_browser)
        self.assertFalse(policy.allow_real_browser)
        self.assertFalse(policy.completeness_escalation)
        self.assertFalse(policy.use_egress_pool)
        self.assertFalse(policy.rescue_not_found)
        self.assertTrue(policy.main_content)


@unittest.skipUnless(importlib.util.find_spec("frankensurf"), "Requires research dependencies (WSL)")
class RealContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_policy_is_accepted_by_pinned_library(self):
        import importlib.metadata
        self.assertEqual(importlib.metadata.version("frankensurf"), "0.52.0")
        policy = adapter.free_policy()
        self.assertFalse(policy.allow_paid_fallbacks)
        self.assertEqual(policy.search_source_allow, ("duckduckgo_html", "bing_rss"))

    async def test_runtime_blocks_private_redirect_before_sending_it(self):
        import httpx
        from frankensurf import Runtime
        requested = []

        def respond(request):
            requested.append(str(request.url))
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

        with tempfile.TemporaryDirectory() as directory:
            async with Runtime(state_dir=directory, transport=httpx.MockTransport(respond)) as web:
                page = await adapter.read_page(web, "https://93.184.216.34/start")
        self.assertEqual(page["receipt"]["status"], "failed")
        self.assertEqual(page["receipt"]["failure"]["code"], "POLICY_DENIED")
        self.assertEqual(requested, ["https://93.184.216.34/start"])
