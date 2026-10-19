import importlib.util
import io
import json
import tempfile
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location("prepare_digest", Path(__file__).parents[1] / "scripts/prepare_digest.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

START = m.parse_time("2026-10-01T00:00:00Z", m.UTC)
END = START + timedelta(days=7)
NOW = END + timedelta(days=2)
SHA = "a" * 40


def commit(sha=SHA, date="2026-10-09T06:00:00Z"):
    return {"sha": sha, "commit": {"committer": {"date": date}}}


def tweet(id="1", date="2026-10-02T00:00:00Z", text="hello"):
    return {"id": id, "createdAt": date, "text": text, "url": f"https://x.com/builder/status/{id}"}


def feed(tweets):
    return {"generatedAt": m.iso(NOW), "x": [{"name": "Builder", "handle": "builder", "tweets": tweets}]}


def counts():
    return {"observations": 0, "invalid_items": 0, "excluded_dates": 0}


class FakeClient:
    def __init__(self, failures=(), empty=False):
        self.failures = failures
        self.empty = empty

    def api(self, path):
        return {"sha": SHA}

    def revisions(self, head, path, start, now):
        assert head == SHA
        return [commit()]

    def get_json(self, url):
        kind = next(k for k, p in m.FEEDS.items() if url.endswith(p))
        if kind in self.failures:
            raise m.FetchError("fixture unavailable")
        if kind == "x":
            return feed([] if self.empty else [tweet()])
        return {kind: [], "generatedAt": m.iso(NOW)}


class PrepareTests(unittest.TestCase):
    def test_timezone_and_boundaries(self):
        self.assertEqual(m.parse_time("2026-10-01", ZoneInfo("Asia/Shanghai")), START - timedelta(hours=8))
        rows = m.normalize("x", feed([tweet("1", m.iso(START)), tweet("2", m.iso(END)),
                                     tweet("3", None), tweet("4", "bad")]), {}, c := counts(), [])
        self.assertEqual(c["excluded_dates"], 2)
        self.assertEqual([i["id"] for i in m.merge(rows, START, END)], ["x:1"])

    def test_latest_version_and_body_fallback(self):
        rows = []
        for version in ["old", "new", ""]:
            rows += m.normalize("x", feed([tweet(text=version)]), {"sha": version}, counts(), [])
        items = m.merge(rows, START, END)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["body"], "new")
        self.assertEqual(len(items[0]["provenance"]), 3)

    def test_podcast_identity_not_channel_url(self):
        rows = [{"name": "Podcast", "guid": g, "publishedAt": m.iso(START),
                 "url": "https://youtube.com/@channel", "transcript": "body"} for g in ["a", "b"]]
        items = m.normalize("podcasts", {"podcasts": rows}, {}, counts(), [])
        self.assertEqual(len(m.merge(items, START, END)), 2)

    def test_url_keeps_semantics(self):
        self.assertEqual(m.canonical_url("https://example.com/story?utm_source=x&id=2#part"),
                         "https://example.com/story?id=2")
        self.assertNotEqual(m.canonical_url("https://example.com/story?id=2"),
                            m.canonical_url("https://example.com/story?id=3"))

    def run_fixture(self, client):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            result = m.prepare(client, START, END, NOW, "zh-CN", "Asia/Shanghai", directory)
            items = json.loads((directory / "items.json").read_text())["items"]
            return result, items, (directory / "digest.md").exists()

    def test_delayed_collection_and_partial_failure(self):
        result, items, _ = self.run_fixture(FakeClient(failures=["blogs"]))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(items), 1)
        self.assertGreater(m.parse_time(items[0]["provenance"][0]["committed_at"], m.UTC), END)
        self.assertEqual(result["feeds"]["blogs"]["status"], "failed")

    def test_empty_differs_from_failure(self):
        empty, items, digest = self.run_fixture(FakeClient(empty=True))
        self.assertEqual(empty["status"], "ok")
        self.assertEqual(items, [])
        self.assertTrue(digest)
        failed, _, digest = self.run_fixture(FakeClient(failures=list(m.FEEDS)))
        self.assertEqual(failed["status"], "failed")
        self.assertFalse(digest)

    def test_empty_digest_keeps_diagnostics_in_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            result = m.prepare(FakeClient(failures=["blogs"], empty=True), START, END, NOW,
                               "zh-CN", "Asia/Shanghai", directory)
            digest = (directory / "digest.md").read_text()
            self.assertEqual(result["status"], "partial")
            self.assertTrue(result["feeds"]["blogs"]["errors"])
            self.assertIn("2026-10-01 08:00", digest)
            self.assertIn("该周期未找到符合条件的内容。", digest)
            self.assertNotIn("fixture unavailable", digest)
            self.assertNotIn("数据质量", digest)
            self.assertNotIn("运行时间", digest)

    def test_one_snapshot_failure_does_not_discard_other_snapshot(self):
        client = FakeClient()
        client.revisions = lambda *a: [commit("b" * 40), commit()]
        get = client.get_json
        client.get_json = lambda url: (_ for _ in ()).throw(m.FetchError("bad snapshot")) if "b" * 40 in url else get(url)
        result, items, _ = self.run_fixture(client)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(items), 1)

    def test_pagination_and_baseline(self):
        client = m.Client()
        calls = []
        def api(endpoint, **params):
            calls.append(params)
            if "since" not in params:
                return [commit("c" * 40, m.iso(START - timedelta(hours=1)))]
            return [commit(f"{i:040x}") for i in range(100)] if params["page"] == 1 else [commit("d" * 40)]
        client.api = api
        revisions = client.revisions(SHA, m.FEEDS["x"], START, NOW)
        self.assertEqual(len(revisions), 102)
        self.assertEqual([c.get("page") for c in calls], [1, 2, None])
        self.assertTrue(all(c["sha"] == SHA for c in calls))
        self.assertEqual(calls[0]["until"], m.iso(NOW))

    def test_retries_and_no_retry_for_auth_or_rate_limit(self):
        client = m.Client()
        for code, expected in [(503, 3), (401, 1), (403, 1), (429, 1)]:
            error = m.urllib.error.HTTPError("https://api.github.com/example", code, "error", {}, None)
            with patch.object(m.urllib.request, "urlopen", side_effect=error) as opening, patch.object(m.time, "sleep"):
                with self.assertRaises(m.FetchError):
                    client.get_json("https://api.github.com/example")
                self.assertEqual(opening.call_count, expected)

    def test_upstream_errors_and_staleness(self):
        client = FakeClient(empty=True)
        get = client.get_json
        def stale(url):
            result = get(url)
            result["generatedAt"] = m.iso(START)
            if url.endswith(m.FEEDS["x"]):
                result["errors"] = ["source unavailable"]
            return result
        client.get_json = stale
        result, _, _ = self.run_fixture(client)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["feeds"]["x"]["warnings"])

    def test_head_failure_keeps_report(self):
        client = FakeClient()
        client.api = lambda *a: (_ for _ in ()).throw(m.FetchError("rate limited"))
        result, items, digest = self.run_fixture(client)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errors"], ["rate limited"])
        self.assertEqual(items, [])
        self.assertFalse(digest)

    def test_later_history_page_failure_keeps_available_commits(self):
        client = m.Client()
        def api(endpoint, **params):
            if params["page"] == 1:
                return [commit(f"{i:040x}") for i in range(100)]
            raise m.FetchError("page unavailable")
        client.api = api
        with self.assertRaises(m.HistoryError) as failure:
            client.revisions(SHA, m.FEEDS["x"], START, NOW)
        self.assertEqual(len(failure.exception.commits), 100)
        partial = FakeClient()
        partial.revisions = lambda *a: (_ for _ in ()).throw(m.HistoryError("page unavailable", [commit()]))
        result, items, _ = self.run_fixture(partial)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(items), 1)

    def test_invalid_feed_schema_is_failure(self):
        client = FakeClient()
        client.get_json = lambda url: {"unexpected": []}
        result, _, _ = self.run_fixture(client)
        self.assertEqual(result["status"], "failed")

    def run_cli_fixture(self, *args):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(sys, "argv", ["prepare_digest.py", "--output-dir", temp, *args]), \
                patch.object(m, "Client", return_value=FakeClient()), \
                patch.object(m, "datetime", wraps=datetime) as clock, \
                patch.object(sys, "stdout", new_callable=io.StringIO) as stdout:
            clock.now.return_value = NOW
            self.assertEqual(m.main(), 0)
            run_dir = Path(json.loads(stdout.getvalue())["run_dir"])
            self.assertEqual(run_dir.parent, Path(temp).resolve())
            return json.loads((run_dir / "manifest.json").read_text())

    def test_cli_defaults_without_configuration(self):
        manifest = self.run_cli_fixture()
        self.assertEqual(manifest["start"], m.iso(NOW - timedelta(days=7)))
        self.assertEqual(manifest["end"], m.iso(NOW))
        self.assertEqual(manifest["language"], "zh-CN")
        self.assertEqual(manifest["timezone"], "Asia/Shanghai")

    def test_cli_requested_days_and_language(self):
        manifest = self.run_cli_fixture("--days", "14", "--language", "en")
        self.assertEqual(manifest["start"], m.iso(NOW - timedelta(days=14)))
        self.assertEqual(manifest["language"], "en")

    def test_cli_requested_timezone_and_calendar_period(self):
        manifest = self.run_cli_fixture("--start", "2026-10-01", "--end", "2026-10-08",
                                        "--timezone", "America/New_York")
        self.assertEqual(manifest["start"], "2026-10-01T04:00:00Z")
        self.assertEqual(manifest["end"], "2026-10-08T04:00:00Z")
        self.assertEqual(manifest["timezone"], "America/New_York")

    def test_cli_invalid_period_does_not_fetch(self):
        script = str(Path(__file__).parents[1] / "scripts/prepare_digest.py")
        for args in [["--start", "2026-10-01"], ["--days", "0"],
                     ["--start", "2026-10-01", "--end", "2026-10-02", "--days", "7"],
                     ["--start", "2026-10-02", "--end", "2026-10-01"],
                     ["--timezone", "Invalid/Timezone"], ["--language", " "]]:
            result = subprocess.run([sys.executable, script] + args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
