"use client";
import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { Activity, TrendingUp, AlertTriangle } from "lucide-react";

export default function Simulator() {
  const [runs, setRuns] = useState(0);
  const [wickets, setWickets] = useState(0);
  const [balls, setBalls] = useState(120);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [chartData, setChartData] = useState([]);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          runs_scored: runs,
          wickets_lost: wickets,
          balls_remaining: balls,
          n_simulations: 1000
        }),
      });
      if (!res.ok) throw new Error("Simulation failed");
      const data = await res.json();
      setResults(data);
      
      // Format trajectories for Recharts
      // trajectories is an array of 100 lists, each containing runs at the end of each remaining over
      const formattedData = [];
      const numOvers = data.trajectories[0].length;
      const startOver = 20 - (balls / 6);
      
      for (let i = 0; i < numOvers; i++) {
        let overData = { name: `Over ${Math.floor(startOver + i)}` };
        // Just plot 20 sample paths to avoid overloading the DOM
        for (let j = 0; j < Math.min(20, data.trajectories.length); j++) {
          overData[`sim${j}`] = data.trajectories[j][i];
        }
        formattedData.push(overData);
      }
      setChartData(formattedData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center gap-4 border-b border-slate-800 pb-6">
          <Activity className="w-10 h-10 text-blue-500" />
          <div>
            <h1 className="text-4xl font-black bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Live Monte Carlo Simulator
            </h1>
            <p className="text-slate-400 mt-1">
              Data-driven projections powered by 3.5 Million empirical ball-by-ball transitions.
            </p>
          </div>
        </div>

        {/* Input Panel */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-400 uppercase tracking-widest">Current Runs</label>
            <input 
              type="number" 
              value={runs} 
              onChange={e => setRuns(parseInt(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-xl font-bold focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-400 uppercase tracking-widest">Wickets Lost</label>
            <input 
              type="number" 
              value={wickets} 
              max="10"
              onChange={e => setWickets(parseInt(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-xl font-bold focus:ring-2 focus:ring-red-500 outline-none"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-400 uppercase tracking-widest">Balls Remaining</label>
            <input 
              type="number" 
              value={balls} 
              max="120"
              onChange={e => setBalls(parseInt(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-xl font-bold focus:ring-2 focus:ring-emerald-500 outline-none"
            />
          </div>
          
          <div className="md:col-span-3 pt-2">
            <button 
              onClick={handleSimulate}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-lg py-4 rounded-xl transition-all shadow-[0_0_15px_rgba(59,130,246,0.3)]"
            >
              {loading ? "Computing 1,000 Universes..." : "Execute Simulation"}
            </button>
          </div>
        </div>

        {/* Results */}
        {results && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
            
            {/* Metrics Sidebar */}
            <div className="lg:col-span-1 space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center shadow-lg relative overflow-hidden">
                <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-emerald-400 to-emerald-600 left-0"></div>
                <h3 className="text-slate-400 font-bold uppercase tracking-wider text-xs mb-2">Expected Final Score</h3>
                <div className="text-5xl font-black text-white">{Math.round(results.mean_runs)}</div>
                <div className="text-emerald-400 text-sm font-semibold mt-2 flex items-center justify-center gap-1">
                  <TrendingUp className="w-4 h-4" /> Median: {Math.round(results.median_runs)}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center shadow-lg relative overflow-hidden">
                <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-red-400 to-red-600 left-0"></div>
                <h3 className="text-slate-400 font-bold uppercase tracking-wider text-xs mb-2">Expected Wickets</h3>
                <div className="text-4xl font-black text-red-400">{results.mean_wickets.toFixed(1)}</div>
                <div className="text-red-500/80 text-sm font-semibold mt-2 flex items-center justify-center gap-1">
                  <AlertTriangle className="w-4 h-4" /> Max 10
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
                <h3 className="text-slate-400 font-bold uppercase tracking-wider text-xs mb-4 border-b border-slate-800 pb-2">Percentiles</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">90th (Best Case)</span>
                    <span className="text-emerald-400 font-bold">{Math.round(results.p90_runs)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">75th (Good)</span>
                    <span className="text-blue-400 font-bold">{Math.round(results.p75_runs)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">25th (Worst Case)</span>
                    <span className="text-red-400 font-bold">{Math.round(results.p25_runs)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Chart Area */}
            <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
              <h3 className="text-slate-200 font-bold text-lg mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" />
                Win Probability Cone (20 Sample Trajectories)
              </h3>
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis 
                      dataKey="name" 
                      stroke="#64748b" 
                      tick={{ fill: '#64748b', fontSize: 12 }} 
                      tickLine={false}
                    />
                    <YAxis 
                      stroke="#64748b" 
                      tick={{ fill: '#64748b', fontSize: 12 }} 
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                      itemStyle={{ color: '#94a3b8' }}
                      labelStyle={{ color: '#f8fafc', fontWeight: 'bold', marginBottom: '8px' }}
                    />
                    <ReferenceLine y={results.mean_runs} stroke="#3b82f6" strokeDasharray="3 3" label={{ position: 'top', value: 'Expected', fill: '#3b82f6', fontSize: 12 }} />
                    
                    {/* Render 20 individual trajectory lines with low opacity */}
                    {Object.keys(chartData[0] || {}).filter(k => k.startsWith('sim')).map((key, i) => (
                      <Line 
                        key={key} 
                        type="monotone" 
                        dataKey={key} 
                        stroke="#6366f1" 
                        strokeWidth={1.5} 
                        dot={false} 
                        opacity={0.15} 
                        isAnimationActive={true}
                        animationDuration={2000}
                        animationBegin={i * 50}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
