#!/usr/bin/env python3
"""Recover public feed revisions and prepare source material for an agent."""
import argparse
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = "zarazhangrui/follow-builders"
FEEDS = {"x": "feed-x.json", "blogs": "feed-blogs.json", "podcasts": "feed-podcasts.json"}
UTC = timezone.utc


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value, zone):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (result.replace(tzinfo=zone) if result.tzinfo is None else result).astimezone(UTC)


def canonical_url(value):
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("missing or invalid content URL")
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "msclkid"}]
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                                   urllib.parse.urlencode(sorted(query)), ""))


class FetchError(Exception):
    pass


class HistoryError(FetchError):
    def __init__(self, message, commits):
        super().__init__(message)
        self.commits = commits


class Client:
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")

    def get_json(self, url):
        headers = {"User-Agent": "follow-builders-digest", "Accept": "application/vnd.github+json"}
        if urllib.parse.urlsplit(url).hostname == "api.github.com":
            headers["X-GitHub-Api-Version"] = "2026-03-10"
            if self.token:
                headers["Authorization"] = "Bearer " + self.token
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as res:
                    return json.load(res)
            except urllib.error.HTTPError as exc:
                if exc.code not in {500, 502, 503, 504}:
                    if exc.code == 429 or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0"):
                        raise FetchError("GitHub rate limit exceeded; set GITHUB_TOKEN or retry after quota reset") from None
                    raise FetchError(f"HTTP {exc.code} fetching {url}") from None
                message = f"HTTP {exc.code} fetching {url}"
            except (urllib.error.URLError, TimeoutError, OSError):
                message = f"Network error fetching {url}"
            except (ValueError, UnicodeError):
                raise FetchError(f"Invalid JSON fetching {url}") from None
            if attempt < 2:
                time.sleep(2 ** attempt)
        raise FetchError(message)

    def api(self, endpoint, **params):
        return self.get_json(f"https://api.github.com/repos/{REPO}/{endpoint}?" + urllib.parse.urlencode(params))

    def revisions(self, head, path, start, now):
        commits = []
        page = 1
        try:
            while True:
                batch = self.api("commits", sha=head, path=path, since=iso(start), until=iso(now),
                                 per_page=100, page=page)
                if not isinstance(batch, list):
                    raise FetchError("Invalid commit listing")
                commits.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            baseline = self.api("commits", sha=head, path=path, until=iso(start), per_page=1)
            if not isinstance(baseline, list):
                raise FetchError("Invalid baseline listing")
        except FetchError as exc:
            raise HistoryError(str(exc), sorted(commits, key=lambda c: (c["commit"]["committer"]["date"], c["sha"]))) from None
        unique = {c["sha"]: c for c in commits + baseline}
        return sorted(unique.values(), key=lambda c: (c["commit"]["committer"]["date"], c["sha"]))


def normalize(kind, feed, origin, counts, errors):
    rows = feed.get(kind)
    if not isinstance(rows, list):
        raise ValueError(f"{kind} must be an array")
    flat = []
    if kind == "x":
        for account in rows:
            if not isinstance(account, dict) or not isinstance(account.get("tweets"), list):
                errors.append("Invalid X account/tweets")
                continue
            flat.extend((tweet, account) for tweet in account["tweets"])
    else:
        flat = [(row, row) for row in rows]
    items = []
    for row, author in flat:
        counts["observations"] += 1
        if not isinstance(row, dict):
            counts["invalid_items"] += 1
            errors.append("Invalid item object")
            continue
        date = row.get("createdAt" if kind == "x" else "publishedAt")
        try:
            published = parse_time(date, UTC) if isinstance(date, str) else None
        except (ValueError, TypeError):
            published = None
        if published is None:
            counts["excluded_dates"] += 1
            continue
        try:
            url = canonical_url(row.get("url", ""))
            if kind == "x":
                identity = str(row.get("id") or "")
            elif kind == "podcasts":
                identity = json.dumps([row.get("name"), row.get("guid")], ensure_ascii=False)
                if not row.get("name") or not row.get("guid"):
                    raise ValueError("missing podcast source or GUID")
            else:
                identity = url
            if not identity:
                raise ValueError("missing stable ID")
            body = row.get({"x": "text", "blogs": "content", "podcasts": "transcript"}[kind]) or ""
            if not isinstance(body, str):
                raise ValueError("body must be a string")
            items.append({"id": kind + ":" + identity, "source": kind,
                          "author": author.get("name", ""), "handle": author.get("handle", ""),
                          "title": row.get("title", ""), "body": body, "url": url,
                          "published_at": iso(published), "provenance": [origin.copy()]})
        except (ValueError, TypeError, AttributeError):
            counts["invalid_items"] += 1
            errors.append("Invalid identity, URL or body")
    return items


def merge(items, start, end):
    unique = {}
    for item in items:
        old = unique.get(item["id"])
        if old:
            item = dict(item)
            item["provenance"] = old["provenance"] + item["provenance"]
            if not item["body"].strip():
                item["body"] = old["body"]
        unique[item["id"]] = item
    eligible = [item for item in unique.values()
                if start <= parse_time(item["published_at"], UTC) < end]
    return sorted(eligible, key=lambda i: (i["source"], i["published_at"], i["id"]))


