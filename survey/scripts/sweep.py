#!/usr/bin/env python3
"""Phase 1b: sweep GitHub search for skill repos across topics/keywords.

Unauthenticated search API: 10 req/min, separate pool from the 60/hr core limit.
Max 1000 results per distinct query, so broad topics are sliced by star ranges.
"""
import json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "skill-gap-survey/1.0", "Accept": "application/vnd.github+json"}
PER_PAGE = 100
SLEEP = 7.0  # 10 req/min budget with headroom

QUERIES = [
    "topic:claude-skills",
    "topic:claude-code-skills",
    "topic:claude-skill",
    "topic:claude-code-skill",
    "topic:agent-skills",
    "topic:agent-skill",
    "topic:claude-code-plugin",
    "claude-skill in:name",
    "claude skills in:name,description",
    "SKILL.md in:readme claude",
]
# broad topics get sliced so we can exceed the 1000-result ceiling
SLICES = ["stars:>2000", "stars:500..2000", "stars:100..499", "stars:20..99", "stars:1..19"]
SLICE_QUERIES = {"topic:claude-skills", "topic:claude-code-skills"}

FIELDS = ("full_name", "html_url", "description", "stargazers_count", "forks_count",
          "open_issues_count", "pushed_at", "created_at", "size", "archived", "fork")

repos = {}
calls = 0
log = []


def search(q, page):
    global calls
    url = ("https://api.github.com/search/repositories?q=%s&per_page=%d&page=%d&sort=stars&order=desc"
           % (urllib.parse.quote(q), PER_PAGE, page))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                calls += 1
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                wait = 20 * (attempt + 1)
                print("    rate-limited, sleeping %ds" % wait, file=sys.stderr, flush=True)
                time.sleep(wait)
                continue
            if e.code == 422:  # past the 1000-result ceiling
                return None
            print("    HTTP %s on %r p%d" % (e.code, q, page), file=sys.stderr, flush=True)
            return None
        except Exception as ex:
            print("    err %s" % ex, file=sys.stderr, flush=True)
            time.sleep(5)
    return None


import urllib.parse  # noqa: E402


def checkpoint():
    out = {"n_repos": len(repos), "search_calls": calls, "log": log,
           "repos": sorted(repos.values(), key=lambda r: -(r["stargazers_count"] or 0))}
    tmp = os.path.join(OUT, "repos_topic.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(OUT, "repos_topic.json"))


def resume():
    p = os.path.join(OUT, "repos_topic.json")
    if not os.path.exists(p):
        return set()
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    for r in d["repos"]:
        repos[r["full_name"]] = r
    log.extend(d.get("log", []))
    print("resumed: %d repos, %d queries already done" % (len(repos), len(log)), file=sys.stderr)
    return {l["query"] for l in d.get("log", [])}


def run_query(q, max_pages=10):
    added = 0
    for page in range(1, max_pages + 1):
        d = search(q, page)
        time.sleep(SLEEP)
        if not d:
            break
        items = d.get("items", [])
        if not items:
            break
        for it in items:
            fn = it["full_name"]
            rec = repos.get(fn)
            if not rec:
                rec = repos[fn] = {k: it.get(k) for k in FIELDS}
                rec["topics"] = it.get("topics") or []
                rec["license"] = (it.get("license") or {}).get("spdx_id")
                rec["found_by"] = []
                added += 1
            if q not in rec["found_by"]:
                rec["found_by"].append(q)
        print("  %-42s p%-2d +%-4d total=%d" % (q[:42], page, len(items), len(repos)),
              file=sys.stderr, flush=True)
        if len(items) < PER_PAGE:
            break
    log.append({"query": q, "new": added, "total_after": len(repos)})
    checkpoint()          # survive a mid-run kill
    return added


done_queries = resume()

plan = []
for q in QUERIES:
    plan.extend(["%s %s" % (q, sl) for sl in SLICES] if q in SLICE_QUERIES else [q])

for q in plan:
    if q in done_queries:
        print("[skip] %s" % q, file=sys.stderr, flush=True)
        continue
    print("[query] %s" % q, file=sys.stderr, flush=True)
    run_query(q)

checkpoint()
print("\nDONE  repos=%d  search_calls=%d" % (len(repos), calls), file=sys.stderr, flush=True)
