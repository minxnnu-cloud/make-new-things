#!/usr/bin/env python3
"""Phase 2b: mine GitHub issues for skills people ask for but do not have.

Star counts only measure what already exists and got popular; they cannot show
demand that nothing satisfies. Issue text can: someone opening "is there a skill
for X" is stating an unmet need directly. Classified with the same taxonomy as
supply, this gives a demand distribution that is independent of supply.
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "skill-gap-survey/1.0", "Accept": "application/vnd.github+json"}
SLEEP = 7.0
PER_PAGE = 100

QUERIES = [
    '"skill for" in:title claude',
    '"claude skill" in:title',
    '"agent skill" in:title',
    '"skill request" in:title',
    '"is there a skill"',
    '"would be great" skill claude in:body',
    '"add a skill" in:title',
    '"new skill" in:title claude',
    '"skill idea" in:title',
    '"missing skill" OR "no skill for"',
    'SKILL.md in:title',
    '"skills" label:enhancement claude in:title',
]

items = {}
calls = 0
log = []


def search(q, page):
    global calls
    url = ("https://api.github.com/search/issues?q=%s&per_page=%d&page=%d&sort=created&order=desc"
           % (urllib.parse.quote(q + " type:issue"), PER_PAGE, page))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                calls += 1
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                w = 20 * (attempt + 1)
                print("    rate-limited, sleeping %ds" % w, file=sys.stderr, flush=True)
                time.sleep(w)
                continue
            if e.code == 422:
                return None
            print("    HTTP %s on %r" % (e.code, q), file=sys.stderr, flush=True)
            return None
        except Exception as ex:
            print("    err %s" % ex, file=sys.stderr, flush=True)
            time.sleep(5)
    return None


def checkpoint():
    tmp = os.path.join(OUT, "demand_issues.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"n_issues": len(items), "search_calls": calls, "log": log,
                   "issues": list(items.values())}, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(OUT, "demand_issues.json"))


def resume():
    p = os.path.join(OUT, "demand_issues.json")
    if not os.path.exists(p):
        return set()
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    for i in d["issues"]:
        items[i["url"]] = i
    log.extend(d.get("log", []))
    print("resumed: %d issues" % len(items), file=sys.stderr)
    return {l["query"] for l in d.get("log", [])}


def run(q, max_pages=10):
    added = 0
    for page in range(1, max_pages + 1):
        d = search(q, page)
        time.sleep(SLEEP)
        if not d:
            break
        got = d.get("items", [])
        if not got:
            break
        for it in got:
            u = it["html_url"]
            if u in items:
                continue
            items[u] = {
                "url": u,
                "title": it.get("title", ""),
                "body": (it.get("body") or "")[:1200],
                "repo": "/".join(it["repository_url"].split("/")[-2:]),
                "created_at": it.get("created_at", "")[:10],
                "state": it.get("state"),
                "comments": it.get("comments", 0),
                "reactions": (it.get("reactions") or {}).get("total_count", 0),
                "found_by": q,
            }
            added += 1
        print("  %-44s p%-2d +%-4d total=%d" % (q[:44], page, len(got), len(items)),
              file=sys.stderr, flush=True)
        if len(got) < PER_PAGE:
            break
    log.append({"query": q, "new": added})
    checkpoint()
    return added


done = resume()
for q in QUERIES:
    if q in done:
        print("[skip] %s" % q, file=sys.stderr, flush=True)
        continue
    print("[query] %s" % q, file=sys.stderr, flush=True)
    run(q)

checkpoint()
print("\nDONE  issues=%d  search_calls=%d" % (len(items), calls), file=sys.stderr, flush=True)
