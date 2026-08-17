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

export function ResultsTable({ result }: { result: QueryResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Generated SQL
          </p>
          <span
            className={
              "rounded-full px-2 py-0.5 text-[11px] font-medium " +
              (result.source === "template"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-indigo-50 text-indigo-700")
            }
          >
            {result.source === "template" ? "Rule-based match" : "Claude"}
          </span>
        </div>
        <pre className="overflow-x-auto rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3 font-mono text-[13px] leading-relaxed text-neutral-800">
          {result.sql}
        </pre>
      </div>

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
    </div>
  );
}
