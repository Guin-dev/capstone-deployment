'use client';

interface ViewControlsProps {
  displayMode: 'both' | 'mask' | 'detection';
  setDisplayMode: (mode: 'both' | 'mask' | 'detection') => void;
  viewMode: 'bev' | 'normal';
  setViewMode: (mode: 'bev' | 'normal') => void;
}

export default function ViewControls({
  displayMode,
  setDisplayMode,
  viewMode,
  setViewMode,
}: ViewControlsProps) {
  return (
    <div className="bento-card p-4 rounded-xl flex flex-wrap items-center gap-6">
      {/* Display Mode Selector */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-[var(--text-subtle)] uppercase tracking-wider">Tampilkan:</label>
        <div className="flex gap-2">
          <button
            onClick={() => setDisplayMode('both')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${displayMode === 'both'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--background)] text-[var(--text-muted)] hover:bg-[var(--border)]'
              }`}
          >
            Keduanya
          </button>
          <button
            onClick={() => setDisplayMode('mask')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${displayMode === 'mask'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--background)] text-[var(--text-muted)] hover:bg-[var(--border)]'
              }`}
          >
            Mask Saja
          </button>
          <button
            onClick={() => setDisplayMode('detection')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${displayMode === 'detection'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--background)] text-[var(--text-muted)] hover:bg-[var(--border)]'
              }`}
          >
            Deteksi Saja
          </button>
        </div>
      </div>

      {/* View Mode Selector */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-[var(--text-subtle)] uppercase tracking-wider">Mode View:</label>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('bev')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${viewMode === 'bev'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--background)] text-[var(--text-muted)] hover:bg-[var(--border)]'
              }`}
          >
            Bird Eye
          </button>
          <button
            onClick={() => setViewMode('normal')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${viewMode === 'normal'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--background)] text-[var(--text-muted)] hover:bg-[var(--border)]'
              }`}
          >
            Normal
          </button>
        </div>
      </div>
    </div>
  );
}

