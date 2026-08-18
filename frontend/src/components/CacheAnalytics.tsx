import { useEffect, useState } from "react";
import {
  fetchCacheAnalytics,
  fetchCacheInvalidations,
  type CacheAnalyticsResponse,
  type CacheInvalidationsResponse,
} from "../api";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-neutral-500">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

export function CacheAnalytics() {
  const [analytics, setAnalytics] = useState<CacheAnalyticsResponse | null>(null);
  const [invalidations, setInvalidations] = useState<CacheInvalidationsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function load() {
      Promise.all([fetchCacheAnalytics(), fetchCacheInvalidations()])
        .then(([a, inv]) => {
          setAnalytics(a);
          setInvalidations(inv);
          setError(null);
        })
        .catch((err: Error) => setError(err.message));
    }

    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  if (!analytics) {
    return <p className="text-sm text-neutral-400">Loading cache analytics…</p>;
  }

  const total =
    analytics.total_cache_hits + analytics.total_cache_misses + analytics.total_invalidations;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard
          label="Hit Rate"
          value={`${(analytics.hit_rate * 100).toFixed(1)}%`}
          accent="text-emerald-600"
        />
        <MetricCard
          label="Cache Hits"
          value={String(analytics.total_cache_hits)}
          accent="text-blue-600"
        />
        <MetricCard
          label="Cost Saved"
          value={`$${analytics.total_cost_saved.toFixed(6)}`}
          accent="text-emerald-600"
        />
        <MetricCard
          label="Unique Queries"
          value={String(analytics.total_queries_cached)}
          accent="text-purple-600"
        />
      </div>

      {total > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Hits vs Misses vs Invalidations
          </p>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-neutral-100">
            <div
              className="bg-emerald-500"
              style={{ width: `${(analytics.total_cache_hits / total) * 100}%` }}
            />
            <div
              className="bg-blue-500"
              style={{ width: `${(analytics.total_cache_misses / total) * 100}%` }}
            />
            <div
              className="bg-amber-500"
              style={{ width: `${(analytics.total_invalidations / total) * 100}%` }}
            />
          </div>
          <div className="mt-1.5 flex gap-4 text-[11px] text-neutral-500">
            <span>🟢 Hits: {analytics.total_cache_hits}</span>
            <span>🔵 Misses: {analytics.total_cache_misses}</span>
            <span>🟠 Invalidations: {analytics.total_invalidations}</span>
          </div>
        </div>
      )}

      <div>
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Top Cached Queries
        </p>
        <div className="overflow-x-auto rounded-md border border-neutral-200">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50">
                <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Question</th>
                <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Hits</th>
                <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Cost Saved</th>
                <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Last Used</th>
              </tr>
            </thead>
            <tbody>
              {analytics.top_cached_queries.map((q) => (
                <tr key={q.question} className="border-b border-neutral-100 last:border-0">
                  <td className="max-w-xs truncate px-3 py-2 text-neutral-800">{q.question}</td>
                  <td className="px-3 py-2 text-neutral-800">{q.hit_count}</td>
                  <td className="px-3 py-2 text-neutral-800">${q.cost_saved.toFixed(6)}</td>
                  <td className="px-3 py-2 text-neutral-500">{formatDate(q.last_used_at)}</td>
                </tr>
              ))}
              {analytics.top_cached_queries.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-neutral-400">
                    No cached queries yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {invalidations && invalidations.invalidations.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Recent Schema-Change Invalidations
          </p>
          <div className="overflow-x-auto rounded-md border border-neutral-200">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50">
                  <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Question</th>
                  <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Reason</th>
                  <th className="px-3 py-2 text-xs font-semibold text-neutral-600">Old → New Hash</th>
                  <th className="px-3 py-2 text-xs font-semibold text-neutral-600">When</th>
                </tr>
              </thead>
              <tbody>
                {invalidations.invalidations.map((event, i) => (
                  <tr key={i} className="border-b border-neutral-100 last:border-0">
                    <td className="max-w-xs truncate px-3 py-2 text-neutral-800">{event.question}</td>
                    <td className="px-3 py-2 text-neutral-500">{event.reason ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-[11px] text-neutral-500">
                      {(event.old_schema_hash ?? "").slice(0, 8)} → {(event.new_schema_hash ?? "").slice(0, 8)}
                    </td>
                    <td className="px-3 py-2 text-neutral-500">{formatDate(event.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
