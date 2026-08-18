#!/usr/bin/env python3
"""Phase 1c: deep-harvest actual SKILL.md files from candidate repos.

Streams each repo's codeload tarball (no GitHub API quota) and reads the YAML
frontmatter of every SKILL.md inside. This yields skill-level records — a repo
holding 40 skills counts as 40, not 1 — which is what supply-density analysis needs.
"""
import io, json, os, re, sys, tarfile, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "skill-gap-survey/1.0"}
# GitHub's reported repo size counts full history, so it predicts tarball size
# poorly (a repo reported at 810MB downloaded as 2MB). Bound the actual stream
# instead and keep the reported-size filter loose so small-snapshot repos survive.
MAX_BYTES = 40 * 1024 * 1024      # abort a repo that streams past this
MAX_REPO_KB = 4 * 1024 * 1024     # only skips absurd outliers
WORKERS = 16

lock = threading.Lock()
done = [0]


class TooBig(Exception):
    pass


class Capped(io.RawIOBase):
    """Read-through wrapper that aborts once MAX_BYTES have been streamed."""

    def __init__(self, fp):
        self.fp = fp
        self.n = 0

    def readable(self):
        return True

    def read(self, size=-1):
        b = self.fp.read(size)
        self.n += len(b)
        if self.n > MAX_BYTES:
            raise TooBig()
        return b


FM = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)


def frontmatter(text):
    m = FM.match(text)
    if not m:
        return {}
    body = m.group(1)
    out = {}
    for key in ("name", "description", "version", "license", "allowed-tools"):
        km = re.search(r"^%s:[ \t]*(?:([|>]-?)[ \t]*\n((?:[ \t]+.*\n?)+)|(.*))$" % re.escape(key),
                       body, re.M)
        if not km:
            continue
        val = km.group(2) if km.group(1) else (km.group(3) or "")
        val = " ".join(val.split()).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def harvest(repo, branches=("main", "master")):
    found, err = [], None
    for br in branches:
        url = "https://codeload.github.com/%s/tar.gz/refs/heads/%s" % (repo, br)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as resp:
                stream = tarfile.open(fileobj=Capped(resp), mode="r|gz")
                for member in stream:
                    if not member.isfile():
                        continue
                    p = member.name
                    if not p.endswith("/SKILL.md"):
                        continue
                    if "/node_modules/" in p or "/.git/" in p:
                        continue
                    try:
                        data = stream.extractfile(member).read(60000).decode("utf-8", "replace")
                    except Exception:
                        continue
                    rel = p.split("/", 1)[1] if "/" in p else p
                    fm = frontmatter(data)
                    found.append({
                        "repo": repo,
                        "path": rel,
                        "dir": rel[: -len("/SKILL.md")] if rel.endswith("/SKILL.md") else rel,
                        "slug": rel.split("/")[-2] if "/" in rel else "",
                        "fm_name": fm.get("name", ""),
                        "description": fm.get("description", "")[:900],
                        "license": fm.get("license", ""),
                        "allowed_tools": fm.get("allowed-tools", ""),
                        "body_chars": len(data),
                    })
            return found, None
        except TooBig:
            return found, "too_big"
        except urllib.error.HTTPError as e:
            err = "http_%s" % e.code
            if e.code == 404:
                continue          # wrong branch name, try the next one
            return found, err
        except Exception as e:
            err = type(e).__name__
            continue
    return found, err


def main():
    candidates, meta = {}, {}

    tp = os.path.join(OUT, "repos_topic.json")
    if os.path.exists(tp):
        with open(tp, encoding="utf-8") as f:
            d = json.load(f)
        for r in d["repos"]:
            candidates[r["full_name"]] = r
            meta[r["full_name"]] = r

    sp = os.path.join(OUT, "skills_raw.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            d = json.load(f)
        for s in d["skills"]:
            if s.get("repo_full"):
                candidates.setdefault(s["repo_full"], {"full_name": s["repo_full"],
                                                       "from_curated_list": True})

    todo = []
    skipped_big = 0
    for name, r in candidates.items():
        if r.get("fork") or r.get("archived"):
            continue
        if (r.get("size") or 0) > MAX_REPO_KB:
            skipped_big += 1
            continue
        todo.append(name)

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if limit:
        todo.sort(key=lambda n: -(candidates[n].get("stargazers_count") or 10 ** 9))
        todo = todo[:limit]

    # resume: a long fetch can be killed, so skip repos already accounted for
    skills, errors, visited = [], {}, set()
    outp = os.path.join(OUT, "skills_deep.json")
    if os.path.exists(outp):
        with open(outp, encoding="utf-8") as f:
            prev = json.load(f)
        skills = prev.get("skills", [])
        errors = prev.get("errors", {})
        visited = set(prev.get("visited", [])) | {s["repo"] for s in skills} | set(errors)
        print("resumed: %d repos visited, %d skills" % (len(visited), len(skills)),
              file=sys.stderr, flush=True)

    todo = [n for n in todo if n not in visited]
    print("candidates=%d  to_fetch=%d  skipped_oversize=%d"
          % (len(candidates), len(todo), skipped_big), file=sys.stderr, flush=True)

    def save():
        tmp = outp + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"n_skills": len(skills), "errors": errors,
                       "visited": sorted(visited), "skills": skills}, f, ensure_ascii=False)
        os.replace(tmp, outp)

    def work(name):
        f, e = harvest(name)
        with lock:
            done[0] += 1
            visited.add(name)
            if e:
                errors[name] = e
            skills.extend(f)
            if done[0] % 25 == 0:
                print("  %d/%d  skills=%d" % (done[0], len(todo), len(skills)),
                      file=sys.stderr, flush=True)
            if done[0] % 250 == 0:
                save()
        return name

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(work, n) for n in todo]
        for _ in as_completed(futs):
            pass

    by_repo = {}
    for s in skills:
        by_repo.setdefault(s["repo"], []).append(s)
    for s in skills:
        m = meta.get(s["repo"], {})
        s["repo_stars"] = m.get("stargazers_count")
        s["repo_pushed_at"] = m.get("pushed_at")
        s["repo_created_at"] = m.get("created_at")
        s["repo_topics"] = m.get("topics", [])
        s["repo_description"] = m.get("description")
        s["skills_in_repo"] = len(by_repo[s["repo"]])

    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"n_repos_visited": len(visited), "n_repos_with_skills": len(by_repo),
                   "n_skills": len(skills), "errors": errors,
                   "visited": sorted(visited), "skills": skills}, f, ensure_ascii=False)

    print("\nDONE  visited=%d  repos_with_skills=%d  skills=%d  errors=%d"
          % (len(visited), len(by_repo), len(skills), len(errors)), file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
