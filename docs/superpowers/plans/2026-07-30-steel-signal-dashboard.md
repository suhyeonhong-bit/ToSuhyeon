# STEEL SIGNAL Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publicly deploy a one-page dashboard that reads the latest public `monthly_indicators.csv` from GitHub and presents current Korean base rate and U.S. steel PPI values, a five-year interactive trend chart, a full table, CSV download, sources, and beginner-friendly guidance.

**Architecture:** Keep the existing `ToSuhyeon` data collector unchanged and create a separate Sites/Vinext project at `/Users/suhyeonhong/Documents/GitHub/SteelSignal`. The browser fetches the public GitHub CSV at runtime, a pure parser validates it, a focused hook manages loading/success/error/retry state, and small React components render the dashboard. The deployed site has no database, authentication, API keys, or server-side data proxy.

**Tech Stack:** Node.js 22.13+, npm, Vinext, Next.js 16, React 19, TypeScript 5.9, Recharts, Vitest, Testing Library, CSS, OpenAI Sites hosting.

## Global Constraints

- Data source: `https://raw.githubusercontent.com/suhyeonhong-bit/ToSuhyeon/main/data/processed/monthly_indicators.csv`.
- Required CSV headers: `month,korea_base_rate_percent,us_steel_ppi_index`.
- Site name: `STEEL SIGNAL`.
- Primary copy: `금리와 철강 가격의 흐름을 한눈에`.
- Visual direction: warm ivory background, dark navy text, copper PPI accent, blue rate accent.
- Public access: anyone with the URL can view the dashboard without signing in.
- Latest cards use each metric's last non-missing value and show that metric's own month.
- Chart uses separate axes, monthly tooltip, keyboard-accessible controls, and independent series toggles.
- Table shows newest month first; missing values display `—`.
- Runtime failures show a plain-language message, retry button, and raw GitHub CSV link.
- API keys remain only in the existing local `.env` and GitHub Actions secrets.
- The site must not call FRED or ECOS directly and must not include analytics, cookies, accounts, persistence, predictions, or investment advice.
- Responsive behavior must support phone, tablet, and desktop layouts.
- Every implementation task follows red-green-refactor TDD and ends with a focused commit.
- Design specification: `/Users/suhyeonhong/Documents/GitHub/ToSuhyeon/docs/superpowers/specs/2026-07-30-steel-signal-dashboard-design.md`.

---

## Planned File Structure

```text
/Users/suhyeonhong/Documents/GitHub/SteelSignal/
├── .openai/
│   └── hosting.json
├── app/
│   ├── components/
│   │   ├── DashboardError.tsx
│   │   ├── DashboardLoading.tsx
│   │   ├── DataGuide.tsx
│   │   ├── DownloadCsvButton.tsx
│   │   ├── IndicatorTable.tsx
│   │   ├── MetricCard.tsx
│   │   ├── SteelSignalDashboard.tsx
│   │   └── TrendChart.tsx
│   ├── hooks/
│   │   └── useIndicatorData.ts
│   ├── lib/
│   │   ├── indicator-data.ts
│   │   └── indicator-download.ts
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── public/
│   └── og.png
├── tests/
│   ├── dashboard.test.tsx
│   ├── indicator-data.test.ts
│   ├── indicator-download.test.ts
│   ├── setup.ts
│   ├── trend-chart.test.tsx
│   ├── use-indicator-data.test.tsx
│   └── rendered-html.test.mjs
├── vitest.config.ts
├── package.json
└── package-lock.json
```

- `indicator-data.ts`: validates and transforms CSV without React or network dependencies.
- `useIndicatorData.ts`: owns fetch, loading, error classification, and retry.
- `indicator-download.ts`: describes the exact downloadable CSV file.
- `TrendChart.tsx`: owns chart-only state and visual interaction.
- `SteelSignalDashboard.tsx`: composes states and page sections without parsing CSV.
- Small display components remain independent and receive typed props.

---

### Task 1: Initialize the Site and Build the CSV Domain Module

**Files:**
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/` from the Sites Vinext starter
- Modify: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/package.json`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/vitest.config.ts`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/setup.ts`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/indicator-data.test.ts`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/lib/indicator-data.ts`

**Interfaces:**
- Consumes: public CSV text matching the three required headers.
- Produces:
  - `IndicatorRow`
  - `IndicatorMetricKey`
  - `LatestMetric`
  - `IndicatorDataError`
  - `parseIndicatorCsv(csvText: string): IndicatorRow[]`
  - `getLatestMetric(rows: IndicatorRow[], key: IndicatorMetricKey): LatestMetric`
  - `getLatestDataMonth(rows: IndicatorRow[]): string | null`
  - `formatMonth(month: string | null): string`
  - `formatRate(value: number | null): string`
  - `formatPpi(value: number | null): string`

- [ ] **Step 1: Initialize the new standalone Sites project**

Run from `/Users/suhyeonhong/Documents/GitHub`:

```bash
bash /Users/suhyeonhong/.codex/plugins/cache/openai-bundled/sites/0.1.30/scripts/init-site.sh \
  /Users/suhyeonhong/Documents/GitHub/SteelSignal
```

Expected:

- The directory is created once.
- `npm ci` finishes successfully.
- `.openai/hosting.json` exists with `d1` and `r2` set to `null`.
- The generated project has its own `main` branch.

- [ ] **Step 2: Start the retained development server and open the starter once**

Run:

```bash
npm run dev
```

Expected: the retained session prints one healthy local URL. Call `open_in_codex`
once with that exact URL. Keep this process alive through implementation and
build.

- [ ] **Step 3: Install the runtime and test dependencies**

Run:

```bash
npm install recharts
npm install --save-dev vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

Update `package.json` scripts to:

```json
{
  "scripts": {
    "dev": "WRANGLER_LOG_PATH=.wrangler/wrangler.log vinext dev",
    "build": "WRANGLER_LOG_PATH=.wrangler/wrangler.log vinext build",
    "start": "WRANGLER_LOG_PATH=.wrangler/wrangler.log vinext start",
    "test:unit": "vitest run",
    "test": "npm run test:unit && npm run build && node --test tests/rendered-html.test.mjs",
    "lint": "eslint . --ignore-pattern dist --ignore-pattern .next",
    "db:generate": "drizzle-kit generate"
  }
}
```

- [ ] **Step 4: Configure Vitest and the DOM test environment**

Create `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    clearMocks: true,
  },
});
```

Create `tests/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, "ResizeObserver", {
  writable: true,
  value: TestResizeObserver,
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {
      return false;
    },
  }),
});

