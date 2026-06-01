"use client";

import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Zap, TrendingUp, Settings2 } from 'lucide-react';

export default function SimulatorPage() {
  const [runs, setRuns] = useState(150);
  const [balls, setBalls] = useState(30);
  const [wickets, setWickets] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [pressure, setPressure] = useState<number | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          runs_scored: runs,
          balls_remaining: balls,
          wickets_lost: wickets,
          n_simulations: 10000
        })
      });
      const data = await res.json();
      
      // Calculate pressure
      const pRes = await fetch("http://localhost:8000/stats/pressure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          innings: 1,
          par_score: 180,
          current_score: runs,
          wickets_lost: wickets,
          expected_runs_remaining: data.mean_runs - runs,
          runs_needed: 0
        })
      });
      const pData = await pRes.json();
      
      setResults(data);
      setPressure(pData.pressure_index);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  // Transform trajectory data for Recharts
  const chartData = [];
  if (results && results.trajectories) {
    const numPoints = results.trajectories[0].length;
    for (let i = 0; i < numPoints; i++) {
      const point: any = { over: i + 1 };
      // Just plot first 10 paths to avoid clutter
      for (let j = 0; j < Math.min(10, results.trajectories.length); j++) {
        point[`path${j}`] = results.trajectories[j][i];
      }
      chartData.push(point);
    }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400 flex items-center gap-3">
              <Activity className="w-8 h-8 text-blue-400" />
              CricMatrix Simulation Engine
            </h1>
            <p className="text-slate-400 mt-2">Vectorized Monte Carlo Predictor via Markov Decision Processes</p>
          </div>
          <button 
            onClick={runSimulation}
            disabled={loading}
            className="px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl font-bold hover:scale-105 transition-all shadow-[0_0_20px_rgba(59,130,246,0.5)] flex items-center gap-2"
          >
            {loading ? "Simulating 10,000 matches..." : <><Zap className="w-5 h-5" /> Execute Simulation</>}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Controls Sidebar */}
          <div className="lg:col-span-1 space-y-6 bg-[#1E293B] p-6 rounded-2xl border border-slate-700/50 shadow-xl">
            <h3 className="text-xl font-bold flex items-center gap-2 text-slate-200">
              <Settings2 className="w-5 h-5" /> Match State
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 block mb-2">Current Runs ({runs})</label>
                <input type="range" min="0" max="300" value={runs} onChange={e => setRuns(Number(e.target.value))} className="w-full accent-blue-500" />
              </div>
              
              <div>
                <label className="text-sm text-slate-400 block mb-2">Balls Remaining ({balls})</label>
                <input type="range" min="1" max="120" value={balls} onChange={e => setBalls(Number(e.target.value))} className="w-full accent-emerald-500" />
              </div>
              
              <div>
                <label className="text-sm text-slate-400 block mb-2">Wickets Lost ({wickets})</label>
                <input type="range" min="0" max="9" value={wickets} onChange={e => setWickets(Number(e.target.value))} className="w-full accent-rose-500" />
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-8">
            
            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-[#1E293B] p-6 rounded-2xl border border-slate-700/50 shadow-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                  <TrendingUp className="w-16 h-16" />
                </div>
                <h4 className="text-slate-400 text-sm font-medium">Expected Final Score</h4>
                <div className="text-4xl font-bold mt-2 text-blue-400">
                  {results ? Math.round(results.mean_runs) : "---"}
                </div>
                <div className="text-sm text-slate-500 mt-2">Median: {results ? Math.round(results.median_runs) : "--"}</div>
              </div>

              <div className="bg-[#1E293B] p-6 rounded-2xl border border-slate-700/50 shadow-xl relative overflow-hidden group">
                <h4 className="text-slate-400 text-sm font-medium">Projected Range (25th - 75th %ile)</h4>
                <div className="text-4xl font-bold mt-2 text-emerald-400">
                  {results ? `${Math.round(results.p25_runs)} - ${Math.round(results.p75_runs)}` : "---"}
                </div>
                <div className="text-sm text-slate-500 mt-2">10,000 Simulations via NumPy</div>
              </div>

              <div className="bg-[#1E293B] p-6 rounded-2xl border border-slate-700/50 shadow-xl relative overflow-hidden group">
                <h4 className="text-slate-400 text-sm font-medium">Contextual Pressure Index</h4>
                <div className="text-4xl font-bold mt-2 text-rose-400">
                  {pressure !== null ? pressure.toFixed(2) : "---"}
                </div>
                <div className="text-sm text-slate-500 mt-2">Phase 2 AI Metric</div>
              </div>
            </div>

            {/* Chart Area */}
            <div className="bg-[#1E293B] p-6 rounded-2xl border border-slate-700/50 shadow-xl h-[400px]">
              <h3 className="text-xl font-bold mb-6 text-slate-200">Monte Carlo Trajectories</h3>
              {results ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="over" stroke="#94A3B8" />
                    <YAxis stroke="#94A3B8" domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ backgroundColor: '#0F172A', border: '1px solid #334155' }} />
                    {/* Plot the first 10 paths softly */}
                    {[...Array(10)].map((_, i) => (
                      <Line key={i} type="monotone" dataKey={`path${i}`} stroke="#3B82F6" strokeWidth={2} opacity={0.3} dot={false} isAnimationActive={true} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-500">
                  Execute simulation to view probability distributions.
                </div>
              )}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
