'use client';

import { useState, useEffect } from 'react';
import VideoPlayer from '@/components/VideoPlayer';
import InfoPanel from '@/components/InfoPanel';
import SettingsPanel from '@/components/SettingsPanel';
import ViewControls from '@/components/ViewControls';

export default function Home() {
  const [piIp, setPiIp] = useState('172.20.10.2');
  const [status, setStatus] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // View controls state (sama seperti Tkinter version)
  const [displayMode, setDisplayMode] = useState<'both' | 'mask' | 'detection'>('both');
  const [viewMode, setViewMode] = useState<'bev' | 'normal'>('bev');

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`http://${piIp}:5000/api/status`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
          setIsConnected(true);
        } else {
          setIsConnected(false);
        }
      } catch (error) {
        setIsConnected(false);
      }
    };
    const interval = setInterval(fetchStatus, 500);
    return () => clearInterval(interval);
  }, [piIp]);

  return (
    <main className="min-h-screen p-4 md:p-8 flex flex-col gap-4 max-w-[1600px] mx-auto">
      {/* Top Bar */}
      <header className="flex justify-between items-end pb-4 border-b border-white/5">
        <div>
          <h1 className="text-xl font-medium tracking-tight text-white">Caluna</h1>
          <p className="text-xs text-neutral-500 uppercase tracking-widest mt-1">Vision System v1.0</p>
        </div>
        <div className="flex items-center gap-4">
          <SettingsPanel piIp={piIp} setPiIp={setPiIp} />
          <div className="flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/5">
            <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-rose-500'} transition-all duration-500`} />
            <span className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
              {isConnected ? 'System Online' : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* View Controls - Sama seperti Tkinter */}
      <ViewControls 
        displayMode={displayMode}
        setDisplayMode={setDisplayMode}
        viewMode={viewMode}
        setViewMode={setViewMode}
      />

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 h-[calc(100vh-220px)] min-h-[600px]">
        <div className="lg:col-span-9 flex flex-col">
          <VideoPlayer 
            piIp={piIp} 
            isConnected={isConnected}
            displayMode={displayMode}
            viewMode={viewMode}
          />
        </div>

        <div className="lg:col-span-3 flex flex-col gap-4">
          <InfoPanel status={status} isConnected={isConnected} />
        </div>
      </div>
    </main>
  );
}