def prepare(client, start, end, now, language, zone, run_dir):
    manifest = {"status": "failed", "run_at": iso(now), "start": iso(start), "end": iso(end),
                "timezone": zone, "language": language, "repository": REPO,
                "head_sha": None, "feeds": {}, "errors": [], "item_count": 0}
    all_items = []
    try:
        head = client.api("commits/main")["sha"]
        if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
            raise FetchError("Invalid HEAD SHA")
        manifest["head_sha"] = head
    except (FetchError, KeyError, TypeError) as exc:
        manifest["errors"].append(str(exc))
    if manifest["head_sha"]:
        with tempfile.TemporaryDirectory(prefix="follow-builders-") as temp:
            for kind, path in FEEDS.items():
                report = {"snapshots": [], "errors": [], "warnings": [], "observations": 0,
                          "excluded_dates": 0, "invalid_items": 0, "successful_snapshots": 0}
                manifest["feeds"][kind] = report
                generated_times = set()
                try:
                    revisions = client.revisions(head, path, start, now)
                except HistoryError as exc:
                    report["errors"].append(f"Incomplete history lookup: {exc}")
                    revisions = exc.commits
                except (FetchError, KeyError, TypeError, ValueError) as exc:
                    report["errors"].append(f"History lookup failed: {exc}")
                    revisions = []
                if not revisions:
                    report["errors"].append("No feed snapshots available")
                for commit in revisions:
                    origin = {"sha": commit["sha"], "path": path,
                              "committed_at": commit["commit"]["committer"]["date"]}
                    snapshot = {**origin, "status": "failed"}
                    report["snapshots"].append(snapshot)
                    try:
                        feed = client.get_json(f"https://raw.githubusercontent.com/{REPO}/{commit['sha']}/{path}")
                        if not isinstance(feed, dict):
                            raise ValueError("feed must be an object")
                        temporary = Path(temp) / (kind + ".json")
                        temporary.write_text(json.dumps(feed, ensure_ascii=False), encoding="utf-8")
                        origin["generated_at"] = feed.get("generatedAt")
                        snapshot["generated_at"] = origin["generated_at"]
                        local_errors = []
                        items = normalize(kind, feed, origin, report, local_errors)
                        report["errors"].extend(f"{commit['sha']}: {e}" for e in sorted(set(local_errors)))
                        all_items.extend(items)
                        snapshot["status"] = "ok"
                        report["successful_snapshots"] += 1
                        upstream_errors = feed.get("errors", [])
                        if upstream_errors:
                            report["errors"].append(f"{commit['sha']} upstream: {upstream_errors}")
                        try:
                            generated_times.add(parse_time(feed.get("generatedAt"), UTC))
                        except (ValueError, TypeError, AttributeError):
                            report["warnings"].append(f"{commit['sha']}: missing/invalid generatedAt")
                    except (FetchError, ValueError, TypeError, KeyError) as exc:
                        report["errors"].append(f"{commit['sha']}: {exc}")
                times = sorted(generated_times)
                if times:
                    report["latest_generated_at"] = iso(times[-1])
                    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(times, times[1:])]
                    report["max_update_gap_hours"] = round(max(gaps, default=0), 2)
                    if max(gaps, default=0) > 36:
                        report["warnings"].append("Feed update gap exceeds 36 hours; coverage may be incomplete")
                    if now - times[-1] > timedelta(hours=36):
                        report["warnings"].append("Latest feed is more than 36 hours old")
                report["status"] = ("failed" if not report["successful_snapshots"] else
                                    "partial" if report["errors"] else "ok")
    items = merge(all_items, start, end)
    manifest["item_count"] = len(items)
    reports = list(manifest["feeds"].values())
    if any(r["successful_snapshots"] for r in reports):
        manifest["status"] = "partial" if any(r["status"] != "ok" for r in reports) else "ok"
    run_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in (("items.json", {"items": items}), ("manifest.json", manifest)):
        (run_dir / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not items and manifest["status"] != "failed":
        notes = []
        for kind, report in manifest["feeds"].items():
            notes.extend(f"- {kind}: {e}" for e in report["errors"] + report["warnings"])
            if report["excluded_dates"]:
                notes.append(f"- {kind}: 排除 {report['excluded_dates']} 次缺失或无效发布时间的观察记录。")
        text = (f"# Follow Builders digest\n\n周期：{iso(start)} 至 {iso(end)}（终点不包含）\n\n"
                f"运行时间：{iso(now)}\n\n截至本次运行，上游 Git 历史中可获取的内容。\n\n"
                "该周期未找到符合条件的内容。\n\n数据质量：\n" +
                ("\n".join(notes) if notes else "未报告获取错误；上游采集范围不代表完整内容。") + "\n")
        (run_dir / "digest.md").write_text(text, encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--days", type=int)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    now = datetime.now(UTC)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
        if not isinstance(config, dict):
            raise ValueError("config must be an object")
        zone_name = config.get("timezone", "Asia/Shanghai")
        zone = ZoneInfo(zone_name)
        if bool(args.start) != bool(args.end) or (args.start and args.days is not None):
            raise ValueError("--start and --end must be paired and cannot be combined with --days")
        days = args.days if args.days is not None else config.get("days", 7)
        if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
            raise ValueError("days must be a positive integer")
        start = parse_time(args.start, zone) if args.start else now - timedelta(days=days)
        end = parse_time(args.end, zone) if args.end else now
        if start >= end or start > now:
            raise ValueError("period must have start < end and start <= run time")
        output = args.output_dir or Path(config.get("output_dir", "./output"))
        output.mkdir(parents=True, exist_ok=True)
        run_dir = Path(tempfile.mkdtemp(prefix=now.strftime("%Y%m%dT%H%M%SZ-"), dir=output)).resolve()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    manifest = prepare(Client(), start, end, now, config.get("language", "zh-CN"), zone_name, run_dir)
    print(json.dumps({"status": manifest["status"], "run_dir": str(run_dir),
                      "item_count": manifest["item_count"]}, ensure_ascii=False))
    return 1 if manifest["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
