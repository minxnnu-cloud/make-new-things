#!/usr/bin/env python3
"""Phase 2: classify harvested skills into a taxonomy and score supply vs demand.

Three corrections matter more than the taxonomy itself, because without them the
raw counts are badly misleading:

 1. Generated families. One vendor ships ~726 near-identical "Automate {App} via
    Rube MCP" wrappers. Left alone they triple the apparent supply of integration
    skills. Any signature repeated >=GEN_MIN times inside one owner collapses to a
    single unit tagged `generated`.
 2. Cross-repo copies. The same skill is vendored into many repos. Identical
    (slug, description signature) collapses to one unit; `copies` records how
    widely it was re-hosted, which is itself a demand signal.
 3. Star attribution. A 78-skill repo must not hand each skill its full star
    count, so stars are split across the skills a repo ships.

Supply = distinct surviving skills. Demand = star mass + curation-list attention
+ how often a skill was copied. High demand over thin supply is a gap.
"""
import json, math, os, re, sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
GEN_MIN = 5          # >= this many identical signatures from one owner == generated family
REPO_CAP = 25        # max units one repo may contribute to one category's supply
FRESH_CUTOFF = "2026-05-01"

TAXONOMY = [
    ("Document & File Processing",
     r"\b(pdf|docx|word document|pptx|powerpoint|slide deck|xlsx|excel|spreadsheet|csv|epub|ebook|ocr|latex|resume|cv |invoice|file format|document convert)\b"),
    ("Testing & QA",
     r"\b(unit test|integration test|e2e|end-to-end|test case|test coverage|tdd|test-driven|pytest|jest|vitest|qa\b|regression|flaky|mutation test|snapshot test|fuzz)\b"),
    ("Debugging & Troubleshooting",
     r"\b(debug|debugging|root cause|stack trace|troubleshoot|crash|postmortem|incident|error analysis|bisect)\b"),
    ("Security & Compliance",
     r"\b(security|vulnerab|pentest|penetration test|exploit|cve\b|owasp|threat model|secret scan|sast|dast|semgrep|codeql|malware|compliance|soc ?2|gdpr|hipaa|supply chain|hardening)\b"),
    ("DevOps & Infrastructure",
     r"\b(docker|kubernetes|k8s|terraform|helm|ci/cd|ci pipeline|github actions|jenkins|deploy|deployment|infrastructure|aws\b|gcp\b|azure|serverless|cloudformation|ansible|nginx|sre\b|provision)\b"),
    ("Observability & Monitoring",
     r"\b(observability|monitoring|telemetry|opentelemetry|logging|log analysis|metrics|tracing|alerting|grafana|prometheus|datadog|sentry|uptime|dashboards?)\b"),
    ("Data & Analytics",
     r"\b(data analysis|analytics|dataframe|pandas|etl\b|data pipeline|data clean|statistic|bigquery|warehouse|dbt\b|jupyter|visuali[sz]ation|chart|plotting|power ?bi|tableau|looker|metabase|reporting|pivot)\b"),
    ("Database & SQL",
     r"\b(sql\b|postgres|mysql|sqlite|mongodb|redis|database|schema migration|orm\b|prisma|supabase|query optimi|indexing)\b"),
    ("Web & Browser Automation",
     r"\b(browser automation|playwright|puppeteer|selenium|scrap(?:e|ing)|crawler|web automation|headless browser|screenshot|chrome extension|dom\b)\b"),
    ("Frontend & UI Engineering",
     r"\b(react|vue\b|svelte|next\.?js|nuxt|tailwind|shadcn|css\b|frontend|front-end|component library|storybook|responsive|web component|html\b|framer[- ]motion|animatepresence|jsx|tsx\b|dom manipulation|form validation|state management|redux|zustand)\b"),
    ("Design & Creative Media",
     r"\b(design system|ui/ux|ux design|figma|brand guideline|logo|illustration|generative art|algorithmic art|animation|video|image generat|photo|canvas|typography|color palette|3d\b|blender|theme|styling)\b"),
    ("Mobile Development",
     r"\b(ios\b|android|swift|swiftui|kotlin|react native|expo\b|flutter|mobile app|xcode|app store|simulator)\b"),
    ("API & Integration",
     r"\b(rest api|graphql|openapi|swagger|webhook|sdk\b|api client|api design|oauth|mcp server|grpc)\b"),
    ("SaaS App Automation",
     r"\b(automate .{0,24} tasks|rube mcp|composio|zapier|salesforce|hubspot|airtable|shopify|stripe\b|quickbooks|workflow automation)\b"),
    ("AI & LLM Tooling",
     r"\b(openai|gpt-|gemini|elevenlabs|text-to-speech|tts\b|whisper|stable diffusion|huggingface|replicate|fine-?tun|inference|model context protocol|llm\b|prompt cach|embeddings?)\b"),
    ("Communication & Messaging",
     r"\b(slack|telegram|whatsapp|discord|email|gmail|sms\b|notification|inbox|newsletter send|chat message|calendar invite)\b"),
    ("Writing & Content",
     r"\b(writing|copywrit|blog post|editing prose|proofread|style guide|storytell|screenplay|content creation|ghostwrit|translat|localization|i18n|summari[sz])\b"),
    ("Marketing, Sales & SEO",
     r"\b(seo\b|marketing|growth|advertis|campaign|landing page|social media|linkedin|crm\b|sales|lead gen|outreach|brand voice|competitor analysis|ad copy|tweet|twitter|x\.com|thread\b|link ?building|content brief|content distribution|keyword|backlink|funnel|conversion rate|launch post|virality|audience)\b"),
    ("Product & Strategy",
     r"\b(product manage|\bpm\b|prd\b|roadmap|product spec|feature spec|scope creep|prioriti[sz]|okr\b|kpi\b|user stor|persona|market fit|positioning|go-to-market|gtm\b|discovery|pre-?mortem|business model|pricing strateg|naming|competitive landscape|stakeholder|vertical\b)\b"),
    ("Evaluation & Benchmarking",
     r"\b(\beval\b|evals\b|evaluat|judge|llm-as-a-judge|benchmark|rubric|scoring|grading|golden (?:set|build|test)|ground truth|a/b test|quality gate|leaderboard)\b"),
    ("UX Research & Audit",
     r"\b(ux (?:audit|review|research|copy|writing)|usability|nielsen|heuristic evaluation|user research|user interview|journey map|wireframe|information architecture|design critique|devex|developer experience|microcopy|error message|empty state|onboarding flow)\b"),
    # Legal/finance keywords are deliberately multilingual: a single German-statute
    # dump ships ~14k skills and a Turkish one ~1k, and an English-only pattern sent
    # all of them to Unclassified.
    ("Finance, Legal & Compliance Ops",
     r"(\b(finance|financial|accounting|invoice process|tax\b|bookkeep|budget|legal|contract review|nda\b|due diligence|patent|trademark|valuation|payroll|audit trail)\b"
     r"|\b(recht|gesetz|vertrag|paragraf|paragraph \d|gmbh\b|bgb\b|hgb\b|stgb\b|zpo\b|anwalt|kanzlei|klage|haftung|insolvenz|steuer|urteil|richter|mietrecht|arbeitsrecht|kirchenrecht|sanierung|aufsichtsrat)"
     r"|\b(hukuk|kanun|madde\b|mahkeme|dava|avukat|sözleşme|ceza)\b"
     r"|(法律|合同|诉讼|法规|条款))"),
    ("Research & Science",
     r"\b(research|literature review|scientific|bioinform|chemistry|physics|academic paper|citation|arxiv|systematic review|experiment|hypothesis)\b"),
    ("Education & Learning",
     r"\b(tutor|teaching|lesson|curriculum|flashcard|quiz|study guide|exam|student|explainer|pedagog|course)\b"),
    ("Productivity & Personal Ops",
     r"\b(todo|task manag|calendar|scheduling|note-?taking|obsidian|notion|second brain|meeting notes|journal|habit|personal knowledge)\b"),
    ("Collaboration & Code Review",
     r"\b(code review|pull request|pr review|jira|linear\b|standup|sprint|project manag|changelog|release notes|git worktree|branch|commit message|merge conflict|version control)\b"),
    ("Agent & Workflow Orchestration",
     r"\b(subagent|multi-agent|orchestrat|agent workflow|parallel agents|delegation|swarm|agent team|handoff|dispatch)\b"),
    ("Engineering Process & Discipline",
     r"\b(brainstorm|implementation plan|writing plans|executing plans|verification before|spec-driven|specification|requirements|design doc|rfc\b|decision record|estimation|retrospective|checklist)\b"),
    ("Memory & Context Engineering",
     r"\b(memory|context window|context engineering|rag\b|retrieval|vector (?:db|store|search)|knowledge graph|semantic search|session state|persistence)\b"),
    ("Meta: Skill & Prompt Authoring",
     r"\b(skill creat|create (?:a )?skill|writing skills|skill author|meta[- ]skill|prompt engineer|prompt optimi|slash command|plugin scaffold|skill template|eval harness|skill\.md)\b"),
    ("Code Quality & Refactoring",
     r"\b(refactor|lint|code quality|static analysis|type check|typescript|dead code|technical debt|code smell|formatting|architecture review|legacy code|migration guide|formal verification|dafny|coq\b|proof assistant|invariant|code explain|explains? .{0,12}code|design pattern)\b"),
    ("Documentation",
     r"\b(documentation|docs site|readme|api docs|docstring|adr\b|architecture decision|runbook|knowledge base|tutorial writ|onboarding doc)\b"),
    ("Accessibility & Assistive",
     r"\b(accessib|a11y|screen reader|wcag|aria\b|assistive|dyslex|caption|alt text)\b"),
    ("Game & Simulation",
     r"\b(game dev|godot|unity|unreal|game design|roguelike|simulation|procedural generation|shader|level design|player journey|gameplay|narrative design|quest)\b"),
    ("Healthcare & Bio",
     r"\b(clinical|medical|healthcare|patient|diagnos|genomic|drug discovery|fhir|ehr\b)\b"),
    ("Terminal & Developer Environment",
     r"\b(terminal|shell|bash script|zsh|cli tool|dotfiles|tmux|neovim|vim\b|editor config|environment setup|package manager|monorepo)\b"),
]
COMPILED = [(lbl, re.compile(rx, re.I)) for lbl, rx in TAXONOMY]


