'use client';

import { useState } from 'react';

interface SettingsPanelProps {
  piIp: string;
  setPiIp: (ip: string) => void;
}

export default function SettingsPanel({ piIp, setPiIp }: SettingsPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [tempIp, setTempIp] = useState(piIp);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-xs text-[var(--text-subtle)] hover:text-[var(--foreground)] transition-colors uppercase tracking-wider font-medium"
      >
        {isOpen ? 'Close' : 'Configure'}
      </button>

      {isOpen && (
        <div className="absolute top-8 right-0 w-64 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          <label className="text-[10px] uppercase tracking-widest text-[var(--text-subtle)] block mb-2">Device IP Address</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={tempIp}
              onChange={(e) => setTempIp(e.target.value)}
              className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded px-3 py-1.5 text-xs text-[var(--foreground)] focus:outline-none focus:border-[var(--accent)] font-mono"
            />
            <button
              onClick={() => {
                setPiIp(tempIp);
                setIsOpen(false);
              }}
              className="bg-[var(--accent)] text-white px-3 py-1.5 rounded text-xs font-medium hover:opacity-90 transition-opacity"
            >
              Set
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

