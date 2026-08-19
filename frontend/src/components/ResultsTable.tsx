import type { QueryResponse } from "../api";

function exportCSV(result: QueryResponse) {
  if (!result.rows.length) return;

  const headers = result.columns;
  const csv = [
    headers.join(","),
    ...result.rows.map((row) =>
      headers.map((h) => JSON.stringify(row[h] ?? "")).join(",")
    ),
  ].join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "query-results.csv";
  a.click();
  window.URL.revokeObjectURL(url);
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function CacheBadge({ result }: { result: QueryResponse }) {
  if (result.cache_status === "hit") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
        ⚡ Cached · saved ${result.api_cost_saved.toFixed(6)}
      </span>
    );
  }
  if (result.cache_status === "regenerated_schema_changed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
        🔄 Schema changed · regenerated
      </span>
    );
  }
  if (result.cache_status === "miss" && result.source === "llm") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
        🆕 New query · ${result.api_cost.toFixed(6)}
      </span>
    );
  }
  return null;
}

export function ResultsTable({ result }: { result: QueryResponse }) {
  return (
    <div className="flex flex-col gap-4">
      {/* ── SQL block (always shown) ── */}
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Generated SQL
          </p>
          <CacheBadge result={result} />
          {result.is_preview && (
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-500">
              Preview — not executed
            </span>
          )}
          <span className="ml-auto text-[11px] text-neutral-400">
            {result.execution_time_ms}ms
          </span>
        </div>
        <pre className="overflow-x-auto rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3 font-mono text-[13px] leading-relaxed text-neutral-800">
          {result.sql}
        </pre>
      </div>

      {/* ── Preview notice (write / DDL queries) ── */}
      {result.is_preview ? (
        <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3">
          <div className="flex items-start gap-2.5">
            <svg
              className="mt-0.5 h-4 w-4 shrink-0 text-neutral-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <p className="text-sm font-medium text-neutral-700">
                Query generated — not executed
              </p>
              <p className="mt-0.5 text-sm text-neutral-500">
                This is a write or schema-change query (DELETE, ALTER, UPDATE,
                INSERT, etc.). It has been generated for your review but has not
                been run against the database. Copy the SQL above and apply it
                manually when ready.
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* ── Normal SELECT results ── */
        <>
          <div className="flex items-center justify-between">
            <p className="text-xs text-neutral-500">
              {result.row_count} {result.row_count === 1 ? "row" : "rows"}
            </p>
            <button
              onClick={() => exportCSV(result)}
              disabled={!result.rows.length}
              className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Export CSV
            </button>
          </div>

          <div className="overflow-x-auto rounded-md border border-neutral-200">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50">
                  {result.columns.map((col) => (
                    <th
                      key={col}
                      className="whitespace-nowrap px-4 py-2.5 font-mono text-xs font-semibold text-neutral-600"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr
                    key={i}
                    className="border-b border-neutral-100 last:border-0"
                  >
                    {result.columns.map((col) => (
                      <td key={col} className="whitespace-nowrap px-4 py-2.5 text-neutral-800">
                        {formatCell(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
                {result.rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={result.columns.length || 1}
                      className="px-4 py-6 text-center text-neutral-400"
                    >
                      No rows returned.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