def classify(strong, weak):
    """strong = the skill's own text; weak = repo-level text (shared by siblings).

    Repo text may only break ties between labels the skill's OWN text already
    supports. Letting it score on its own put 12,509 German-statute skills into
    "Research & Science" purely because their shared repo blurb matched there.
    """
    scores = {}
    for lbl, rx in COMPILED:
        s = len(rx.findall(strong or ""))
        if s:
            scores[lbl] = s + 0.25 * len(rx.findall(weak or ""))
    return sorted(scores.items(), key=lambda x: -x[1])


LANGS = [
    ("de", re.compile(r"(wenn es um|geht:|der|die|und|für|nicht|Recht|Gesetz|werden|einen)")),
    ("tr", re.compile(r"(ve|için|ile|bir|olarak|hukuk|madde)")),
    ("zh", re.compile(r"[一-鿿]")),
    ("ko", re.compile(r"[가-힯]")),
    ("ja", re.compile(r"[぀-ヿ]")),
    ("es", re.compile(r"(para|con|los|las|una|del|que|cuando)")),
    ("fr", re.compile(r"(pour|avec|les|des|une|dans|lorsque)")),
]


def detect_lang(text):
    t = text or ""
    if not t.strip():
        return "?"
    best, score = "en", 1.5          # English is the default; others must beat it
    for code, rx in LANGS:
        n = len(rx.findall(t))
        if code in ("zh", "ko", "ja"):
            n = n / 3.0
        if n > score:
            best, score = code, n
    return best