Object.defineProperties(URL, {
  createObjectURL: {
    writable: true,
    value: () => "blob:test",
  },
  revokeObjectURL: {
    writable: true,
    value: () => undefined,
  },
});
```

- [ ] **Step 5: Write the failing CSV domain tests**

Create `tests/indicator-data.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  IndicatorDataError,
  formatMonth,
  formatPpi,
  formatRate,
  getLatestDataMonth,
  getLatestMetric,
  parseIndicatorCsv,
} from "../app/lib/indicator-data";

const VALID_CSV =
  "\uFEFFmonth,korea_base_rate_percent,us_steel_ppi_index\r\n" +
  "2026-04,2.5,341.281\r\n" +
  "2026-06,2.5,361.439\r\n" +
  "2026-05,,349.023\r\n";

describe("parseIndicatorCsv", () => {
  it("removes the BOM, parses numbers and sorts months ascending", () => {
    expect(parseIndicatorCsv(VALID_CSV)).toEqual([
      {
        month: "2026-04",
        koreaBaseRatePercent: 2.5,
        usSteelPpiIndex: 341.281,
      },
      {
        month: "2026-05",
        koreaBaseRatePercent: null,
        usSteelPpiIndex: 349.023,
      },
      {
        month: "2026-06",
        koreaBaseRatePercent: 2.5,
        usSteelPpiIndex: 361.439,
      },
    ]);
  });

  it.each([
    ["wrong headers", "month,rate,ppi\n2026-06,2.5,361.439"],
    ["invalid month", "month,korea_base_rate_percent,us_steel_ppi_index\n2026-13,2.5,361.439"],
    ["invalid number", "month,korea_base_rate_percent,us_steel_ppi_index\n2026-06,nope,361.439"],
    ["duplicate month", "month,korea_base_rate_percent,us_steel_ppi_index\n2026-06,2.5,361\n2026-06,2.5,362"],
    ["no rows", "month,korea_base_rate_percent,us_steel_ppi_index\n"],
  ])("rejects %s", (_label, csv) => {
    expect(() => parseIndicatorCsv(csv)).toThrow(IndicatorDataError);
  });
});

describe("metric helpers", () => {
  const rows = parseIndicatorCsv(VALID_CSV);

  it("finds each metric's last valid value independently", () => {
    expect(getLatestMetric(rows, "koreaBaseRatePercent")).toEqual({
      value: 2.5,
      month: "2026-06",
    });
    expect(getLatestMetric(rows, "usSteelPpiIndex")).toEqual({
      value: 361.439,
      month: "2026-06",
    });
  });

  it("uses the latest month containing any valid metric", () => {
    expect(getLatestDataMonth(rows)).toBe("2026-06");
  });

  it("formats Korean labels without inventing missing values", () => {
    expect(formatMonth("2026-06")).toBe("2026년 6월");
    expect(formatMonth(null)).toBe("기준월 없음");
    expect(formatRate(2.5)).toBe("2.50%");
    expect(formatRate(null)).toBe("—");
    expect(formatPpi(361.439)).toBe("361.439");
    expect(formatPpi(null)).toBe("—");
  });
});
```

- [ ] **Step 6: Run the domain tests and confirm red**

Run:

```bash
npx vitest run tests/indicator-data.test.ts
```

Expected: FAIL because `app/lib/indicator-data.ts` does not exist.

- [ ] **Step 7: Implement the pure CSV domain module**

Create `app/lib/indicator-data.ts`:

```ts
export type IndicatorRow = {
  month: string;
  koreaBaseRatePercent: number | null;
  usSteelPpiIndex: number | null;
};

export type IndicatorMetricKey =
  | "koreaBaseRatePercent"
  | "usSteelPpiIndex";

export type LatestMetric = {
  value: number | null;
  month: string | null;
};

const EXPECTED_HEADERS = [
  "month",
  "korea_base_rate_percent",
  "us_steel_ppi_index",
] as const;

export class IndicatorDataError extends Error {
  readonly kind = "format";

  constructor(message = "CSV format is invalid") {
    super(message);
    this.name = "IndicatorDataError";
  }
}

function parseMonth(value: string): string {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) {
    throw new IndicatorDataError();
  }
  return value;
}

function parseOptionalNumber(value: string): number | null {
  if (value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new IndicatorDataError();
  return parsed;
}

export function parseIndicatorCsv(csvText: string): IndicatorRow[] {
  const normalized = csvText.replace(/^\uFEFF/, "").trim();
  const [headerLine, ...lines] = normalized.split(/\r?\n/);
  if (!headerLine) throw new IndicatorDataError();

  const headers = headerLine.split(",");
  if (
    headers.length !== EXPECTED_HEADERS.length ||
    headers.some((header, index) => header !== EXPECTED_HEADERS[index])
  ) {
    throw new IndicatorDataError();
  }

  const seen = new Set<string>();
  const rows = lines
    .filter((line) => line.trim() !== "")
    .map((line) => {
      const cells = line.split(",");
      if (cells.length !== 3) throw new IndicatorDataError();

      const month = parseMonth(cells[0]);
      if (seen.has(month)) throw new IndicatorDataError();
      seen.add(month);

      return {
        month,
        koreaBaseRatePercent: parseOptionalNumber(cells[1]),
        usSteelPpiIndex: parseOptionalNumber(cells[2]),
      };
    })
    .sort((left, right) => left.month.localeCompare(right.month));

  if (rows.length === 0) throw new IndicatorDataError();
  return rows;
}

export function getLatestMetric(
  rows: IndicatorRow[],
  key: IndicatorMetricKey,
): LatestMetric {
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const value = rows[index][key];
    if (value !== null) return { value, month: rows[index].month };
  }
  return { value: null, month: null };
}

export function getLatestDataMonth(rows: IndicatorRow[]): string | null {
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    if (
      rows[index].koreaBaseRatePercent !== null ||
      rows[index].usSteelPpiIndex !== null
    ) {
      return rows[index].month;
    }
  }
  return null;
}

export function formatMonth(month: string | null): string {
  if (!month) return "기준월 없음";
  const [year, monthNumber] = month.split("-");
  return `${year}년 ${Number(monthNumber)}월`;
}

export function formatRate(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(2)}%`;
}

export function formatPpi(value: number | null): string {
  return value === null ? "—" : value.toFixed(3);
}
```

- [ ] **Step 8: Run the parser tests and confirm green**

Run:

```bash
npx vitest run tests/indicator-data.test.ts
```

Expected: all parser and metric helper tests PASS.

- [ ] **Step 9: Commit Task 1**

```bash
git add package.json package-lock.json vitest.config.ts tests/setup.ts \
  tests/indicator-data.test.ts app/lib/indicator-data.ts
git commit -m "feat: parse STEEL SIGNAL indicator data"
```

