import type { SchemaResponse } from "../api";

interface Props {
  schema: SchemaResponse | null;
  loading: boolean;
  error: string | null;
  /** When true, renders without its own <aside> wrapper (for embedding inside another sidebar). */
  bare?: boolean;
}

function SchemaPanelContent({ schema, loading, error }: Props) {
  return (
    <>
      <div className="border-b border-neutral-200 px-5 py-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Database Schema
        </h2>
      </div>

      <div className="max-h-[calc(100vh-57px)] overflow-y-auto px-5 py-4">
        {loading && <p className="text-sm text-neutral-400">Loading schema…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {schema &&
          Object.entries(schema.tables).map(([tableName, columns]) => (
            <div key={tableName} className="mb-5 last:mb-0">
              <p className="mb-1.5 font-mono text-sm font-medium text-neutral-800">
                {tableName}
              </p>
              <ul className="space-y-0.5 border-l border-neutral-200 pl-3">
                {columns.map((col) => (
                  <li key={col.name} className="flex items-baseline justify-between gap-2">
                    <span className="truncate font-mono text-[13px] text-neutral-600">
                      {col.name}
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-neutral-400">
                      {col.type}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
      </div>
    </>
  );
}

export function SchemaPanel({ schema, loading, error, bare }: Props) {
  if (bare) {
    return <SchemaPanelContent schema={schema} loading={loading} error={error} />;
  }
  return (
    <aside className="w-72 shrink-0 border-r border-neutral-200 bg-white">
      <SchemaPanelContent schema={schema} loading={loading} error={error} />
    </aside>
  );
}