PLACEHOLDER = re.compile(
    r"^(one sentence|brief description|short description|what this skill does"
    r"|todo|tbd|description here|your description|lorem ipsum|\.\.\.|n/a)\b", re.I)


def signature(text):
    """Collapse proper nouns/numbers so template families share one signature."""
    t = re.sub(r"[A-Z][A-Za-z0-9_.-]*", " X ", text or "")
    return re.sub(r"\W+", " ", t.lower()).strip()[:110]


def load(fn):
    p = os.path.join(OUT, fn)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    deep = load("skills_deep.json")
    raw = load("skills_raw.json")
    topic = load("repos_topic.json")
    if not deep:
        print("run harvest.py first", file=sys.stderr)
        sys.exit(1)

    meta = {}
    if topic:
        for r in topic["repos"]:
            meta[r["full_name"]] = r

    list_hits = defaultdict(set)
    if raw:
        for s in raw["skills"]:
            if s.get("repo_full"):
                list_hits[s["repo_full"]].update(s["listed_in"])

    rows_in = deep["skills"]

    # --- 1. generated-family detection, per owner ---
    fam = Counter((s["repo"].split("/")[0], signature(s["description"])) for s in rows_in
                  if s.get("description", "").strip())
    generated = {k for k, n in fam.items() if n >= GEN_MIN}

    # --- 2. cross-repo copy collapse ---
    units, seen = [], {}
    n_generated_collapsed = 0
    for s in rows_in:
        desc = s.get("description", "") or ""
        owner = s["repo"].split("/")[0]
        sig = signature(desc)
        is_gen = (owner, sig) in generated and desc.strip()
        m = meta.get(s["repo"], {})
        stars = m.get("stargazers_count") or s.get("repo_stars") or 0
        n_in_repo = max(1, s.get("skills_in_repo") or 1)
        key = ("GEN", owner, sig) if is_gen else (s.get("slug", ""), sig)
        if key in seen:
            u = seen[key]
            u["copies"] += 1
            u["copy_repos"].add(s["repo"])
            if stars > u["stars"]:
                u["stars"], u["repo"] = stars, s["repo"]
            if is_gen:
                n_generated_collapsed += 1
            continue
        strong = " ".join(filter(None, [s.get("fm_name"), (s.get("slug") or "").replace("-", " "), desc]))
        weak = m.get("description") or s.get("repo_description") or ""
        ranked = classify(strong, weak)
        u = {
            "slug": s.get("slug") or s.get("fm_name"), "repo": s["repo"], "owner": owner,
            "placeholder": bool(PLACEHOLDER.match(desc.strip())) or not desc.strip(),
            "lang": detect_lang(desc),
            "description": desc[:400],
            "primary": ranked[0][0] if ranked else "Unclassified",
            "labels": [l for l, _ in ranked[:3]],
            "generated": is_gen, "copies": 1, "copy_repos": {s["repo"]},
            "stars": stars, "star_share": stars / n_in_repo,
            "pushed_at": (m.get("pushed_at") or s.get("repo_pushed_at") or "")[:10],
            "n_lists": len(list_hits.get(s["repo"], ())),
            "has_desc": bool(desc.strip()),
            "body_chars": s.get("body_chars", 0),
            "from_bulk_repo": n_in_repo > 100,
        }
        seen[key] = u
        units.append(u)

    for u in units:
        u["copy_repos"] = len(u["copy_repos"])

    live = [u for u in units if not u["generated"] and not u["placeholder"]]

    # Winsorize star credit. anthropics/skills (170k stars, 20 skills) and
    # obra/superpowers (273k stars, 14 skills) hand each of their skills 8-20k
    # stars, so whichever category they touch wins on attention alone. Those
    # numbers measure the repo's fame, not per-skill demand. Clip at p95.
    shares = sorted(u["star_share"] for u in live)
    p95 = shares[int(len(shares) * 0.95)] if shares else 0.0
    n_clipped = 0
    for u in live:
        if u["star_share"] > p95:
            u["star_share_raw"] = u["star_share"]
            u["star_share"] = p95
            n_clipped += 1

    # --- 3. per-repo capping ---------------------------------------------------
    # Twenty repos hold 62% of every SKILL.md found; one German-statute dump alone
    # ships 23,793. A bulk dump is one author's decision to mass-produce, not N
    # independent offerings, so each repo contributes at most REPO_CAP units to a
    # category's supply. Author count is the primary supply measure regardless.
    per = defaultdict(lambda: defaultdict(int))
    for u in live:
        per[u["primary"]][u["repo"]] += 1

    agg = defaultdict(lambda: {"raw": 0, "repos": set(), "owners": set(), "stars": 0.0,
                               "top": 0, "listed": 0, "fresh": 0, "copied": 0, "ex": [],
                               "seen_from": defaultdict(int), "capped": 0,
                               "traction100": set(), "traction1k": set(),
                               "depth": [], "bulk": 0})
    for u in live:
        a = agg[u["primary"]]
        a["raw"] += 1
        a["seen_from"][u["repo"]] += 1
        if a["seen_from"][u["repo"]] <= REPO_CAP:
            a["capped"] += 1
        a["repos"].add(u["repo"])
        a["owners"].add(u["owner"])
        if u["stars"] >= 100:
            a["traction100"].add(u["repo"])
        if u["stars"] >= 1000:
            a["traction1k"].add(u["repo"])
        a["stars"] += u["star_share"]
        a["top"] = max(a["top"], u["stars"])
        a["listed"] += 1 if u["n_lists"] else 0
        a["copied"] += u["copies"] - 1
        a["depth"].append(u["body_chars"])
        if u["from_bulk_repo"]:
            a["bulk"] += 1
        if u["pushed_at"] >= FRESH_CUTOFF:
            a["fresh"] += 1
        if len(a["ex"]) < 8 and u["stars"]:
            a["ex"].append("%s/%s (%d*)" % (u["repo"], u["slug"], u["stars"]))

    rows = []
    for cat, a in agg.items():
        authors = len(a["owners"])
        capped = a["capped"]
        bulk = sorted(((n, r) for r, n in per[cat].items() if n > REPO_CAP), reverse=True)[:3]
        rows.append({
            "category": cat,
            "supply_authors": authors,
            "supply_repos": len(a["repos"]),
            "supply_skills_capped": capped,
            "supply_skills_raw": a["raw"],
            "bulk_sources": ["%s (%d)" % (r, n) for n, r in bulk],
            "star_mass": round(a["stars"]),
            "top_repo_stars": a["top"],
            # repos that actually got traction - robust to the long zero-star tail
            # that flattens any per-skill star average
            "median_body_chars": (sorted(a["depth"])[len(a["depth"]) // 2] if a["depth"] else 0),
            "bulk_share": round(a["bulk"] / a["raw"], 3) if a["raw"] else 0,
            "traction_repos_100": len(a["traction100"]),
            "traction_repos_1k": len(a["traction1k"]),
            "traction_rate": round(len(a["traction100"]) / len(a["repos"]), 3) if a["repos"] else 0,
            "copies": a["copied"],
            "curated_hits": a["listed"],
            "fresh_share": round(a["fresh"] / a["raw"], 2) if a["raw"] else 0,
            # attention each distinct offering attracts
            "attention_per_skill": round(a["stars"] / capped, 1) if capped else 0,
            # how many independent people already serve this need
            "builder_density": authors,
            "examples": a["ex"],
        })

    # rank: high attention per offering, thin builder base
    for r in rows:
        r["gap_score"] = round(
            math.log10(1 + r["attention_per_skill"]) / math.log10(10 + r["builder_density"]), 3)
    rows.sort(key=lambda r: -r["gap_score"])

    summary = {
        "harvested_skill_files": len(rows_in),
        "generated_family_files_collapsed": n_generated_collapsed,
        "generated_families": sum(1 for u in units if u["generated"]),
        "placeholder_dropped": sum(1 for u in units if u["placeholder"] and not u["generated"]),
        "cross_repo_copies_collapsed": sum(u["copies"] - 1 for u in live),
        "distinct_skills": len(live),
        "no_description": sum(1 for u in live if not u["has_desc"]),
        "unclassified": sum(1 for u in live if u["primary"] == "Unclassified"),
        "repos_swept": topic["n_repos"] if topic else None,
        "repo_cap_applied": REPO_CAP,
        "star_share_p95_cap": round(p95, 1),
        "star_shares_clipped": n_clipped,
    }

    with open(os.path.join(OUT, "gap_analysis.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows, "units": live}, f, ensure_ascii=False)

    for k, v in summary.items():
        print("%-34s %s" % (k, v))
    print()
    w = "%-34s %7s %6s %7s %9s %9s %7s %6s"
    print(w % ("CATEGORY", "AUTHORS", "REPOS", "SKILLS", "RAW", "STAR_MASS", "ATT/SK", "GAP"))
    print("-" * 96)
    for r in rows:
        print(w % (r["category"][:34], r["supply_authors"], r["supply_repos"],
                   r["supply_skills_capped"], r["supply_skills_raw"], r["star_mass"],
                   r["attention_per_skill"], r["gap_score"]))


if __name__ == "__main__":
    main()