---

### Task 2: Add Runtime Loading, Retry, and CSV Download

**Files:**
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/use-indicator-data.test.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/indicator-download.test.ts`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/hooks/useIndicatorData.ts`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/lib/indicator-download.ts`

**Interfaces:**
- Consumes:
  - `parseIndicatorCsv(csvText: string): IndicatorRow[]`
  - `IndicatorDataError`
- Produces:
  - `INDICATOR_CSV_URL`
  - `IndicatorDataState`
  - `useIndicatorData(): IndicatorDataState & { retry(): Promise<void> }`
  - `buildCsvDownload(rawCsv: string): CsvDownload`

- [ ] **Step 1: Write the failing hook and download tests**

Create `tests/use-indicator-data.test.tsx`:

```tsx
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  INDICATOR_CSV_URL,
  useIndicatorData,
} from "../app/hooks/useIndicatorData";

const CSV =
  "month,korea_base_rate_percent,us_steel_ppi_index\n" +
  "2026-06,2.5,361.439\n";

function response(body: string): Response {
  return {
    ok: true,
    text: async () => body,
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useIndicatorData", () => {
  it("loads the public CSV without browser caching", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(CSV));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useIndicatorData());
    expect(result.current.status).toBe("loading");

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(fetchMock).toHaveBeenCalledWith(INDICATOR_CSV_URL, {
      cache: "no-store",
    });
    expect(result.current.rows).toHaveLength(1);
    expect(result.current.rawCsv).toBe(CSV);
  });

  it("classifies network failures and succeeds after retry", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(response(CSV));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useIndicatorData());
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorKind).toBe("network");

    await act(async () => {
      await result.current.retry();
    });
    expect(result.current.status).toBe("success");
  });

  it("classifies invalid CSV separately", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(response("wrong,csv")),
    );

    const { result } = renderHook(() => useIndicatorData());
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorKind).toBe("format");
  });
});
```

Create `tests/indicator-download.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildCsvDownload } from "../app/lib/indicator-download";

describe("buildCsvDownload", () => {
  it("keeps the exact fetched CSV with a stable file name", () => {
    const rawCsv = "month,korea_base_rate_percent,us_steel_ppi_index\n";
    expect(buildCsvDownload(rawCsv)).toEqual({
      fileName: "monthly_indicators.csv",
      mimeType: "text/csv;charset=utf-8",
      content: rawCsv,
    });
  });
});
```

- [ ] **Step 2: Run the new tests and confirm red**

Run:

```bash
npx vitest run tests/use-indicator-data.test.tsx tests/indicator-download.test.ts
```

Expected: FAIL because the hook and download modules do not exist.

- [ ] **Step 3: Implement the runtime data hook**

Create `app/hooks/useIndicatorData.ts`:

```ts
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  IndicatorDataError,
  type IndicatorRow,
  parseIndicatorCsv,
} from "../lib/indicator-data";

export const INDICATOR_CSV_URL =
  "https://raw.githubusercontent.com/suhyeonhong-bit/ToSuhyeon/main/data/processed/monthly_indicators.csv";

type LoadingState = {
  status: "loading";
  rows: [];
  rawCsv: "";
  errorKind: null;
};

type SuccessState = {
  status: "success";
  rows: IndicatorRow[];
  rawCsv: string;
  errorKind: null;
};

type ErrorState = {
  status: "error";
  rows: [];
  rawCsv: "";
  errorKind: "network" | "format";
};

export type IndicatorDataState =
  | LoadingState
  | SuccessState
  | ErrorState;

const LOADING: LoadingState = {
  status: "loading",
  rows: [],
  rawCsv: "",
  errorKind: null,
};

