# Claude Skills 생태계 공백 분석

## 1. 데이터셋

| 항목 | 값 |
|---|---|
| 검색으로 발견한 repo | 8,419 |
| 수집한 SKILL.md 원본 | 233,455 |
| 자동생성 계열 병합 (2507개 계열) | −31,046 |
| repo 간 복제본 병합 | −39,958 |
| 미작성 템플릿 제외 | −4,060 |
| **분석 대상 고유 스킬** | **155,219** |
| 미분류 | 51,245 |
| 수집한 수요 이슈 | 8,555 |
| — 유지보수성 이슈 제외 | −4,979 |
| — 카테고리 미분류 제외 | −495 |
| — repo당 10건 상한 초과 제외 | −79 |
| **수요로 집계된 요청** | **3,002** |

공급은 `repo당 25개` 상한을 적용했습니다. repo 20개가 전체 파일의 62%를 차지하고 
한 곳은 조문당 1개씩 23,793개를 자동생성했기 때문에, 상한 없이는 대량 생산이 공급 밀도를 왜곡합니다.
공급의 1차 지표는 **독립 저자 수**입니다.

## 2. 카테고리별 공급·수요·품질

| 카테고리 | 저자 | 요청 | 대량생산% | 중앙깊이 | 최다repo | 품질공백 |
|---|---:|---:|---:|---:|---:|---:|
| Finance, Legal & Compliance Ops ⚠ | 457 | 47 | 94% | 4,301 | 66% | **5.80** |
| Meta: Skill & Prompt Authoring ✱ | 244 | 450 | 49% | 6,899 | 8% | **4.19** |
| Productivity & Personal Ops ⚠ | 451 | 43 | 78% | 5,935 | 51% | **2.16** |
| Terminal & Developer Environment | 299 | 72 | 66% | 5,936 | 16% | **1.50** |
| Communication & Messaging | 491 | 65 | 68% | 5,858 | 11% | **1.42** |
| Memory & Context Engineering | 643 | 100 | 67% | 5,965 | 24% | **1.26** |
| Documentation | 634 | 139 | 59% | 5,846 | 10% | **0.82** |
| Code Quality & Refactoring | 575 | 43 | 59% | 5,784 | 8% | **0.46** |
| Education & Learning | 268 | 46 | 59% | 6,073 | 8% | **0.39** |
| Observability & Monitoring | 772 | 114 | 69% | 6,789 | 10% | **0.34** |
| SaaS App Automation | 155 | 4 | 82% | 7,499 | 10% | **0.32** |
| Healthcare & Bio | 87 | 3 | 82% | 7,645 | 14% | **0.15** |
| API & Integration | 579 | 80 | 73% | 7,216 | 21% | **0.15** |
| Writing & Content | 878 | 91 | 57% | 6,001 | 14% | **0.10** |
| Engineering Process & Discipline | 671 | 120 | 62% | 6,516 | 8% | **0.10** |
| Product & Strategy | 892 | 211 | 58% | 6,441 | 9% | **0.09** |
| Data & Analytics | 546 | 41 | 73% | 7,140 | 10% | **0.05** |
| Collaboration & Code Review | 840 | 226 | 44% | 5,497 | 5% | **0.04** |
| Research & Science | 981 | 124 | 63% | 6,671 | 17% | **-0.12** |
| DevOps & Infrastructure | 821 | 193 | 72% | 7,660 | 6% | **-0.18** |
| Document & File Processing | 992 | 87 | 53% | 6,082 | 6% | **-0.45** |
| Database & SQL | 517 | 64 | 72% | 7,628 | 6% | **-0.46** |
| Security & Compliance | 938 | 125 | 70% | 7,501 | 7% | **-0.49** |
| UX Research & Audit | 158 | 9 | 60% | 6,578 | 5% | **-0.52** |
| Marketing, Sales & SEO | 936 | 112 | 61% | 7,008 | 5% | **-0.78** |
| Debugging & Troubleshooting | 824 | 86 | 61% | 7,018 | 8% | **-0.89** |
| Testing & QA | 780 | 122 | 60% | 7,165 | 5% | **-0.99** |
| Web & Browser Automation | 420 | 30 | 60% | 6,969 | 7% | **-1.00** |
| AI & LLM Tooling | 810 | 134 | 68% | 7,906 | 23% | **-1.07** |
| Evaluation & Benchmarking | 529 | 101 | 60% | 7,420 | 10% | **-1.14** |
| Agent & Workflow Orchestration | 643 | 111 | 52% | 6,895 | 11% | **-1.33** |
| Accessibility & Assistive | 156 | 4 | 60% | 7,124 | 9% | **-1.36** |
| Frontend & UI Engineering | 954 | 117 | 55% | 7,046 | 8% | **-1.40** |
| Design & Creative Media | 1013 | 66 | 52% | 6,866 | 6% | **-1.69** |
| Mobile Development | 389 | 21 | 56% | 7,343 | 7% | **-1.95** |
| Game & Simulation | 168 | 17 | 47% | 8,027 | 8% | **-3.52** |

