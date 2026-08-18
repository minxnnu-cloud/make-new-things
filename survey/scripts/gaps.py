#!/usr/bin/env python3
"""Phase 2d: match each explicit request against the supply corpus.

Category-level scores are too coarse to pick what to build, and the star-based
demand axis turned out not to discriminate between categories at all (traction
rate sits at 30-49% everywhere). What does discriminate is whether a specific
thing people asked for already exists.

So: index all 155k supplied skills by content word, score every request-shaped
issue against that index, and surface the requests nothing matches well.
"""
import json, math, os, re, sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
sys.path.insert(0, HERE)
from report import request_shaped  # noqa: E402

STOP = set("""a an the and or but if then else for to of in on at by with without from into
over under again further once here there all any both each few more most other some such no
nor not only own same so than too very can will just should now this that these those it its
is are was were be been being have has had do does did doing as i you he she we they what which
who whom when where why how add create support request idea proposal feat feature new skill
skills claude code agent agents use using used make made need needs want wants please help
would like also get set run via let allow enable provide give take work works working file
files repo repository issue issues pr github project projects tool tools plugin plugins""".split())
TOKEN = re.compile(r"[a-z][a-z0-9+#.-]{2,}")


def toks(text):
    return {t for t in TOKEN.findall((text or "").lower()) if t not in STOP and len(t) > 2}


def load(fn):
    p = os.path.join(OUT, fn)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    supply = load("gap_analysis.json")
    issues = load("demand_issues.json")
    if not supply or not issues:
        print("need gap_analysis.json and demand_issues.json", file=sys.stderr)
        sys.exit(1)

    units = supply["units"]
    print("indexing %d skills..." % len(units), file=sys.stderr, flush=True)

    unit_toks = []
    index = defaultdict(list)
    for i, u in enumerate(units):
        t = toks("%s %s" % ((u.get("slug") or "").replace("-", " "), u.get("description", "")))
        unit_toks.append(t)
        for w in t:
            index[w].append(i)

    N = len(units)
    idf = {w: math.log(N / (1.0 + len(ix))) for w, ix in index.items()}
    # a word in half the corpus carries no signal; ignore it when matching
    COMMON = {w for w, ix in index.items() if len(ix) > N * 0.02}

    reqs = [it for it in issues["issues"] if request_shaped(it["title"])]
    print("scoring %d requests..." % len(reqs), file=sys.stderr, flush=True)

    scored = []
    for it in reqs:
        q = toks(it["title"]) - COMMON
        if len(q) < 2:
            continue
        cand = Counter()
        for w in q:
            if w not in index:
                continue
            iw = idf[w]
            for i in index[w]:
                cand[i] += iw
        qmass = sum(idf.get(w, 0.0) for w in q) or 1.0
        best, best_i = 0.0, None
        for i, sc in cand.most_common(40):
            cov = sc / qmass                      # share of the ask the skill covers
            j = len(q & unit_toks[i]) / len(q | unit_toks[i])   # jaccard, penalises breadth
            v = 0.7 * cov + 0.3 * j
            if v > best:
                best, best_i = v, i
        m = units[best_i] if best_i is not None else None
        scored.append({
            "title": it["title"], "repo": it["repo"], "url": it["url"],
            "created_at": it["created_at"],
            "reactions": it.get("reactions", 0), "comments": it.get("comments", 0),
            "match_score": round(best, 3),
            "best_match": ("%s/%s" % (m["repo"], m["slug"])) if m else None,
            "best_match_desc": (m.get("description", "")[:140]) if m else None,
            "query_terms": sorted(q)[:12],
        })

    scored.sort(key=lambda r: (r["match_score"], -r["reactions"]))
    unmatched = [r for r in scored if r["match_score"] < 0.25]

    # cluster the unmatched asks by their shared distinctive terms
    tf = Counter()
    for r in unmatched:
        tf.update(set(r["query_terms"]))
    themes = [(w, n) for w, n in tf.most_common(60) if n >= 3]

    with open(os.path.join(OUT, "request_gaps.json"), "w", encoding="utf-8") as f:
        json.dump({"n_requests_scored": len(scored), "n_unmatched": len(unmatched),
                   "themes": themes, "requests": scored}, f, ensure_ascii=False, indent=1)

    print("\nscored=%d  unmatched(<0.25)=%d  (%.0f%%)"
          % (len(scored), len(unmatched), 100.0 * len(unmatched) / max(1, len(scored))))
    print("\n--- recurring terms among unmatched asks ---")
    for w, n in themes[:30]:
        print("   %-24s %d" % (w, n))
    print("\n--- 25 lowest-match requests ---")
    for r in unmatched[:25]:
        print("   [%.2f] %s" % (r["match_score"], r["title"][:96]))


if __name__ == "__main__":
    main()
