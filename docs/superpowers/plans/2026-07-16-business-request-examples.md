# Business Request Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bullet-list subsection of representative business data requests to `goal.md` without expanding the scope of the first API mission.

**Architecture:** The new subsection belongs in section 2 because it translates the existing industry hypotheses into examples of future business questions. It is placed after `철강에 적용해본 가설` and before `찾아볼 데이터 소스`; section 3 remains the narrowly scoped first mission.

**Tech Stack:** Markdown and text-search commands.

## Global Constraints

- Use the heading `### 실무에서 받을 수 있는 데이터 요청 예시`.
- Use a lead-in paragraph and ten bullet points, not a table.
- Include the five user-provided themes: United States interest rates, Korean interest rates, global shipbuilding orders, the internal-combustion-to-EV transition, and war-related demand.
- Add five inferred themes: infrastructure and construction, China, trade policy, exchange rates, and carbon regulation.
- Frame every example as data-and-hypothesis work; do not promise or state a causal forecast as fact.
- Do not alter section 3's first mission, requirements, or assessment criteria.

---

### Task 1: Add the practical request examples subsection

**Files:**
- Modify: `goal.md` after the paragraph ending with `기각 또는 보류하는 것이 올바른 결과입니다.`

**Interfaces:**
- Consumes: the existing industry framework and steel hypotheses in section 2.
- Produces: ten practical business-request examples that demonstrate why the framework and data-source matrix are useful.

- [ ] **Step 1: Insert the subsection between hypotheses and data sources**

Use `apply_patch` to insert this Markdown content directly before `### 찾아볼 데이터 소스`:

```markdown
### 실무에서 받을 수 있는 데이터 요청 예시

아래 질문은 답을 미리 정해두는 것이 아니라, 가설을 세우고 필요한 데이터를 찾아 검증하기 위한 실무형 요청의 예시입니다.

- 최근 미국 기준금리 인상·인하가 타깃 국가의 건설·자동차 투자와 철강 수요에 미칠 가능성을 검토할 데이터와 가설을 준비해줘.
- 국내 기준금리 인상·인하가 건설·설비투자·자동차 생산을 거쳐 국내 철강 수요에 미칠 가능성을 정리해줘.
- 전 세계 조선 수주와 수주잔량 추이를 확인하고, 선박용 후판 등 철강 수요와 연결해볼 자료를 준비해줘.
- 기존 내연기관차 산업이 전기차로 전환되면서 자동차용 강재의 총수요와 필요한 강종·규격이 어떻게 바뀔지 검토해줘.
- 전쟁 장기화, 국방비 지출, 전후 복구 수요가 어떤 산업과 철강 제품군의 수요를 견조하게 만들 수 있을지 가설과 데이터를 준비해줘.
- 타깃 국가의 정부 인프라 투자, 주택 착공, 도시개발 계획 변화가 철근·형강 등 건설용 철강 수요에 미칠 영향을 확인해줘.
- 중국의 부동산 투자, 조강 생산, 철강 수출 변화가 글로벌 철강 가격과 한국산 철강의 경쟁 환경에 미칠 영향을 검토해줘.
- 관세, 반덤핑 조치, 원산지 규정 변화가 타깃 국가에서 한국산 철강의 판매량과 가격경쟁력에 미칠 영향을 정리해줘.
- 원/달러 환율과 타깃 국가 통화의 변화가 수출 가격경쟁력 및 현지 구매자의 수입 수요에 미칠 가능성을 확인해줘.
- 탄소배출 규제와 고객사의 저탄소 소재 조달 요구가 철강 수요, 제품 사양, 수출 가능성에 미칠 영향을 준비해줘.
```

- [ ] **Step 2: Verify placement and content**

Run:

```bash
rg -n -A14 -B3 '^### 실무에서 받을 수 있는 데이터 요청 예시$' goal.md
rg -n '^### 철강에 적용해본 가설$|^### 실무에서 받을 수 있는 데이터 요청 예시$|^### 찾아볼 데이터 소스$' goal.md
```

Expected: the subsection has exactly ten list items and appears between the hypothesis and data-source subsections in section 2.