> `Meta: Skill & Prompt Authoring`은 순위에서 제외했습니다. 수요 이슈 검색어를 전부 `"skill"`로 짰기 때문에 스킬 제작·도구 관련 이슈가 구조적으로 과대 대표됩니다 — 발견이 아니라 수집 방식의 산물입니다.

GAP = 수요(z) + 희소성(z), 단 **희소성은 수요가 평균 이상일 때만 가산**합니다. 수요를 빼고 희소성만 보면 "아무도 원하지 않아서 비어 있는" 영역이 상위로 올라옵니다 — 수정 전에는 스킬당 관심이 3.0에 불과한 Healthcare & Bio가 3위였습니다.

## 3. 상위 공백 후보

### Terminal & Developer Environment  (품질공백 1.50)

- 공급: 독립 저자 **299명**, repo 303개, 고유 스킬 611개 — 최다 repo 비중 16% (단일 repo 편중 아님)
- 품질: 공급의 **66%가 스킬 100개 이상 찍어내는 repo 출신**, SKILL.md 중앙 길이 5,936자 (전체 중앙 6,500자)
- 수요: 명시적 요청 72건, 100★ 이상 repo 131개 (43%)
- 최신성: 최근 갱신 비율 92%
- 대량생산 출처(상한 적용): majiayu000/claude-skill-registry-data (124), NeverSight/learn-skills.dev (70), mvanhorn/printing-press-library (34)
- 기존 사례: Jeffallan/claude-skills/cli-developer (11057*), alirezarezvani/claude-skills/monorepo-navigator (24603*), zebbern/claude-code-guide/dev-guide-generator (4578*), zebbern/claude-code-guide/linux-shell-scripting (4578*)
- 요청 사례:
  - M0rtalPhe0nix/dotfiles — Add static validation for Claude skills and AI artifacts
  - teng-lin/notebooklm-py — Support for sandboxed agent environments (Claude Cowork): docs + skill packaging
  - anthropics/claude-code — [Feature Request] Add support for organization skills in Claude CLI

### Communication & Messaging  (품질공백 1.42)

- 공급: 독립 저자 **491명**, repo 512개, 고유 스킬 1718개 — 최다 repo 비중 11% (단일 repo 편중 아님)
- 품질: 공급의 **68%가 스킬 100개 이상 찍어내는 repo 출신**, SKILL.md 중앙 길이 5,858자 (전체 중앙 6,500자)
- 수요: 명시적 요청 65건, 100★ 이상 repo 203개 (40%)
- 최신성: 최근 갱신 비율 86%
- 대량생산 출처(상한 적용): majiayu000/claude-skill-registry-data (230), NeverSight/learn-skills.dev (81), LeoYeAI/openclaw-master-skills (64)
- 기존 사례: nanocoai/nanoclaw/add-deltachat (30539*), nanocoai/nanoclaw/add-discord (30539*), nanocoai/nanoclaw/add-resend (30539*), nanocoai/nanoclaw/add-slack (30539*)
- 요청 사례:
  - Ivy-Interactive/Ivy-Tendril — Create skills or similar for installing tendril knowledge in claude code etc. 
  - Falcoraxyz/genesis-architect — Credit request for genesis-architect Claude skill
  - omriariav/amq-squad — 1.0.0: New skill amq-team-setup for organized team bootstrapping (Claude + Codex)

### Memory & Context Engineering  (품질공백 1.26)

- 공급: 독립 저자 **643명**, repo 658개, 고유 스킬 1857개 — 최다 repo 비중 24% (단일 repo 편중 아님)
- 품질: 공급의 **67%가 스킬 100개 이상 찍어내는 repo 출신**, SKILL.md 중앙 길이 5,965자 (전체 중앙 6,500자)
- 수요: 명시적 요청 100건, 100★ 이상 repo 247개 (38%)
- 최신성: 최근 갱신 비율 89%
- 대량생산 출처(상한 적용): majiayu000/claude-skill-registry-data (649), NeverSight/learn-skills.dev (90), ndpvt-web/arxiv-claude-skills (76)
- 기존 사례: Jeffallan/claude-skills/cpp-pro (11057*), Jeffallan/claude-skills/rag-architect (11057*), Jeffallan/claude-skills/rust-engineer (11057*), nanocoai/nanoclaw/add-mnemon (30539*)
- 요청 사례:
  - MosslandOpenDevs/agentic-orchestrator — [Idea] Claude Code Skill-Driven Protocol Docs Generator for Mossland Web3 Engineers
  - MosslandOpenDevs/agentic-orchestrator — [Idea] Claude Code Skill Delta Firewall for Regulated Engineering Teams and Audit-Ready Te
  - MosslandOpenDevs/agentic-orchestrator — [Idea] Claude Code Skill Mesh for Protocol Learning, Auto-Generated by DeepSeek Harness an

