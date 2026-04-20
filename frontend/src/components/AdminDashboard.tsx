/**
 * Admin Dashboard — usage stats for the current tenant.
 * Requires admin-scoped API key (or header auth in dev).
 */
import React, { useEffect, useState } from 'react';

interface Trend {
  date: string;
  count: number;
}

interface Stats {
  tenant_id: string;
  period_days: number;
  components: {
    total_active: number;
    trend: Trend[];
  };
  active_pins: number;
  active_api_keys: number;
  cache: {
    cache_hits?: number;
    cache_misses?: number;
  };
  generated_at: string;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="stat bg-base-100 rounded-xl border border-base-300 shadow-sm">
      <div className="stat-title text-xs font-semibold uppercase tracking-wide">{label}</div>
      <div className="stat-value text-2xl font-bold">{value}</div>
      {sub && <div className="stat-desc text-xs opacity-60">{sub}</div>}
    </div>
  );
}

function MiniChart({ trend }: { trend: Trend[] }) {
  if (!trend.length) return <div className="text-xs opacity-40 text-center py-4">No data yet</div>;

  const max = Math.max(...trend.map((t) => t.count), 1);
  return (
    <div className="flex items-end gap-1 h-16 w-full">
      {trend.map((t) => (
        <div key={t.date} className="flex-1 flex flex-col items-center gap-0.5 group">
          <div
            className="w-full rounded-sm bg-primary/70 group-hover:bg-primary transition-all"
            style={{ height: `${Math.max(4, (t.count / max) * 56)}px` }}
            title={`${t.date}: ${t.count}`}
          />
        </div>
      ))}
    </div>
  );
}

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  const load = async (d: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/stats?days=${d}`);
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.detail ?? `HTTP ${res.status}`);
      }
      setStats(await res.json());
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(days); }, [days]);

  const cacheHitRate =
    stats && stats.cache.cache_hits !== undefined
      ? (() => {
          const total = (stats.cache.cache_hits ?? 0) + (stats.cache.cache_misses ?? 0);
          return total > 0 ? `${Math.round(((stats.cache.cache_hits ?? 0) / total) * 100)}%` : 'N/A';
        })()
      : 'N/A';

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Admin</h1>
            {stats && (
              <p className="text-xs text-base-content/50 mt-0.5">
                Tenant: <span className="font-mono">{stats.tenant_id}</span> · updated {new Date(stats.generated_at).toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="flex gap-2 items-center">
            <span className="text-xs opacity-60">Period:</span>
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                type="button"
                className={`btn btn-xs ${days === d ? 'btn-primary' : 'btn-ghost border border-base-300'}`}
                onClick={() => setDays(d)}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="alert alert-error text-sm py-2">
            <span>{error}</span>
          </div>
        )}

        {loading && (
          <div className="flex justify-center py-12">
            <span className="loading loading-spinner loading-md" />
          </div>
        )}

        {stats && !loading && (
          <>
            {/* KPI cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Active Components" value={stats.components.total_active} />
              <StatCard label="Pinned Apps" value={stats.active_pins} />
              <StatCard label="API Keys" value={stats.active_api_keys} />
              <StatCard label="Cache Hit Rate" value={cacheHitRate} sub="since last restart" />
            </div>

            {/* Generation trend */}
            <div className="bg-base-100 rounded-xl border border-base-300 shadow-sm p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">
                Components Generated (last {stats.period_days} days)
              </p>
              <MiniChart trend={stats.components.trend} />
              <div className="flex justify-between text-xs opacity-40 mt-1">
                {stats.components.trend.length > 0 && (
                  <>
                    <span>{stats.components.trend[0].date}</span>
                    <span>{stats.components.trend[stats.components.trend.length - 1].date}</span>
                  </>
                )}
              </div>
            </div>

            {/* Cache details */}
            {stats.cache.cache_hits !== undefined && (
              <div className="bg-base-100 rounded-xl border border-base-300 shadow-sm p-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-base-content/60 mb-3">Redis Cache</p>
                <div className="flex gap-8 text-sm">
                  <div>
                    <span className="text-base-content/50">Hits</span>
                    <span className="ml-2 font-bold">{stats.cache.cache_hits?.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-base-content/50">Misses</span>
                    <span className="ml-2 font-bold">{stats.cache.cache_misses?.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-base-content/50">Hit rate</span>
                    <span className="ml-2 font-bold">{cacheHitRate}</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