export function useIndicatorData(): IndicatorDataState & {
  retry: () => Promise<void>;
} {
  const [state, setState] = useState<IndicatorDataState>(LOADING);

  const load = useCallback(async () => {
    setState(LOADING);
    try {
      const response = await fetch(INDICATOR_CSV_URL, { cache: "no-store" });
      if (!response.ok) throw new Error("network");
      const rawCsv = await response.text();
      const rows = parseIndicatorCsv(rawCsv);
      setState({ status: "success", rows, rawCsv, errorKind: null });
    } catch (error) {
      setState({
        status: "error",
        rows: [],
        rawCsv: "",
        errorKind: error instanceof IndicatorDataError ? "format" : "network",
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, retry: load };
}
```

- [ ] **Step 4: Implement the pure download descriptor**

Create `app/lib/indicator-download.ts`:

```ts
export type CsvDownload = {
  fileName: "monthly_indicators.csv";
  mimeType: "text/csv;charset=utf-8";
  content: string;
};

export function buildCsvDownload(rawCsv: string): CsvDownload {
  return {
    fileName: "monthly_indicators.csv",
    mimeType: "text/csv;charset=utf-8",
    content: rawCsv,
  };
}
```

- [ ] **Step 5: Run Task 2 tests and confirm green**

Run:

```bash
npx vitest run tests/use-indicator-data.test.tsx tests/indicator-download.test.ts
```

Expected: all hook and download tests PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add tests/use-indicator-data.test.tsx tests/indicator-download.test.ts \
  app/hooks/useIndicatorData.ts app/lib/indicator-download.ts
git commit -m "feat: load and download public indicator CSV"
```

---

### Task 3: Build the Interactive Dual-Axis Trend Chart

**Files:**
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/trend-chart.test.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/TrendChart.tsx`

**Interfaces:**
- Consumes: `IndicatorRow[]`, `formatMonth`, `formatRate`, `formatPpi`.
- Produces:
  - `TrendChart({ rows }: { rows: IndicatorRow[] }): JSX.Element`
  - `buildTooltipValues(row: IndicatorRow): TooltipValues`

- [ ] **Step 1: Write the failing chart interaction tests**

Create `tests/trend-chart.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { TrendChart, buildTooltipValues } from "../app/components/TrendChart";
import type { IndicatorRow } from "../app/lib/indicator-data";

const ROWS: IndicatorRow[] = [
  {
    month: "2026-05",
    koreaBaseRatePercent: null,
    usSteelPpiIndex: 349.023,
  },
  {
    month: "2026-06",
    koreaBaseRatePercent: 2.5,
    usSteelPpiIndex: 361.439,
  },
];

describe("TrendChart", () => {
  it("lets users toggle each series independently", async () => {
    const user = userEvent.setup();
    render(<TrendChart rows={ROWS} />);

    const ppi = screen.getByRole("button", { name: "철강 PPI" });
    const rate = screen.getByRole("button", { name: "한국 기준금리" });
    expect(ppi).toHaveAttribute("aria-pressed", "true");
    expect(rate).toHaveAttribute("aria-pressed", "true");

    await user.click(ppi);
    expect(ppi).toHaveAttribute("aria-pressed", "false");
    expect(rate).toHaveAttribute("aria-pressed", "true");
  });

  it("formats exact tooltip values and missing observations", () => {
    expect(buildTooltipValues(ROWS[0])).toEqual({
      month: "2026년 5월",
      ppi: "349.023",
      rate: "—",
    });
  });
});
```

- [ ] **Step 2: Run the chart tests and confirm red**

Run:

```bash
npx vitest run tests/trend-chart.test.tsx
```

Expected: FAIL because `TrendChart.tsx` does not exist.

- [ ] **Step 3: Implement the accessible Recharts component**

Create `app/components/TrendChart.tsx`:

```tsx
"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  formatMonth,
  formatPpi,
  formatRate,
  type IndicatorRow,
} from "../lib/indicator-data";

type TooltipValues = {
  month: string;
  ppi: string;
  rate: string;
};

type TooltipPayload = {
  payload?: IndicatorRow;
};

export function buildTooltipValues(row: IndicatorRow): TooltipValues {
  return {
    month: formatMonth(row.month),
    ppi: formatPpi(row.usSteelPpiIndex),
    rate: formatRate(row.koreaBaseRatePercent),
  };
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  const values = buildTooltipValues(row);
  return (
    <div className="chart-tooltip" role="status">
      <strong>{values.month}</strong>
      <span>철강 PPI {values.ppi}</span>
      <span>기준금리 {values.rate}</span>
    </div>
  );
}

export function TrendChart({ rows }: { rows: IndicatorRow[] }) {
  const [showPpi, setShowPpi] = useState(true);
  const [showRate, setShowRate] = useState(true);

  return (
    <section className="chart-panel" aria-labelledby="trend-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">60개월 데이터</p>
          <h2 id="trend-title">월별 지표 추이</h2>
          <p>왼쪽은 철강 PPI 지수, 오른쪽은 한국 기준금리 %입니다.</p>
        </div>
        <div className="series-toggles" aria-label="그래프 지표 선택">
          <button
            type="button"
            className="series-toggle series-toggle--ppi"
            aria-pressed={showPpi}
            aria-controls="indicator-trend-chart"
            onClick={() => setShowPpi((value) => !value)}
          >
            철강 PPI
          </button>
          <button
            type="button"
            className="series-toggle series-toggle--rate"
            aria-pressed={showRate}
            aria-controls="indicator-trend-chart"
            onClick={() => setShowRate((value) => !value)}
          >
            한국 기준금리
          </button>
        </div>
      </div>
      <div
        id="indicator-trend-chart"
        className="chart-frame"
        aria-label="미국 철강 PPI와 한국 기준금리 월별 그래프"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={rows}
            margin={{ top: 12, right: 12, bottom: 8, left: 0 }}
            accessibilityLayer
          >
            <CartesianGrid stroke="#d9d6ce" vertical={false} />
            <XAxis
              dataKey="month"
              tickFormatter={(month: string) => month.slice(2)}
              stroke="#697386"
              minTickGap={28}
            />
            <YAxis
              yAxisId="ppi"
              stroke="#b86137"
              width={52}
              domain={["auto", "auto"]}
            />
            <YAxis
              yAxisId="rate"
              orientation="right"
              stroke="#255880"
              width={48}
              domain={["auto", "auto"]}
              tickFormatter={(value: number) => `${value}%`}
            />
            <Tooltip content={<ChartTooltip />} />
            {showPpi ? (
              <Line
                yAxisId="ppi"
                type="monotone"
                dataKey="usSteelPpiIndex"
                name="철강 PPI"
                stroke="#c66e3c"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />
            ) : null}
            {showRate ? (
              <Line
                yAxisId="rate"
                type="stepAfter"
                dataKey="koreaBaseRatePercent"
                name="한국 기준금리"
                stroke="#255880"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />
            ) : null}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run the chart tests and confirm green**

Run:

```bash
npx vitest run tests/trend-chart.test.tsx
```

Expected: chart toggle and tooltip helper tests PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add tests/trend-chart.test.tsx app/components/TrendChart.tsx
git commit -m "feat: add interactive indicator trend chart"
```

---

### Task 4: Compose the Dashboard States, Cards, Table, Guide, and Download

**Files:**
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/dashboard.test.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/DashboardError.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/DashboardLoading.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/DataGuide.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/DownloadCsvButton.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/IndicatorTable.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/MetricCard.tsx`
- Create: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/components/SteelSignalDashboard.tsx`

**Interfaces:**
- Consumes:
  - `useIndicatorData`
  - parser helpers
  - `TrendChart`
  - `buildCsvDownload`
- Produces: complete client dashboard content for `app/page.tsx`.

- [ ] **Step 1: Write failing dashboard state and content tests**

Create `tests/dashboard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SteelSignalDashboard } from "../app/components/SteelSignalDashboard";
import { useIndicatorData } from "../app/hooks/useIndicatorData";

vi.mock("../app/hooks/useIndicatorData", async () => {
  const actual = await vi.importActual<
    typeof import("../app/hooks/useIndicatorData")
  >("../app/hooks/useIndicatorData");
  return { ...actual, useIndicatorData: vi.fn() };
});

vi.mock("../app/components/TrendChart", () => ({
  TrendChart: () => <div data-testid="trend-chart">chart</div>,
}));

const mockedUseIndicatorData = vi.mocked(useIndicatorData);
const ROWS = [
  {
    month: "2026-05",
    koreaBaseRatePercent: 2.5,
    usSteelPpiIndex: 349.023,
  },
  {
    month: "2026-06",
    koreaBaseRatePercent: 2.5,
    usSteelPpiIndex: 361.439,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SteelSignalDashboard", () => {
  it("shows the product shell and loading status", () => {
    mockedUseIndicatorData.mockReturnValue({
      status: "loading",
      rows: [],
      rawCsv: "",
      errorKind: null,
      retry: vi.fn(),
    });
    render(<SteelSignalDashboard />);
    expect(screen.getByText("STEEL SIGNAL")).toBeInTheDocument();
    expect(
      screen.getByText("최신 데이터를 불러오고 있습니다."),
    ).toBeInTheDocument();
  });

  it("shows a plain-language format error and retries", async () => {
    const user = userEvent.setup();
    const retry = vi.fn().mockResolvedValue(undefined);
    mockedUseIndicatorData.mockReturnValue({
      status: "error",
      rows: [],
      rawCsv: "",
      errorKind: "format",
      retry,
    });
    render(<SteelSignalDashboard />);
    expect(
      screen.getByText("데이터 형식을 확인할 수 없습니다"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("shows latest metrics, newest-first table and public sources", () => {
    mockedUseIndicatorData.mockReturnValue({
      status: "success",
      rows: ROWS,
      rawCsv: "csv",
      errorKind: null,
      retry: vi.fn(),
    });
    render(<SteelSignalDashboard />);

    expect(screen.getByText("2026년 6월 데이터 기준")).toBeInTheDocument();
    expect(screen.getByText("2.50%")).toBeInTheDocument();
    expect(screen.getByText("361.439")).toBeInTheDocument();
    expect(screen.getByTestId("trend-chart")).toBeInTheDocument();
    const tableRows = screen.getAllByRole("row");
    expect(tableRows[1]).toHaveTextContent("2026-06");
    expect(tableRows[2]).toHaveTextContent("2026-05");
    expect(
      screen.getByRole("link", { name: "한국은행 ECOS" }),
    ).toHaveAttribute("href", "https://ecos.bok.or.kr/");
    expect(screen.getByRole("link", { name: "미국 FRED" })).toHaveAttribute(
      "href",
      "https://fred.stlouisfed.org/series/WPU1017",
    );
  });

  it("downloads the exact fetched CSV", async () => {
    const user = userEvent.setup();
    const rawCsv =
      "month,korea_base_rate_percent,us_steel_ppi_index\n" +
      "2026-06,2.5,361.439\n";
    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:test-download");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL");
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    mockedUseIndicatorData.mockReturnValue({
      status: "success",
      rows: ROWS,
      rawCsv,
      errorKind: null,
      retry: vi.fn(),
    });

    render(<SteelSignalDashboard />);
    await user.click(screen.getByRole("button", { name: "CSV 내려받기" }));

    expect(createObjectUrl).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:test-download");
  });
});
```

- [ ] **Step 2: Run the dashboard tests and confirm red**

Run:

```bash
npx vitest run tests/dashboard.test.tsx
```

Expected: FAIL because dashboard display components do not exist.

- [ ] **Step 3: Implement the small display components**

Create `app/components/MetricCard.tsx`:

```tsx
export function MetricCard({
  label,
  value,
  month,
  tone,
}: {
  label: string;
  value: string;
  month: string;
  tone: "rate" | "ppi";
}) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{month} 기준</span>
    </article>
  );
}
```

Create `app/components/DashboardLoading.tsx`:

```tsx
export function DashboardLoading() {
  return (
    <section className="loading-panel" role="status" aria-live="polite">
      <div className="loading-card" />
      <div className="loading-card" />
      <div className="loading-chart" />
      <p>최신 데이터를 불러오고 있습니다.</p>
    </section>
  );
}
```

Create `app/components/DashboardError.tsx`:

```tsx
import { INDICATOR_CSV_URL } from "../hooks/useIndicatorData";

export function DashboardError({
  kind,
  onRetry,
}: {
  kind: "network" | "format";
  onRetry: () => Promise<void>;
}) {
  const title =
    kind === "format"
      ? "데이터 형식을 확인할 수 없습니다"
      : "데이터를 불러오지 못했습니다";

  return (
    <section className="error-panel" role="alert">
      <span className="error-mark" aria-hidden="true">!</span>
      <h2>{title}</h2>
      <p>잠시 후 다시 시도하거나 GitHub에서 원본 CSV를 확인해주세요.</p>
      <div className="error-actions">
        <button type="button" onClick={() => void onRetry()}>
          다시 시도
        </button>
        <a href={INDICATOR_CSV_URL}>GitHub 원본 CSV</a>
      </div>
    </section>
  );
}
```

Create `app/components/IndicatorTable.tsx`:

```tsx
import {
  formatPpi,
  formatRate,
  type IndicatorRow,
} from "../lib/indicator-data";

export function IndicatorTable({ rows }: { rows: IndicatorRow[] }) {
  const newestFirst = [...rows].reverse();
  return (
    <div className="table-scroll">
      <table>
        <caption>한국 기준금리와 미국 철강 PPI 월별 전체 데이터</caption>
        <thead>
          <tr>
            <th scope="col">월</th>
            <th scope="col">한국 기준금리</th>
            <th scope="col">미국 철강 PPI</th>
          </tr>
        </thead>
        <tbody>
          {newestFirst.map((row) => (
            <tr key={row.month}>
              <th scope="row">{row.month}</th>
              <td>{formatRate(row.koreaBaseRatePercent)}</td>
              <td>{formatPpi(row.usSteelPpiIndex)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

Create `app/components/DataGuide.tsx`:

```tsx
export function DataGuide() {
  return (
    <aside className="guide-panel" aria-labelledby="guide-title">
      <p className="eyebrow">읽는 법</p>
      <h2 id="guide-title">숫자의 단위를 먼저 확인하세요</h2>
      <ul>
        <li>철강 PPI는 퍼센트가 아니라 지수 수준입니다.</li>
        <li>두 지표는 단위가 달라 그래프의 양쪽 축을 사용합니다.</li>
        <li>두 선이 함께 움직여도 원인과 결과를 바로 뜻하지 않습니다.</li>
      </ul>
      <div className="source-links">
        <a href="https://ecos.bok.or.kr/">한국은행 ECOS</a>
        <a href="https://fred.stlouisfed.org/series/WPU1017">미국 FRED</a>
      </div>
    </aside>
  );
}
```

Create `app/components/DownloadCsvButton.tsx`:

```tsx
"use client";

import { buildCsvDownload } from "../lib/indicator-download";

export function DownloadCsvButton({ rawCsv }: { rawCsv: string }) {
  function download() {
    const descriptor = buildCsvDownload(rawCsv);
    const url = URL.createObjectURL(
      new Blob([descriptor.content], { type: descriptor.mimeType }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = descriptor.fileName;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button type="button" className="download-button" onClick={download}>
      CSV 내려받기
    </button>
  );
}
```

- [ ] **Step 4: Implement the stateful page composition**

Create `app/components/SteelSignalDashboard.tsx`:

```tsx
"use client";

import { useIndicatorData } from "../hooks/useIndicatorData";
import {
  formatMonth,
  formatPpi,
  formatRate,
  getLatestDataMonth,
  getLatestMetric,
} from "../lib/indicator-data";
import { DashboardError } from "./DashboardError";
import { DashboardLoading } from "./DashboardLoading";
import { DataGuide } from "./DataGuide";
import { DownloadCsvButton } from "./DownloadCsvButton";
import { IndicatorTable } from "./IndicatorTable";
import { MetricCard } from "./MetricCard";
import { TrendChart } from "./TrendChart";

export function SteelSignalDashboard() {
  const data = useIndicatorData();

  return (
    <main className="site-shell">
      <header className="site-header">
        <a className="brand" href="#top">STEEL SIGNAL</a>
        {data.status === "success" ? (
          <span>{formatMonth(getLatestDataMonth(data.rows))} 데이터 기준</span>
        ) : (
          <span>공개 경제지표 대시보드</span>
        )}
      </header>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">5년 시장 지표</p>
          <h1>금리와 철강 가격의<br />흐름을 한눈에</h1>
          <p className="hero-copy">
            한국은행 기준금리와 미국 철강 생산자물가지수를 월별로 연결해
            시장의 방향을 살펴봅니다.
          </p>
        </div>
      </section>

      {data.status === "loading" ? <DashboardLoading /> : null}
      {data.status === "error" ? (
        <DashboardError kind={data.errorKind} onRetry={data.retry} />
      ) : null}
      {data.status === "success" ? (
        <>
          <section className="metric-grid" aria-label="최신 지표">
            <MetricCard
              label="한국 기준금리"
              value={formatRate(
                getLatestMetric(data.rows, "koreaBaseRatePercent").value,
              )}
              month={formatMonth(
                getLatestMetric(data.rows, "koreaBaseRatePercent").month,
              )}
              tone="rate"
            />
            <MetricCard
              label="미국 철강 PPI"
              value={formatPpi(
                getLatestMetric(data.rows, "usSteelPpiIndex").value,
              )}
              month={formatMonth(
                getLatestMetric(data.rows, "usSteelPpiIndex").month,
              )}
              tone="ppi"
            />
          </section>
          <TrendChart rows={data.rows} />
          <section className="detail-grid">
            <div className="table-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">원본에 가까운 보기</p>
                  <h2>월별 전체 데이터</h2>
                </div>
                <DownloadCsvButton rawCsv={data.rawCsv} />
              </div>
              <IndicatorTable rows={data.rows} />
            </div>
            <DataGuide />
          </section>
        </>
      ) : null}

      <footer className="site-footer">
        <p>매주 월요일 오전 11시 한국 시간 자동 갱신</p>
        <a href="https://github.com/suhyeonhong-bit/ToSuhyeon">
          공개 GitHub 데이터 저장소
        </a>
        <p>이 페이지는 공개 경제지표를 보여주며 투자 판단을 제공하지 않습니다.</p>
      </footer>
    </main>
  );
}
```

- [ ] **Step 5: Run dashboard tests and confirm green**

Run:

```bash
npx vitest run tests/dashboard.test.tsx
```

Expected: all dashboard state/content tests PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add tests/dashboard.test.tsx app/components
git commit -m "feat: compose STEEL SIGNAL dashboard"
```

---

### Task 5: Apply the Approved Visual System, Metadata, and Product Build

**Files:**
- Modify: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/page.tsx`
- Modify: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/layout.tsx`
- Replace: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/globals.css`
- Replace: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/tests/rendered-html.test.mjs`
- Delete: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/_sites-preview/SkeletonPreview.tsx`
- Delete: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/app/_sites-preview/preview.css`
- Delete: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/public/favicon.svg`
- Delete: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/public/file.svg`
- Delete: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/public/globe.svg`
- Delete: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/public/window.svg`
- Modify: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/package.json`
- Create if validated: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/public/og.png`

**Interfaces:**
- Consumes: `SteelSignalDashboard`.
- Produces: complete responsive product page, Korean metadata, link preview, and Cloudflare-compatible build.

- [ ] **Step 1: Replace the starter rendered-HTML test with product assertions**

Replace `tests/rendered-html.test.mjs` with:

```js
import assert from "node:assert/strict";
import { access } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("https://steel-signal.example/", {
      headers: {
        accept: "text/html",
        host: "steel-signal.example",
        "x-forwarded-host": "steel-signal.example",
        "x-forwarded-proto": "https",
      },
    }),
    {
      ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
    },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the STEEL SIGNAL product shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<html[^>]*lang="ko"/i);
  assert.match(html, /<title>STEEL SIGNAL/);
  assert.match(html, /금리와 철강 가격의/);
  assert.match(html, /최신 데이터를 불러오고 있습니다/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|Building your site/i);
  assert.doesNotMatch(html, /FRED_API_KEY|ECOS_API_KEY/);
});

test("removes disposable starter assets", async () => {
  await assert.rejects(access(new URL("app/_sites-preview", projectRoot)));
});
```

- [ ] **Step 2: Run the rendered test before replacing the starter**

Run:

```bash
npm run build
node --test tests/rendered-html.test.mjs
```

Expected: FAIL because the current starter does not contain STEEL SIGNAL and
still contains the disposable preview.

- [ ] **Step 3: Replace the page and metadata**

Replace `app/page.tsx` with:

```tsx
import { SteelSignalDashboard } from "./components/SteelSignalDashboard";

export default function Home() {
  return <SteelSignalDashboard />;
}
```

Replace `app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const incoming = await headers();
  const protocol = incoming.get("x-forwarded-proto") ?? "https";
  const host =
    incoming.get("x-forwarded-host") ??
    incoming.get("host") ??
    "localhost:3000";
  const origin = `${protocol}://${host}`;

  return {
    title: "STEEL SIGNAL | 금리와 철강 가격의 흐름",
    description:
      "한국 기준금리와 미국 철강 생산자물가지수의 최신 값과 5년 흐름을 한눈에 확인하세요.",
    openGraph: {
      title: "STEEL SIGNAL",
      description: "금리와 철강 가격의 흐름을 한눈에",
      type: "website",
      locale: "ko_KR",
      images: [{ url: `${origin}/og.png`, width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      title: "STEEL SIGNAL",
      description: "금리와 철강 가격의 흐름을 한눈에",
      images: [`${origin}/og.png`],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

If no validated `public/og.png` is available in Step 7, remove both `images`
properties before the final build instead of shipping a missing or generic
image.

- [ ] **Step 4: Apply the complete approved CSS system**

Replace `app/globals.css` with CSS that contains these exact foundations and
component contracts:

```css
@import "tailwindcss";

:root {
  --ivory: #f4f0e8;
  --paper: #fffdf8;
  --navy: #17253b;
  --muted: #687384;
  --line: #d9d6ce;
  --copper: #c66e3c;
  --blue: #255880;
  --error: #9d472c;
  --focus: #0f6cbd;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--navy);
  background: var(--ivory);
  font-family: "Pretendard Variable", Pretendard, -apple-system,
    BlinkMacSystemFont, "Segoe UI", sans-serif;
}
button, a { font: inherit; }
button:focus-visible, a:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 3px;
}
.site-shell { width: min(1180px, calc(100% - 40px)); margin: 0 auto; }
.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 76px;
  border-bottom: 1px solid rgba(23, 37, 59, .14);
  font-size: .875rem;
}
.brand {
  color: var(--navy);
  font-weight: 900;
  letter-spacing: .09em;
  text-decoration: none;
}
.site-header span {
  border: 1px solid rgba(23, 37, 59, .2);
  border-radius: 999px;
  padding: 7px 11px;
  color: var(--muted);
}
.hero { padding: 72px 0 40px; }
.eyebrow {
  margin: 0 0 10px;
  color: var(--copper);
  font-size: .75rem;
  font-weight: 850;
  letter-spacing: .13em;
  text-transform: uppercase;
}
.hero h1 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(2.7rem, 7vw, 5.8rem);
  line-height: .99;
  letter-spacing: -.055em;
}
.hero-copy {
  max-width: 620px;
  margin: 24px 0 0;
  color: var(--muted);
  font-size: clamp(1rem, 2vw, 1.2rem);
  line-height: 1.7;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}
.metric-card {
  position: relative;
  overflow: hidden;
  min-height: 180px;
  padding: 28px;
  border: 1px solid rgba(23, 37, 59, .12);
  border-radius: 22px;
  background: rgba(255, 253, 248, .78);
}
.metric-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 5px;
  background: var(--blue);
}
.metric-card--ppi::before { background: var(--copper); }
.metric-card p { margin: 0; color: var(--muted); font-weight: 750; }
.metric-card strong {
  display: block;
  margin: 18px 0 12px;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  line-height: 1;
}
.metric-card span { color: var(--muted); font-size: .9rem; }
.chart-panel, .table-panel, .guide-panel {
  border: 1px solid rgba(23, 37, 59, .12);
  border-radius: 22px;
  background: rgba(255, 253, 248, .82);
}
.chart-panel { padding: 28px; }
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}
.panel-heading h2, .guide-panel h2 { margin: 0; font-size: 1.45rem; }
.panel-heading p:not(.eyebrow) { margin: 7px 0 0; color: var(--muted); }
.series-toggles { display: flex; flex-wrap: wrap; gap: 8px; }
.series-toggle, .download-button, .error-actions button {
  border: 1px solid rgba(23, 37, 59, .18);
  border-radius: 999px;
  padding: 9px 13px;
  background: var(--paper);
  color: var(--navy);
  cursor: pointer;
  font-weight: 800;
}
.series-toggle--ppi { color: var(--copper); }
.series-toggle--rate { color: var(--blue); }
.series-toggle[aria-pressed="false"] { opacity: .42; text-decoration: line-through; }
.chart-frame { width: 100%; height: 430px; }
.chart-tooltip {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--navy);
  color: white;
  box-shadow: 0 12px 30px rgba(23, 37, 59, .2);
}
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(260px, .7fr);
  gap: 18px;
  margin-top: 18px;
}
.table-panel, .guide-panel { padding: 26px; }
.download-button { color: white; background: var(--navy); }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
caption {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
th, td {
  padding: 13px 10px;
  border-bottom: 1px solid rgba(23, 37, 59, .1);
  text-align: right;
  white-space: nowrap;
}
th:first-child, td:first-child { text-align: left; }
thead th { color: var(--muted); font-size: .8rem; }
tbody th { font-weight: 700; }
.guide-panel ul { padding-left: 20px; color: var(--muted); line-height: 1.65; }
.source-links { display: flex; flex-wrap: wrap; gap: 8px; }
.source-links a, .error-actions a {
  border-radius: 9px;
  padding: 8px 10px;
  color: var(--navy);
  background: #e9edf2;
  font-weight: 750;
  text-decoration: none;
}
.loading-panel, .error-panel {
  min-height: 390px;
  margin-bottom: 18px;
  padding: 28px;
  border: 1px solid rgba(23, 37, 59, .12);
  border-radius: 22px;
  background: rgba(255, 253, 248, .82);
}
.loading-card, .loading-chart {
  background: linear-gradient(90deg, #e5e0d6, #faf7f0, #e5e0d6);
  background-size: 200% 100%;
  animation: loading 1.8s ease-in-out infinite;
}
.loading-card { display: inline-block; width: calc(50% - 8px); height: 110px; border-radius: 16px; }
.loading-card + .loading-card { margin-left: 12px; }
.loading-chart { height: 180px; margin-top: 16px; border-radius: 16px; }
.loading-panel p { color: var(--muted); text-align: center; }
.error-panel { display: grid; place-items: center; align-content: center; text-align: center; }
.error-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  color: white;
  background: var(--error);
  font-weight: 900;
}
.error-panel h2 { margin: 16px 0 8px; }
.error-panel p { margin: 0; color: var(--muted); }
.error-actions { display: flex; gap: 10px; margin-top: 18px; }
.error-actions button { color: white; background: var(--navy); }
.site-footer {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 16px;
  align-items: center;
  margin-top: 44px;
  padding: 26px 0 40px;
  border-top: 1px solid rgba(23, 37, 59, .14);
  color: var(--muted);
  font-size: .8rem;
}
.site-footer a { color: var(--navy); font-weight: 800; }
.site-footer p:last-child { text-align: right; }
@keyframes loading { to { background-position: -200% 0; } }
@media (max-width: 800px) {
  .site-shell { width: min(100% - 24px, 680px); }
  .site-header { align-items: flex-start; gap: 12px; padding: 18px 0; }
  .site-header span { font-size: .72rem; }
  .hero { padding: 52px 0 32px; }
  .metric-grid, .detail-grid, .site-footer { grid-template-columns: 1fr; }
  .panel-heading { align-items: stretch; flex-direction: column; }
  .chart-panel, .table-panel, .guide-panel { padding: 18px; }
  .chart-frame { height: 340px; }
  .site-footer p:last-child { text-align: left; }
}
@media (max-width: 520px) {
  .metric-grid { grid-template-columns: 1fr; }
  .metric-card { min-height: 150px; padding: 22px; }
  .chart-frame { height: 300px; }
  .loading-card { display: block; width: 100%; }
  .loading-card + .loading-card { margin: 10px 0 0; }
  .error-actions { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

- [ ] **Step 5: Remove all starter-only product files and dependency**

Remove `app/_sites-preview/` and the unused starter public SVG files listed
above. Remove `react-loading-skeleton`:

```bash
npm uninstall react-loading-skeleton
```

Verify:

```bash
rg -n "codex-preview|SkeletonPreview|react-loading-skeleton|Your site is taking shape" .
```

Expected: no matches outside ignored build/cache directories.

- [ ] **Step 6: Run the complete local validation before social metadata**

Run:

```bash
npm run test:unit
npm run build
node --test tests/rendered-html.test.mjs
npm run lint
```

Expected: unit tests PASS, build succeeds, product rendered-HTML tests PASS,
and lint reports no errors.

- [ ] **Step 7: Generate and validate exactly one product-specific social card**

Use one `imagegen` call with a prompt equivalent to:

```text
Create a complete 1200×630 social preview card for STEEL SIGNAL, a Korean
economic dashboard. Use a warm ivory background (#f4f0e8), dark navy
typography (#17253b), copper and muted blue chart accents. Include the exact
text “STEEL SIGNAL” and “금리와 철강 가격의 흐름을 한눈에”. Show two refined
metric cards and an abstract dual-line market chart. Professional editorial
market brief, high legibility in Slack and iMessage, no device frame, no logos,
no watermark, no invented numbers.
```

Inspect the returned image. If all text is correct and legible, save it as
`public/og.png` and retain the metadata image URLs. Retry once only when the
first card has incorrect, missing, or invented text. If the second result is
still unusable, do not save it and remove the Open Graph/Twitter `images`
fields from `app/layout.tsx`.

- [ ] **Step 8: Run the final build after social metadata changes**

Run:

```bash
npm test
npm run lint
git status --short
```

Expected:

- All unit and rendered tests PASS.
- Cloudflare Worker-compatible build succeeds.
- Lint has no errors.
- Only intentional product files are modified.

- [ ] **Step 9: Commit Task 5**

```bash
git add app public tests package.json package-lock.json
git commit -m "feat: finish STEEL SIGNAL dashboard experience"
```

---

### Task 6: Package, Publish Publicly, and Verify the Deployment

**Files:**
- Modify: `/Users/suhyeonhong/Documents/GitHub/SteelSignal/.openai/hosting.json`
- Create temporarily outside source: deployment archive generated by the Sites package helper

**Interfaces:**
- Consumes: successful `npm test`, lint, and build output from Task 5.
- Produces: public deployed URL and persisted Sites `project_id`.

- [ ] **Step 1: Read hosting metadata before creating anything**

Read:

```text
/Users/suhyeonhong/Documents/GitHub/SteelSignal/.openai/hosting.json
```

Expected: `d1` and `r2` are `null`, and no `project_id` exists for this new
site.

- [ ] **Step 2: Discover the current Sites connector schemas**

Use the connector discovery sequence required by Sites. Confirm the exact
arguments for:

- `create_site`
- source repository write credential creation or reuse
- `save_site_version`
- public deployment
- `get_deployment_status`
- `open_in_codex`

Do not invent IDs or call `create_site` more than once.

- [ ] **Step 3: Create the site once and persist its project ID**

Create one site with a human-readable name/slug based on `steel-signal`.
Persist only the returned opaque `project_id` alongside the existing `d1` and
`r2` values in `.openai/hosting.json`. Keep source credentials out of files,
Git configuration, logs, and user-facing messages.

- [ ] **Step 4: Commit the exact validated source and push it with the Sites credential**

Run:

```bash
git status --short
git add .openai/hosting.json
git commit -m "chore: connect STEEL SIGNAL hosting"
```

Push the exact branch head using the returned per-command HTTP authorization
header. Record the pushed branch-head SHA as `commit_sha`. Do not embed the
credential in a remote URL.

- [ ] **Step 5: Package the exact pushed state**

Run the bundled helper:

```bash
bash /Users/suhyeonhong/.codex/plugins/cache/openai-bundled/sites/0.1.30/scripts/package-site.sh \
  /Users/suhyeonhong/Documents/GitHub/SteelSignal \
  /private/tmp/steel-signal-site.tar.gz
```

Expected archive contents include:

- `dist/server/index.js`
- `dist/.openai/hosting.json`
- emitted static assets
- no `.env`, API key, `.git`, source credential, or `node_modules`

- [ ] **Step 6: Save one version from the pushed commit and archive**

Call `save_site_version` once with the exact opaque `project_id`, the exact
`commit_sha` from Step 4, and the archive from Step 5. Preserve returned version
IDs exactly.

- [ ] **Step 7: Deploy publicly using the user's approved access level**

The approved design explicitly requires a public dashboard. Use the connector's
public deployment action for the saved version. Deploy only the saved version;
do not deploy a working tree or an unsaved archive.

- [ ] **Step 8: Poll deployment status to a terminal result**

Call `get_deployment_status` until status is `succeeded` or `failed`.

Expected on success:

- public deployed URL is returned;
- status is `succeeded`;
- the URL resolves to STEEL SIGNAL, not the starter skeleton.

On failure, stop and report the connector's user-visible reason without
creating another site or changing the slug speculatively.

- [ ] **Step 9: Open the public deployment and hand it off**

Call `open_in_codex` once with the exact deployed URL and no `threadId`.
Return that URL as the primary deliverable and explain in plain Korean:

- opening the page reads the latest GitHub CSV;
- Monday data updates do not require site redeployment;
- the chart supports hover and independent series toggles;
- the table and CSV download expose all 60 months;
- API keys are not included in the public site.

- [ ] **Step 10: Stop retained local processes**

After hosting succeeds, stop the retained `npm run dev` session. Stop the
brainstorming companion server using:

```bash
bash /Users/suhyeonhong/.codex/skills/brainstorming/scripts/stop-server.sh \
  /Users/suhyeonhong/Documents/GitHub/ToSuhyeon/.superpowers/brainstorm/26914-1785383099
```

Do not delete the ignored mockup directory; it remains available for design
reference without entering Git history.

---

## Final Verification Checklist

- [ ] Existing `ToSuhyeon` collector tests still pass unchanged.
- [ ] `SteelSignal` unit tests pass.
- [ ] `SteelSignal` Cloudflare-compatible production build succeeds.
- [ ] Rendered HTML contains Korean metadata and product shell.
- [ ] Starter skeleton, temporary metadata, and starter assets are absent.
- [ ] Public site fetches the exact GitHub CSV URL at runtime.
- [ ] Latest cards match the last valid values in the CSV.
- [ ] Chart tooltip, toggles, dual axes, and missing-value breaks are present.
- [ ] Table is newest-first and includes all parsed rows.
- [ ] CSV download preserves the fetched contents.
- [ ] Loading, network error, format error, and retry states are covered.
- [ ] Mobile styles, keyboard focus, semantic table, and reduced motion are present.
- [ ] No `.env`, API keys, source credential, or private data appears in source, build, archive, or deployment.
- [ ] Deployment status is `succeeded`.
- [ ] Public URL is opened and returned to the user.