### Documentation  (품질공백 0.82)

- 공급: 독립 저자 **634명**, repo 653개, 고유 스킬 1501개 — 최다 repo 비중 10% (단일 repo 편중 아님)
- 품질: 공급의 **59%가 스킬 100개 이상 찍어내는 repo 출신**, SKILL.md 중앙 길이 5,846자 (전체 중앙 6,500자)
- 수요: 명시적 요청 139건, 100★ 이상 repo 237개 (36%)
- 최신성: 최근 갱신 비율 85%
- 대량생산 출처(상한 적용): majiayu000/claude-skill-registry-data (181), NeverSight/learn-skills.dev (97), lionelsimai/claude-skills-collection (46)
- 기존 사례: Jeffallan/claude-skills/architecture-designer (11057*), Jeffallan/claude-skills/atlassian-mcp (11057*), Jeffallan/claude-skills/spec-miner (11057*), alirezarezvani/claude-skills/knowledge-ops (24603*)
- 요청 사례:
  - MosslandOpenDevs/agentic-orchestrator — [Idea] Claude Code Skill–Powered Web3 Protocol Atlas for Mossland Developer Onboarding and
  - jmccrae/ewe — Add a Claude Code Skill for wordnet editing workflow
  - nosportugal/backstage-plugin-dev-ai-hub — [2.8a] Add skill and hook launchers for Claude Code and Cursor

### Code Quality & Refactoring  (품질공백 0.46)

- 공급: 독립 저자 **575명**, repo 583개, 고유 스킬 1427개 — 최다 repo 비중 8% (단일 repo 편중 아님)
- 품질: 공급의 **59%가 스킬 100개 이상 찍어내는 repo 출신**, SKILL.md 중앙 길이 5,784자 (전체 중앙 6,500자)
- 수요: 명시적 요청 43건, 100★ 이상 repo 223개 (38%)
- 최신성: 최근 갱신 비율 87%
- 대량생산 출처(상한 적용): NeverSight/learn-skills.dev (142), ECNU-ICALK/AutoSkill (113), majiayu000/claude-skill-registry-data (85)
- 기존 사례: Jeffallan/claude-skills/typescript-pro (11057*), nanocoai/nanoclaw/migrate-nanoclaw (30539*), alirezarezvani/claude-skills/tech-debt-tracker (24603*), zebbern/claude-code-guide/deep-module-refactor (4578*)
- 요청 사례:
  - NodeJSmith/Claudefiles — Add pre-commit lint for hardcoded ~/.claude path references in skill and agent files
  - fullsend-ai/fullsend — Add CI check for skill directory sync across skills/, .claude/skills/, .cursor/skills/
  - kolohelios/kolohelios — feat: add Claude Code skill for completing work

## 4. 한계

- **수요 이슈는 쿼리당 1,000건 상한**에 걸렸습니다(11개 쿼리 모두 상한 도달). 절대 수요량은 과소 추정이지만, 상한이 모든 카테고리에 동일하게 걸리므로 카테고리 간 상대 비교는 유지됩니다.
- 요청/유지보수 분류기는 표본 검증에서 정밀도는 높았으나(10건 중 9건 정답) **약 20%의 진짜 요청을 놓칩니다**. 카테고리 편향은 관찰되지 않았습니다.
- 분류는 정규식 기반이라 **미분류가 33%** 남아 있습니다. 대부분 비영어권 법률·의료 대량생산물입니다.
- repo 155개는 40MB 스트리밍 상한에 걸려 일부만 수집됐습니다.
- 별점 기반 수요는 **카테고리 변별력이 없었습니다** — 100★ 이상 repo 비율이 모든 카테고리에서 31~49%로 평평합니다. 별점은 카테고리 수요가 아니라 repo 개별 요인(홍보·시점·번들링)을 반영합니다. 그래서 최종 순위에서 제외했습니다.
- 명시적 요청 3,292건 중 **91%는 이미 공급에 대응물이 있습니다**(`data/request_gaps.json`). 즉 '비어 있는 카테고리'는 사실상 없고, 승부처는 커버리지가 아니라 품질입니다.
