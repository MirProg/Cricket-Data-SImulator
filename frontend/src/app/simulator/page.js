"use client";
import { useState } from "react";

export default function Home() {
  const [teamA, setTeamA] = useState("India");
  const [teamB, setTeamB] = useState("Australia");
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const res = await fetch("http://localhost:8000/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ team_a: teamA, team_b: teamB }),
      });
      if (!res.ok) throw new Error("Failed to fetch prediction");
      const data = await res.json();
      setPrediction(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const teams = [
    "India", "Australia", "England", "South Africa", 
    "New Zealand", "Pakistan", "Sri Lanka", "West Indies", 
    "Bangladesh", "Afghanistan"
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      
      {/* Background gradients */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-600/20 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-emerald-600/10 rounded-full blur-[120px] translate-y-1/2 -translate-x-1/2 pointer-events-none"></div>

      <div className="z-10 max-w-4xl w-full flex flex-col gap-10">
        
        {/* Header */}
        <div className="text-center animate-in fade-in slide-in-from-top-8 duration-1000">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400">
            AI Cricket Predictor
          </h1>
          <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto">
            Powered by PyTorch Transformers. Simulate match outcomes and top performer stats using 900,000+ historical records.
          </p>
        </div>

        {/* Main Glass Panel */}
        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 md:p-12 shadow-2xl hover:-translate-y-1 transition-all duration-500 ease-out animate-in fade-in zoom-in-95 duration-1000 delay-150 fill-mode-both">
          
          <div className="flex flex-col md:flex-row gap-6 md:gap-10 items-center justify-between mb-10">
            
            <div className="w-full flex flex-col gap-2">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Team A</label>
              <select 
                value={teamA} 
                onChange={(e) => setTeamA(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700 text-slate-200 p-4 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all appearance-none cursor-pointer"
              >
                {teams.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="text-2xl font-black text-slate-600 italic px-4">VS</div>

            <div className="w-full flex flex-col gap-2">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Team B</label>
              <select 
                value={teamB} 
                onChange={(e) => setTeamB(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700 text-slate-200 p-4 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all appearance-none cursor-pointer"
              >
                {teams.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            
          </div>

          <button 
            onClick={handlePredict}
            disabled={loading || teamA === teamB}
            className={`w-full py-4 rounded-xl text-lg font-bold transition-all duration-300 shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)] ${
              loading || teamA === teamB ? "bg-slate-700 text-slate-400 cursor-not-allowed shadow-none hover:shadow-none" : "bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:scale-[1.01]"
            }`}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-3">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Analyzing Model Sequences...
              </div>
            ) : "Simulate Match"}
          </button>

          {error && (
            <div className="mt-6 p-4 bg-red-900/30 border border-red-500/30 text-red-400 rounded-xl text-center">
              {error}
            </div>
          )}

        </div>

        {/* Results Panel */}
        {prediction && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-10 duration-700 ease-out">
            <div className="bg-slate-800/50 backdrop-blur-xl border border-emerald-500/30 rounded-2xl p-8 text-center flex flex-col justify-center shadow-[0_0_40px_rgba(16,185,129,0.1)]">
              <h3 className="text-emerald-400/80 text-sm font-bold uppercase tracking-widest mb-2">Predicted Winner</h3>
              <div className="text-4xl md:text-5xl font-black text-emerald-400 mb-2">{prediction.winner}</div>
              <div className="text-slate-300 text-lg">Win Probability: <span className="font-bold text-white">{prediction.win_probability}%</span></div>
            </div>
            
            <div className="bg-slate-800/50 backdrop-blur-xl border border-purple-500/30 rounded-2xl p-8 text-center flex flex-col justify-center shadow-[0_0_40px_rgba(168,85,247,0.1)]">
              <h3 className="text-purple-400/80 text-sm font-bold uppercase tracking-widest mb-2">Top Performer Stat</h3>
              <div className="text-4xl md:text-5xl font-black text-purple-400 mb-2">{prediction.top_batsman_runs} Runs</div>
              <div className="text-slate-300 text-lg">Predicted Highest Individual Score</div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
