'use client';

import { useState, useEffect } from 'react';

interface VideoPlayerProps {
  piIp: string;
  isConnected: boolean;
  displayMode: 'both' | 'mask' | 'detection';
  viewMode: 'bev' | 'normal';
}

export default function VideoPlayer({ piIp, isConnected, displayMode, viewMode }: VideoPlayerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [key, setKey] = useState(0);

  useEffect(() => {
    setKey(prev => prev + 1);
  }, [displayMode, viewMode]);

  const toggleFullscreen = () => {
    const el = document.getElementById('video-container');
    if (!el) return;
    if (!isFullscreen) el.requestFullscreen?.();
    else document.exitFullscreen?.();
    setIsFullscreen(!isFullscreen);
  };

  if (!isConnected) {
    return (
      <div className="bento-card w-full h-full rounded-2xl overflow-hidden flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-[var(--text-subtle)]">
          <div className="w-12 h-12 border-2 border-[var(--border)] border-t-[var(--accent)] rounded-full animate-spin"></div>
          <p className="text-xs font-mono uppercase tracking-widest">Signal Lost</p>
        </div>
      </div>
    );
  }

  const getUrl = (type: string) => `http://${piIp}:5000/video_feed?type=${type}&mode=${viewMode}`;

  return (
    <div id="video-container" className="bento-card w-full h-full rounded-2xl overflow-hidden relative group flex flex-col">
      <div className="absolute top-0 left-0 right-0 p-4 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-b from-black/50 to-transparent flex justify-between items-start pointer-events-none">
        <div className="bg-black/40 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></span>
          <span className="text-[10px] font-mono text-white/80">LIVE • {viewMode.toUpperCase()}</span>
        </div>
        <button onClick={toggleFullscreen} className="pointer-events-auto bg-white/10 hover:bg-white/20 p-2 rounded-lg backdrop-blur-md transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white">
            <path d="M15 3h6v6" /><path d="M9 21H3v-6" /><path d="M21 3l-7 7" /><path d="M3 21l7-7" />
          </svg>
        </button>
      </div>

      <div className="flex-1 bg-[var(--background)] relative flex items-center justify-center p-4">
        {displayMode === 'both' ? (
          <div className="grid grid-cols-2 gap-4 w-full h-full">
            <div className="relative flex items-center justify-center bg-black rounded-lg overflow-hidden">
              <img key={`mask-${key}`} src={getUrl('mask')} alt="Mask" className="max-w-full max-h-full object-contain" />
              <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-[10px] text-white/80">MASK</div>
            </div>
            <div className="relative flex items-center justify-center bg-black rounded-lg overflow-hidden">
              <img key={`det-${key}`} src={getUrl('detection')} alt="Detection" className="max-w-full max-h-full object-contain" />
              <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-[10px] text-white/80">DETECTION</div>
            </div>
          </div>
        ) : (
          <img key={`single-${displayMode}-${viewMode}-${key}`} src={getUrl(displayMode)} alt="Stream" className="max-w-full max-h-full object-contain rounded-lg" />
        )}
      </div>

      <div className="absolute inset-0 border border-[var(--border)] pointer-events-none rounded-2xl"></div>
    </div>
  );
}

