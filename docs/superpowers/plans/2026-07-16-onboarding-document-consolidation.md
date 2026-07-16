# Onboarding Document Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the onboarding purpose and reference material into one clearly structured `goal.md`, then remove `과제.md`.

**Architecture:** `goal.md` becomes the only project document for the internship onboarding. It uses four top-level sections: purpose/background, industry-reference material, the concrete project assignment, and a final restatement of the CLI/AI learning objective. No software code or data artifacts are added.

**Tech Stack:** Markdown and repository text-search commands.

## Global Constraints

- Use exactly four top-level sections, in the user-specified order.
- Treat all industry connections as hypotheses to validate, not established answers.
- Retain API key issuance, raw-data preservation, monthly processing, missing-data/time-lag notes, and numerical verification requirements.
- Remove `과제.md` after its relevant content is merged.
- Do not change code, configuration, or data files.

---

### Task 1: Rewrite the single onboarding document

**Files:**
- Modify: `goal.md`

**Interfaces:**
- Consumes: the purpose, mission, and assessment requirements currently in `goal.md`; the framework, hypotheses, source matrix, and expansion guidance currently in `과제.md`.
- Produces: a self-contained `goal.md` with the four requested top-level sections.

- [ ] **Step 1: Replace the current document with the four-section structure**

Use `apply_patch` to replace the complete contents of `goal.md`. The document must contain these exact top-level headings, in this order:

```markdown
# 인턴 온보딩: 데이터를 통해 낯선 산업을 파악하는 법

## 1. 목적과 배경
## 2. 산업 이해를 위해 내가 그나마 정리해본 참고 정보
## 3. 이번 프로젝트에서 실제로 할 일
## 4. 목적 다시 강조: CLI와 AI를 쓰면 데이터 수집은 일이 아니다
```

Under section 2, include the five-question framework, labelled steel hypotheses, data-source matrix, and the statement that unavailable paid data is an acceptable limitation when documented. Under section 3, include the ECOS/FRED mission, assessment criteria, and the Customs Service extension.

- [ ] **Step 2: Inspect the headings and required concepts**

Run:

```bash
rg -n '^## ' goal.md
rg -n 'ECOS|FRED|WPU1017|raw|결측치|시차|검증|관세청' goal.md
```

Expected: exactly four `##` headings in the specified order; the required collection, preservation, processing, and verification concepts appear in the document.

### Task 2: Remove the superseded source document and verify references

**Files:**
- Delete: `과제.md`

**Interfaces:**
- Consumes: the completed standalone `goal.md` from Task 1.
- Produces: a project root with no active dependency on a separate assignment document.

- [ ] **Step 1: Delete the superseded document**

Use `apply_patch` with a delete-file patch for `과제.md`.

- [ ] **Step 2: Verify that no remaining project document links to the removed file**

Run:

```bash
rg -n '과제\.md' . -g '!docs/superpowers/**' || true
rg --files
```

Expected: the first command emits no project-content results; the second no longer lists `과제.md`.

- [ ] **Step 3: Read the final document end-to-end**

Run:

```bash
sed -n '1,360p' goal.md
```

Expected: the document reads independently, starts with purpose/background, separates reference material from the active mission, and ends by emphasizing responsible AI/CLI-assisted data work.
