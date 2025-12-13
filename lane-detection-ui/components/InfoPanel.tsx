'use client';

interface InfoPanelProps {
  status: any;
  isConnected: boolean;
}

export default function InfoPanel({ status, isConnected }: InfoPanelProps) {
  const metrics = [
    { label: 'Offset', value: status?.offset ?? 0, unit: 'px', highlight: true },
    { label: 'Gamma', value: status?.gamma?.toFixed(2) ?? '0.00', unit: '' },
    { label: 'Lux', value: status?.lux?.toFixed(0) ?? '0', unit: 'lx' },
    { label: 'FPS', value: status?.fps?.toFixed(0) ?? '0', unit: '' },
  ];

  return (
    <>
      {/* Primary Metric: Direction */}
      <div className="bento-card p-6 rounded-2xl flex flex-col justify-between h-40 relative overflow-hidden group">
        <div className="relative z-10">
          <span className="text-xs text-[var(--text-subtle)] font-mono uppercase tracking-widest">Vehicle Status</span>
          <h2 className="text-3xl font-medium text-[var(--foreground)] mt-1">
            {isConnected ? (status?.arah || 'HOLD') : '---'}
          </h2>
        </div>

        {/* Dynamic decorative element */}
        <div className={`absolute right-4 top-1/2 -translate-y-1/2 w-24 h-24 rounded-full blur-[60px] opacity-20 transition-colors duration-700 
            ${status?.arah === 'TENGAH' ? 'bg-emerald-500' : status?.arah === 'KIRI' || status?.arah === 'KANAN' ? 'bg-amber-500' : 'bg-neutral-500'}`}
        />

        <div className="relative z-10 flex items-center gap-2 mt-auto">
          <div className="text-xs text-[var(--text-muted)] bg-[var(--background)] px-2 py-1 rounded border border-[var(--border)]">
            {isConnected ? 'ACTIVE' : 'STANDBY'}
          </div>
        </div>
      </div>

      {/* Metric Grid */}
      <div className="grid grid-cols-2 gap-4 flex-1">
        {metrics.map((m, i) => (
          <div key={i} className="bento-card p-4 rounded-xl flex flex-col justify-between min-h-[100px] hover:bg-[var(--background)] transition-colors">
            <span className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wider">{m.label}</span>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-light tracking-tight ${m.highlight ? 'text-[var(--foreground)]' : 'text-[var(--text-muted)]'}`}>
                {m.value}
              </span>
              <span className="text-xs text-[var(--text-subtle)] font-medium">{m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* System Log / Debug - Minimal */}
      <div className="bento-card p-4 rounded-xl flex-1 min-h-[120px] flex flex-col">
        <span className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wider mb-2">System Metrics</span>
        <div className="flex-1 py-1 space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-[var(--text-subtle)]">Brightness</span>
            <span className="text-[var(--text-muted)] font-mono">{status?.brightness?.toFixed(1) ?? '0.0'}%</span>
          </div>
          <div className="w-full bg-[var(--background)] h-1 rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--accent)] transition-all duration-500"
              style={{ width: `${Math.min(status?.brightness ?? 0, 100)}%` }}
            />
          </div>

          <div className="flex justify-between items-center text-xs mt-3">
            <span className="text-[var(--text-subtle)]">Latency</span>
            <span className="text-green-500/80 font-mono">~10 ms</span>
          </div>
        </div>
      </div>
    </>
  );
}

