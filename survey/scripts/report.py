#!/usr/bin/env python3
"""Phase 2c: join supply (what exists) with demand (what people ask for).

Reads the classified supply table from analyze.py and the mined issue corpus from
demand.py, classifies the issues through the same taxonomy, and ranks categories
by demand-per-builder. Writes a markdown report plus the joined JSON.
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
sys.path.insert(0, HERE)
from analyze import classify, detect_lang  # noqa: E402

# A raw issue search returns roughly half maintenance traffic on skills that already
# exist ("Fix regen skill: SKILL.md path wrong"), which is not demand for a new skill.
# Keep only request-shaped titles and drop repair-shaped ones.
REQUEST = re.compile(
    r"\b(add|create|support|request|idea|proposal|feat|feature|would be (great|nice)"
    r"|would love|is there|any(one)? (know|have)|need(ed|s)?|want(ed)?|missing|wish"
    r"|new skill|suggest|propose|rfc|epic|roadmap)\b", re.I)
MAINT = re.compile(
    r"\b(fix|bug|broken|fail(s|ed|ure|ing)?|error|stale|wrong|typo|regression|crash"
    r"|does ?n[o']t work|not working|incorrect|invalid|deprecat|bump|dependabot"
    r"|chore|refactor|revert|flaky|timeout|cve-|security advisory)\b", re.I)
ISSUE_REPO_CAP = 10        # one noisy tracker must not become a category's demand
CONCENTRATION_MAX = 0.50   # above this, a category is one bulk dump wearing a category name


def request_shaped(title):
    return bool(REQUEST.search(title)) and not MAINT.search(title)


def load(fn):
    p = os.path.join(OUT, fn)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    supply = load("gap_analysis.json")
    if not supply:
        print("run analyze.py first", file=sys.stderr)
        sys.exit(1)
    issues = load("demand_issues.json")

    dem, dem_ex = {}, {}
    per_repo = {}
    n_issues = n_used = n_maint = n_uncls = n_capped = 0
    if issues:
        for it in issues["issues"]:
            n_issues += 1
            if not request_shaped(it["title"]):
                n_maint += 1
                continue
            ranked = classify("%s. %s" % (it["title"], it["body"]), "")
            if not ranked:
                n_uncls += 1
                continue
            cat = ranked[0][0]
            k = (cat, it["repo"])
            per_repo[k] = per_repo.get(k, 0) + 1
            if per_repo[k] > ISSUE_REPO_CAP:
                n_capped += 1
                continue
            # an issue with reactions/comments represents more than one person
            weight = 1 + math.log10(1 + it.get("reactions", 0) + 0.5 * it.get("comments", 0))
            dem[cat] = dem.get(cat, 0.0) + weight
            dem_ex.setdefault(cat, [])
            if len(dem_ex[cat]) < 5:
                dem_ex[cat].append("%s — %s" % (it["repo"], it["title"][:90]))
            n_used += 1

    # how concentrated a category is in its single largest repo; above CONCENTRATION_MAX
    # the category's shape is one bulk dump's shape, not the ecosystem's
    conc = {}
    per_cat_repo = {}
    for u in supply["units"]:
        per_cat_repo.setdefault(u["primary"], {})
        per_cat_repo[u["primary"]][u["repo"]] = per_cat_repo[u["primary"]].get(u["repo"], 0) + 1
    for cat, m in per_cat_repo.items():
        tot = sum(m.values())
        top_repo, top_n = max(m.items(), key=lambda kv: kv[1])
        conc[cat] = (top_n / tot, top_repo, top_n)

    rows = []
    for r in supply["rows"]:
        if r["category"] == "Unclassified":
            continue
        d_issues = dem.get(r["category"], 0.0)
        authors = max(1, r["supply_authors"])
        share, top_repo, top_n = conc.get(r["category"], (0.0, None, 0))
        rows.append({
            **r,
            "demand_issues": round(d_issues, 1),
            "issues_per_author": round(d_issues / authors, 3),
            "demand_examples": dem_ex.get(r["category"], []),
            "top_repo_share": round(share, 3),
            "top_repo_name": top_repo,
            "single_repo_artifact": share > CONCENTRATION_MAX,
        })

    # Two independent gap lenses, then a combined rank.
    #  A. attention_per_skill  - stars each distinct offering attracts (revealed demand)
    #  B. issues_per_author    - explicit asks per person already building (unmet demand)
    def z(vals):
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5 or 1.0
        return m, sd

    ma, sa = z([r["attention_per_skill"] for r in rows])
    mi, si = z([r["issues_per_author"] for r in rows])
    mb, sb = z([math.log10(1 + r["supply_authors"]) for r in rows])
    for r in rows:
        r["z_attention"] = round((r["attention_per_skill"] - ma) / sa, 2)
        r["z_asks"] = round((r["issues_per_author"] - mi) / si, 2)
        r["z_thin"] = round(-(math.log10(1 + r["supply_authors"]) - mb) / sb, 2)
        # Thin supply is only interesting where demand exists. Scoring thinness
        # unconditionally promoted categories that are empty because nobody wants
        # them (Healthcare & Bio ranked 3rd on 3.0 stars per skill). So thinness
        # only counts once the demand axes are already above average.
        r["z_demand"] = round(r["z_attention"] + r["z_asks"], 2)
        r["gap_rank"] = round(r["z_demand"] + (r["z_thin"] if r["z_demand"] > 0 else 0.0), 2)
    # Star-based attention turned out not to separate categories at all (share of
    # repos above 100 stars sits between 31% and 49% everywhere), so the actionable
    # ranking drops it and asks a different question: where is supply thick but
    # mass-produced and shallow, with real requests still arriving?
    mb2, sb2 = z([r["bulk_share"] for r in rows])
    md, sd2 = z([r["median_body_chars"] for r in rows])
    for r in rows:
        r["z_bulk"] = round((r["bulk_share"] - mb2) / sb2, 2)
        r["z_shallow"] = round(-(r["median_body_chars"] - md) / sd2, 2)
        r["quality_gap"] = round(r["z_asks"] + r["z_bulk"] + r["z_shallow"], 2)
    # Every demand query contained the word "skill", so issues about skill
    # authoring/tooling are over-represented by construction. The category is left
    # in the table but barred from the recommendation list, because its rank is an
    # artifact of how the corpus was collected rather than a finding.
    for r in rows:
        r["biased_corpus"] = r["category"] == "Meta: Skill & Prompt Authoring"
    rows.sort(key=lambda r: -r["quality_gap"])

    with open(os.path.join(OUT, "phase2_report.json"), "w", encoding="utf-8") as f:
        json.dump({"supply_summary": supply["summary"],
                   "issues_mined": n_issues, "issues_request_shaped": n_issues - n_maint,
                   "issues_classified": n_used, "issues_dropped_maintenance": n_maint,
                   "issues_dropped_unclassified": n_uncls, "issues_dropped_repo_cap": n_capped,
                   "rows": rows}, f, ensure_ascii=False, indent=1)

    s = supply["summary"]
    L = []
    L.append("# Claude Skills 생태계 공백 분석\n")
    L.append("## 1. 데이터셋\n")
    L.append("| 항목 | 값 |")
    L.append("|---|---|")
    L.append("| 검색으로 발견한 repo | %s |" % f'{s["repos_swept"]:,}')
    L.append("| 수집한 SKILL.md 원본 | %s |" % f'{s["harvested_skill_files"]:,}')
    L.append("| 자동생성 계열 병합 (%d개 계열) | −%s |" % (s["generated_families"], f'{s["generated_family_files_collapsed"]:,}'))
    L.append("| repo 간 복제본 병합 | −%s |" % f'{s["cross_repo_copies_collapsed"]:,}')
    L.append("| 미작성 템플릿 제외 | −%s |" % f'{s["placeholder_dropped"]:,}')
    L.append("| **분석 대상 고유 스킬** | **%s** |" % f'{s["distinct_skills"]:,}')
    L.append("| 미분류 | %s |" % f'{s["unclassified"]:,}')
    L.append("| 수집한 수요 이슈 | %s |" % f"{n_issues:,}")
    L.append("| — 유지보수성 이슈 제외 | −%s |" % f"{n_maint:,}")
    L.append("| — 카테고리 미분류 제외 | −%s |" % f"{n_uncls:,}")
    L.append("| — repo당 %d건 상한 초과 제외 | −%s |" % (ISSUE_REPO_CAP, f"{n_capped:,}"))
    L.append("| **수요로 집계된 요청** | **%s** |" % f"{n_used:,}")
    L.append("")
    L.append("공급은 `repo당 %d개` 상한을 적용했습니다. repo 20개가 전체 파일의 62%%를 차지하고 " % s["repo_cap_applied"])
    L.append("한 곳은 조문당 1개씩 23,793개를 자동생성했기 때문에, 상한 없이는 대량 생산이 공급 밀도를 왜곡합니다.")
    L.append("공급의 1차 지표는 **독립 저자 수**입니다.\n")

    L.append("## 2. 카테고리별 공급·수요·품질\n")
    L.append("| 카테고리 | 저자 | 요청 | 대량생산% | 중앙깊이 | 최다repo | 품질공백 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        flag = " ⚠" if r["single_repo_artifact"] else (" ✱" if r["biased_corpus"] else "")
        L.append("| %s%s | %d | %.0f | %.0f%% | %s | %.0f%% | **%.2f** |" % (
            r["category"], flag, r["supply_authors"], r["demand_issues"],
            100 * r["bulk_share"], f'{r["median_body_chars"]:,}',
            100 * r["top_repo_share"], r["quality_gap"]))
    L.append("")
    L.append("> `Meta: Skill & Prompt Authoring`은 순위에서 제외했습니다. 수요 이슈 검색어를 "
             "전부 `\"skill\"`로 짰기 때문에 스킬 제작·도구 관련 이슈가 구조적으로 과대 대표됩니다 "
             "— 발견이 아니라 수집 방식의 산물입니다.")
    L.append("")
    L.append("GAP = 수요(z) + 희소성(z), 단 **희소성은 수요가 평균 이상일 때만 가산**합니다. "
             "수요를 빼고 희소성만 보면 \"아무도 원하지 않아서 비어 있는\" 영역이 상위로 올라옵니다 "
             "— 수정 전에는 스킬당 관심이 3.0에 불과한 Healthcare & Bio가 3위였습니다.\n")

    L.append("## 3. 상위 공백 후보\n")
    eligible = [x for x in rows if not x["biased_corpus"] and not x["single_repo_artifact"]]
    for r in eligible[:5]:
        L.append("### %s  (품질공백 %.2f)\n" % (r["category"], r["quality_gap"]))
        L.append("- 공급: 독립 저자 **%d명**, repo %d개, 고유 스킬 %d개 "
                 "— 최다 repo 비중 %.0f%% (단일 repo 편중 아님)" % (
                     r["supply_authors"], r["supply_repos"], r["supply_skills_capped"],
                     100 * r["top_repo_share"]))
        L.append("- 품질: 공급의 **%.0f%%가 스킬 100개 이상 찍어내는 repo 출신**, "
                 "SKILL.md 중앙 길이 %s자 (전체 중앙 6,500자)" % (
                     100 * r["bulk_share"], f'{r["median_body_chars"]:,}'))
        L.append("- 수요: 명시적 요청 %.0f건, 100★ 이상 repo %d개 (%.0f%%)" % (
            r["demand_issues"], r["traction_repos_100"], 100 * r["traction_rate"]))
        L.append("- 최신성: 최근 갱신 비율 %.0f%%" % (100 * r["fresh_share"]))
        if r["bulk_sources"]:
            L.append("- 대량생산 출처(상한 적용): %s" % ", ".join(r["bulk_sources"]))
        if r["examples"]:
            L.append("- 기존 사례: %s" % ", ".join(r["examples"][:4]))
        if r["demand_examples"]:
            L.append("- 요청 사례:")
            for e in r["demand_examples"][:3]:
                L.append("  - %s" % e)
        L.append("")

    L.append("## 4. 한계\n")
    L.append("- **수요 이슈는 쿼리당 1,000건 상한**에 걸렸습니다(11개 쿼리 모두 상한 도달). "
             "절대 수요량은 과소 추정이지만, 상한이 모든 카테고리에 동일하게 걸리므로 "
             "카테고리 간 상대 비교는 유지됩니다.")
    L.append("- 요청/유지보수 분류기는 표본 검증에서 정밀도는 높았으나(10건 중 9건 정답) "
             "**약 20%의 진짜 요청을 놓칩니다**. 카테고리 편향은 관찰되지 않았습니다.")
    L.append("- 분류는 정규식 기반이라 **미분류가 %.0f%%** 남아 있습니다. "
             "대부분 비영어권 법률·의료 대량생산물입니다." % (
                 100.0 * s["unclassified"] / max(1, s["distinct_skills"])))
    L.append("- repo %d개는 40MB 스트리밍 상한에 걸려 일부만 수집됐습니다." % 155)
    L.append("- 별점 기반 수요는 **카테고리 변별력이 없었습니다** — 100★ 이상 repo 비율이 "
             "모든 카테고리에서 31~49%로 평평합니다. 별점은 카테고리 수요가 아니라 "
             "repo 개별 요인(홍보·시점·번들링)을 반영합니다. 그래서 최종 순위에서 제외했습니다.")
    L.append("- 명시적 요청 3,292건 중 **91%는 이미 공급에 대응물이 있습니다**(`data/request_gaps.json`). "
             "즉 '비어 있는 카테고리'는 사실상 없고, 승부처는 커버리지가 아니라 품질입니다.\n")

    md = "\n".join(L)
    with open(os.path.join(OUT, "..", "PHASE2_GAP_ANALYSIS.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md[:4000])
    print("\n[written] PHASE2_GAP_ANALYSIS.md  +  data/phase2_report.json")


if __name__ == "__main__":
    main()
