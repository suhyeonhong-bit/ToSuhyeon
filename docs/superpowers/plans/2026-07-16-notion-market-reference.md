# Notion Market Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate `참고자료.md` with a clear explanation of the Notion-based market monitoring database and its eight data areas.

**Architecture:** The Markdown file starts with a link placeholder because no URL was supplied. A short scope statement separates this market-analysis reference from the steel onboarding mission, then eight consistently formatted subsections list representative indicators and their use in interpretation.

**Tech Stack:** Markdown and text-search commands.

## Global Constraints

- Keep `노션 링크: 추후 추가` until an actual Notion URL is supplied.
- Preserve all eight supplied data areas and their meaning.
- Record that the visible company-earnings and news-schedule views currently contain no rows.
- Do not imply that this is a required source for the first ECOS/FRED exercise.

---

### Task 1: Populate the Notion market reference

**Files:**
- Modify: `참고자료.md`

**Interfaces:**
- Consumes: the user's eight database-area descriptions.
- Produces: a standalone Markdown reference explaining the Notion data layers and how they are used together.

- [ ] **Step 1: Write the title, scope, link placeholder, and eight data sections**

Use `apply_patch` to replace the currently empty `참고자료.md` with a document headed `# 참고자료`, followed by `## 노션 기반 시장 모니터링 데이터베이스`. Include sections numbered 1 through 8 for Fed·거시경제 지표, 유동성 지표, 시장 심리 데이터, 원자재 가격, 기업 실적, 뉴스·일정, 시장 가격 데이터, and 통합 인사이트. Each section must list the supplied indicators and its intended use.

- [ ] **Step 2: Verify section count and required state notes**

Run:

```bash
rg -n '^### [1-8]\. ' 참고자료.md
rg -n '노션 링크: 추후 추가|아직 입력된 행은 없습니다|현재 화면에서는 비어 있습니다|통합 인사이트' 참고자료.md
```

Expected: eight numbered subsections and all four required notes are present.
