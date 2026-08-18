#!/usr/bin/env python3
"""Phase 1: harvest Claude Skill listings from curation repos into one dataset."""
import json, re, os, sys, urllib.request, urllib.error, time

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "skill-gap-survey/1.0"}


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
        except Exception:
            time.sleep(1 + i)
    return None


def read(fn):
    with open(os.path.join(RAW, fn), encoding="utf-8") as f:
        return f.read()


def parse_repo(url):
    """-> (owner, repo, subpath) for github urls, else (None, None, '')"""
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)(?:/tree/[^/]+/(.*?))?/?(?:[#?].*)?$", url)
    if not m:
        return (None, None, "")
    return (m.group(1), m.group(2).replace(".git", ""), (m.group(3) or "").rstrip("/"))


records = []


def add(**kw):
    kw.setdefault("category", "")
    kw.setdefault("description", "")
    kw.setdefault("author", "")
    records.append(kw)


# ---------- 1. composio: "### Cat" then "- [name](url) - desc *By [@a](..)*"
def parse_composio():
    txt = read("composio.md")
    cat = None
    started = False
    for line in txt.splitlines():
        if line.startswith("## "):
            started = line.strip() == "## Skills"
            cat = None
            continue
        if not started:
            continue
        if line.startswith("### "):
            cat = line[4:].strip()
            continue
        m = re.match(r"^-\s+\[([^\]]+)\]\(([^)]+)\)\s*[-–—]\s*(.*)$", line)
        if not m or not cat:
            continue
        name, url, desc = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        am = re.search(r"\*By \[@?([^\]]+)\]", desc)
        author = am.group(1) if am else ""
        desc = re.sub(r"\s*\*By \[.*?\]\(.*?\)\*\s*$", "", desc).strip()
        if url.startswith("./") or url.startswith("/"):
            url = "https://github.com/ComposioHQ/awesome-claude-skills/tree/master/" + url.lstrip("./")
        add(name=name, url=url, description=desc, category=cat, author=author,
            source="ComposioHQ/awesome-claude-skills")


# ---------- 2. travisvn: "- **[n](u)** - d" bullets and "| **[n](u)** | d |" tables
def parse_travisvn():
    txt = read("travisvn.md")
    h2 = None
    cat = None
    for line in txt.splitlines():
        if line.startswith("## "):
            h2 = line[3:].strip()
            cat = None
            continue
        if line.startswith("### "):
            cat = line[4:].strip()
            continue
        if not h2 or "Skill" not in h2:
            continue
        m = re.match(r"^-\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*[-–—]\s*(.*)$", line)
        if not m:
            m = re.match(r"^\|\s*\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*\|\s*(.*?)\s*\|\s*$", line)
        if not m:
            continue
        add(name=m.group(1).strip(), url=m.group(2).strip(), description=m.group(3).strip(),
            category=(cat or h2), source="travisvn/awesome-claude-skills")


# ---------- 3. karanb192: "#### slug" blocks with **Source:** / **Description:**
def parse_karanb192():
    txt = read("karanb192.md")
    h2 = None
    cat = None
    cur = None

    def flush():
        if cur and cur.get("name"):
            add(**cur)

    for line in txt.splitlines():
        if line.startswith("## "):
            if cur:
                flush()
            cur = None
            h2 = line[3:].strip()
            cat = None
            continue
        if line.startswith("### "):
            if cur:
                flush()
            cur = None
            cat = re.sub(r"^[^\w]+", "", line[4:].strip())
            continue
        if line.startswith("#### "):
            if cur:
                flush()
            cur = {"name": line[5:].strip(), "url": "", "description": "",
                   "category": cat or h2 or "", "author": "",
                   "source": "karanb192/awesome-claude-skills"}
            continue
        if cur is None:
            continue
        sm = re.match(r"^\*\*Source:\*\*\s*\[([^\]]+)\]\(([^)]+)\)", line)
        if sm:
            cur["url"] = sm.group(2).strip()
            cur["author"] = sm.group(1).split("/")[0]
            continue
        dm = re.match(r"^\*\*Description:\*\*\s*(.*)$", line)
        if dm:
            cur["description"] = dm.group(1).strip()
            continue
        um = re.match(r"^\*\*Use Case:\*\*\s*(.*)$", line)
        if um:
            cur["use_case"] = um.group(1).strip()
    if cur:
        flush()


# ---------- 4. awesome-claude-code: "## Skills" section plus skill-shaped entries
#             elsewhere (it is a general Claude Code list, so many skills sit under
#             topical sections like Security / Design & UI-UX / Creative Media).
SKILLY = re.compile(r"\bskills?\b", re.I)


def parse_acc():
    txt = read("awesome-claude-code.md")
    h2 = h3 = None
    skipped = 0
    for line in txt.splitlines():
        if line.startswith("## "):
            h2 = line[3:].strip()
            h3 = None
            continue
        if line.startswith("### "):
            h3 = line[4:].strip()
            continue
        if not h2 or h2 in ("Recently Added", "The Claude Code Ticker - A Sample of Claude Code Projects Around GitHub"):
            continue
        m = re.match(r"^-\s+\[([^\]]+)\]\(([^)]+)\)\s*(?:by\s+\[([^\]]+)\]\([^)]+\)\s*)?[-–—]\s*(.*)$", line)
        if not m:
            continue
        name, url, author, desc = (m.group(1).strip(), m.group(2).strip(),
                                   (m.group(3) or "").strip(), m.group(4).strip())
        in_skills_section = (h2 == "Skills")
        if not in_skills_section and not (SKILLY.search(name) or SKILLY.search(desc)):
            skipped += 1
            continue
        cat = h2 if in_skills_section else ("%s / %s" % (h2, h3) if h3 else h2)
        add(name=name, url=url, author=author, description=desc, category=cat,
            source="hesreallyhim/awesome-claude-code")
    print("    (acc: skipped %d non-skill entries)" % skipped, file=sys.stderr)


# ---------- 5. anthropics/skills: live directory + SKILL.md frontmatter
def parse_anthropics():
    j = get("https://api.github.com/repos/anthropics/skills/contents/skills")
    if not j:
        print("  ! anthropics dir listing failed", file=sys.stderr)
        return
    for e in json.loads(j):
        if e.get("type") != "dir":
            continue
        slug = e["name"]
        md = get("https://raw.githubusercontent.com/anthropics/skills/main/skills/%s/SKILL.md" % slug) or ""
        desc = ""
        fm = re.match(r"^---\n(.*?)\n---", md, re.S)
        if fm:
            dm = re.search(r"^description:\s*(?:[|>]-?\s*\n\s*)?(.*?)(?=\n[a-z_]+:|\Z)", fm.group(1), re.S | re.M)
            if dm:
                desc = " ".join(dm.group(1).split()).strip().strip('"').strip("'")
        add(name=slug, url="https://github.com/anthropics/skills/tree/main/skills/%s" % slug,
            description=desc[:600], category="Official (Anthropic)", author="anthropics",
            source="anthropics/skills")


# ---------- 6. obra/superpowers: live skills directory + README descriptions
def parse_superpowers():
    listing = None
    for path in ("skills", "plugins/superpowers/skills"):
        j = get("https://api.github.com/repos/obra/superpowers/contents/%s" % path)
        if j:
            try:
                listing = (path, json.loads(j))
            except Exception:
                listing = None
            if listing:
                break
    readme_desc, cat_of = {}, {}
    cur_cat = ""
    for line in read("superpowers.md").splitlines():
        cm = re.match(r"^\*\*([A-Za-z /&]+)\*\*\s*$", line)
        if cm:
            cur_cat = cm.group(1).strip()
            continue
        m = re.match(r"^-\s+\*\*([a-z0-9-]+)\*\*\s*[-–—]\s*(.*)$", line)
        if m:
            readme_desc[m.group(1)] = m.group(2).strip()
            cat_of[m.group(1)] = cur_cat
    if listing:
        path, entries = listing
        for e in entries:
            if e.get("type") != "dir":
                continue
            slug = e["name"]
            add(name=slug,
                url="https://github.com/obra/superpowers/tree/main/%s/%s" % (path, slug),
                description=readme_desc.get(slug, ""),
                category=cat_of.get(slug, "Superpowers"), author="obra",
                source="obra/superpowers")
    else:
        for slug, d in readme_desc.items():
            add(name=slug, url="https://github.com/obra/superpowers", description=d,
                category=cat_of.get(slug, "Superpowers"), author="obra",
                source="obra/superpowers")


for fn in (parse_composio, parse_travisvn, parse_karanb192, parse_acc,
           parse_anthropics, parse_superpowers):
    n0 = len(records)
    fn()
    print("  %-22s +%d" % (fn.__name__, len(records) - n0), file=sys.stderr)


# ---------- normalize + dedupe ----------
def norm_name(n):
    n = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
    n = re.sub(r"^(claude-|the-)", "", n)
    n = re.sub(r"(-skill|-skills|-for-claude)$", "", n)
    return n


merged = {}
for r in records:
    owner, repo, sub = parse_repo(r["url"])
    slug = norm_name(sub.split("/")[-1]) if sub else norm_name(r["name"])
    key = "%s/%s#%s" % (owner, repo, slug) if owner else "url:%s" % r["url"].rstrip("/")
    m = merged.get(key)
    if not m:
        m = merged[key] = {
            "key": key, "name": r["name"], "slug": slug, "owner": owner, "repo": repo,
            "repo_full": ("%s/%s" % (owner, repo)) if owner else None, "subpath": sub,
            "url": r["url"], "descriptions": {}, "categories": [], "listed_in": [],
            "author": r.get("author", ""),
        }
    if r["description"]:
        m["descriptions"][r["source"]] = r["description"]
    if r["category"] and r["category"] not in m["categories"]:
        m["categories"].append(r["category"])
    if r["source"] not in m["listed_in"]:
        m["listed_in"].append(r["source"])
    if not m["author"] and r.get("author"):
        m["author"] = r["author"]
    if r.get("use_case"):
        m["use_case"] = r["use_case"]

skills = list(merged.values())
for s in skills:
    s["n_lists"] = len(s["listed_in"])
    s["description"] = max(s["descriptions"].values(), key=len) if s["descriptions"] else ""

with open(os.path.join(OUT, "skills_raw.json"), "w", encoding="utf-8") as f:
    json.dump({
        "collected_sources": sorted({r["source"] for r in records}),
        "n_raw_entries": len(records),
        "n_unique": len(skills),
        "skills": skills,
    }, f, ensure_ascii=False, indent=1)

print("\nraw entries: %d  ->  unique skills: %d" % (len(records), len(skills)), file=sys.stderr)
print("unique repos: %d" % len({s["repo_full"] for s in skills if s["repo_full"]}), file=sys.stderr)
