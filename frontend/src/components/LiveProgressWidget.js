"use client";
import { useState, useEffect } from "react";

export default function LiveProgressWidget() {
  const [metrics, setMetrics] = useState({
    total: 323000,
    completed: 0,
    speed_hr: 0,
    speed_min: 0,
    speed_sec: 0,
    recent: []
  });
  
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    let initialCompleted = -1;
    let initialTime = Date.now();

    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/system/status");
        if (res.ok) {
          const data = await res.json();
          const currentCompleted = data.database.completed_extractions || 0;
          const currentTotal = data.database.total_matches || 323000;
          const recentExtractions = data.recent_extractions || [];
          
          if (initialCompleted === -1) {
            initialCompleted = currentCompleted;
            initialTime = Date.now();
          }

          const now = Date.now();
          const elapsedSeconds = (now - initialTime) / 1000;
          
          let hr = metrics.speed_hr;
          let min = metrics.speed_min;
          let sec = metrics.speed_sec;

          // Only calculate speed if at least 10 seconds have passed to build a stable average
          if (elapsedSeconds >= 10 && currentCompleted > initialCompleted) {
            const diffMatches = currentCompleted - initialCompleted;
            sec = diffMatches / elapsedSeconds;
            min = sec * 60;
            hr = min * 60;
          }
          
          setMetrics(prev => ({
            total: currentTotal,
            completed: currentCompleted,
            speed_hr: hr > 0 ? Math.round(hr) : prev.speed_hr,
            speed_min: min > 0 ? Math.round(min) : prev.speed_min,
            speed_sec: sec > 0 ? Number(sec).toFixed(1) : prev.speed_sec,
            recent: recentExtractions
          }));
          
          setIsLive(true);
        }
      } catch (e) {
        setIsLive(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const percentage = metrics.total > 0 ? ((metrics.completed / metrics.total) * 100).toFixed(2) : 0;
  const remaining = metrics.total - metrics.completed;
  
  let etaString = "Calculating...";
  if (metrics.speed_hr > 0) {
    const hoursRemaining = remaining / metrics.speed_hr;
    if (hoursRemaining < 1) {
      etaString = `${Math.round(hoursRemaining * 60)} mins`;
    } else {
      etaString = `${hoursRemaining.toFixed(1)} hrs`;
    }
  }

  // Ticker items
  const tickerItems = [...metrics.recent, ...metrics.recent, ...metrics.recent];

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl mb-8 flex flex-col">
      <div className="bg-zinc-800/50 px-6 py-4 flex justify-between items-center border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold tracking-widest text-emerald-500 uppercase">Live Database Extraction</span>
          {isLive && (
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          )}
        </div>
        <span className="text-xs font-mono text-zinc-500">POLL_RATE: 3s</span>
      </div>
      
      <div className="p-6">
        <div className="mb-2 flex justify-between items-end">
          <span className="text-3xl font-black tracking-tight text-white">{percentage}%</span>
          <span className="text-sm text-zinc-400 font-medium">{metrics.completed.toLocaleString()} / {metrics.total.toLocaleString()}</span>
        </div>
        
        <div className="w-full bg-zinc-800 rounded-full h-3 mb-6 overflow-hidden shadow-inner">
          <div 
            className="bg-gradient-to-r from-emerald-600 to-emerald-400 h-3 rounded-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(52,211,153,0.5)]" 
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
        
        {/* Telemetry Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-zinc-950/50 rounded-lg p-4 border border-zinc-800/50">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">Scorecards Left</p>
            <p className="text-xl font-mono text-zinc-200">{remaining.toLocaleString()}</p>
          </div>
          
          <div className="bg-zinc-950/50 rounded-lg p-4 border border-zinc-800/50">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">Speed (Hr)</p>
            <p className="text-xl font-mono text-emerald-400">
              {metrics.speed_hr > 0 ? metrics.speed_hr.toLocaleString() : "..."} <span className="text-xs text-emerald-600 font-sans">/hr</span>
            </p>
          </div>

          <div className="bg-zinc-950/50 rounded-lg p-4 border border-zinc-800/50">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">Speed (Min/Sec)</p>
            <p className="text-xl font-mono text-emerald-400">
              {metrics.speed_min > 0 ? metrics.speed_min.toLocaleString() : "..."} <span className="text-xs text-emerald-600 font-sans">/m</span>
              <span className="text-zinc-600 mx-2">|</span>
              {metrics.speed_sec > 0 ? metrics.speed_sec : "..."} <span className="text-xs text-emerald-600 font-sans">/s</span>
            </p>
          </div>
          
          <div className="bg-zinc-950/50 rounded-lg p-4 border border-zinc-800/50">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">ETA</p>
            <p className="text-xl font-mono text-blue-400">{etaString}</p>
          </div>
        </div>
      </div>

      {/* Stock Market Ticker Footer */}
      <div className="bg-zinc-950 border-t border-zinc-800 overflow-hidden relative h-12 flex items-center">
        <div className="absolute left-0 z-10 h-full w-24 bg-gradient-to-r from-zinc-950 to-transparent pointer-events-none"></div>
        
        {metrics.recent.length > 0 ? (
           <div className="w-full h-full overflow-hidden whitespace-nowrap block absolute">
             <div className="animate-marquee h-full inline-flex items-center gap-12 pl-12 pr-12">
               {tickerItems.map((match, idx) => (
                 <div key={idx} className="inline-flex items-center text-sm font-mono text-zinc-400 shrink-0">
                   <span className="text-emerald-500 mr-2">◆</span>
                   {match}
                 </div>
               ))}
             </div>
           </div>
        ) : (
          <div className="px-6 text-xs font-mono text-zinc-600 italic">Waiting for incoming extractions...</div>
        )}
        
        <div className="absolute right-0 z-10 h-full w-24 bg-gradient-to-l from-zinc-950 to-transparent pointer-events-none"></div>
      </div>
    </div>
  );
}
