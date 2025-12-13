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
        className="text-xs text-neutral-500 hover:text-white transition-colors uppercase tracking-wider font-medium"
      >
        {isOpen ? 'Close' : 'Configure'}
      </button>

      {isOpen && (
        <div className="absolute top-8 right-0 w-64 bg-[#0a0a0a] border border-[#1f1f1f] rounded-xl p-4 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          <label className="text-[10px] uppercase tracking-widest text-neutral-500 block mb-2">Device IP Address</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={tempIp}
              onChange={(e) => setTempIp(e.target.value)}
              className="flex-1 bg-[#151515] border border-[#2a2a2a] rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30 font-mono"
            />
            <button
              onClick={() => {
                setPiIp(tempIp);
                setIsOpen(false);
              }}
              className="bg-white text-black px-3 py-1.5 rounded text-xs font-medium hover:bg-neutral-200 transition-colors"
            >
              Set
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
