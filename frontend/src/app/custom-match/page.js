"use client";
import { useState } from "react";
import { Play, Trophy, Users, Loader2 } from "lucide-react";

const CLASSIC_INDIA = [
  "RG Sharma", "V Kohli", "SA Yadav", "RR Pant", "HH Pandya", 
  "RA Jadeja", "AR Patel", "R Ashwin", "B Kumar", "JJ Bumrah", "Mohammed Shami"
];

const CLASSIC_AUS = [
  "DA Warner", "TM Head", "MR Marsh", "GJ Maxwell", "MP Stoinis", 
  "TH David", "MS Wade", "PJ Cummins", "MA Starc", "A Zampa", "JR Hazlewood"
];

export default function CustomMatchSimulator() {
  const [team1, setTeam1] = useState(CLASSIC_INDIA.join("\n"));
  const [team2, setTeam2] = useState(CLASSIC_AUS.join("\n"));
  const [venue, setVenue] = useState("MCG, Melbourne");
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/simulate_match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team1: team1.split("\n").map(s => s.trim()).filter(Boolean),
          team2: team2.split("\n").map(s => s.trim()).filter(Boolean),
          venue
        })
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const renderInnings = (inn, teamName) => (
    <div className="bg-white border rounded-xl overflow-hidden shadow-sm mb-8">
      <div className="bg-slate-800 text-white p-4 font-bold flex justify-between items-center">
        <span>{teamName} Innings</span>
        <span className="text-xl">{inn.total_runs}/{inn.total_wickets} <span className="text-sm font-normal text-slate-300">({inn.overs} ov)</span></span>
      </div>
      
      {/* Batting Card */}
      <table className="w-full text-sm text-left">
        <thead className="bg-slate-50 text-slate-500 uppercase font-bold text-xs">
          <tr>
            <th className="px-4 py-3">Batter</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3 text-right">R</th>
            <th className="px-4 py-3 text-right">B</th>
            <th className="px-4 py-3 text-right">4s</th>
            <th className="px-4 py-3 text-right">6s</th>
            <th className="px-4 py-3 text-right">SR</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {Object.entries(inn.scorecard.batting).map(([player, stats]) => (
            stats.balls > 0 && (
              <tr key={player} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-semibold text-blue-700">{player}</td>
                <td className="px-4 py-3 text-slate-500 text-xs">
                  {stats.out ? `b ${stats.bowler}` : "not out"}
                </td>
                <td className="px-4 py-3 text-right font-bold">{stats.runs}</td>
                <td className="px-4 py-3 text-right">{stats.balls}</td>
                <td className="px-4 py-3 text-right">{stats["4s"]}</td>
                <td className="px-4 py-3 text-right">{stats["6s"]}</td>
                <td className="px-4 py-3 text-right">{(stats.runs / stats.balls * 100).toFixed(2)}</td>
              </tr>
            )
          ))}
        </tbody>
      </table>

      {/* Fall of Wickets */}
      <div className="p-4 bg-slate-50 border-t text-sm">
        <span className="font-bold text-slate-600 mr-2">Fall of wickets:</span>
        <span className="text-slate-600">{inn.scorecard.fall_of_wickets.join(", ")}</span>
      </div>

      {/* Bowling Card */}
      <table className="w-full text-sm text-left border-t border-slate-200">
        <thead className="bg-slate-50 text-slate-500 uppercase font-bold text-xs">
          <tr>
            <th className="px-4 py-3">Bowler</th>
            <th className="px-4 py-3 text-right">O</th>
            <th className="px-4 py-3 text-right">R</th>
            <th className="px-4 py-3 text-right">W</th>
            <th className="px-4 py-3 text-right">ECON</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {Object.entries(inn.scorecard.bowling).map(([player, stats]) => (
            stats.overs > 0 && (
              <tr key={player} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-semibold text-blue-700">{player}</td>
                <td className="px-4 py-3 text-right">{stats.overs}</td>
                <td className="px-4 py-3 text-right">{stats.runs}</td>
                <td className="px-4 py-3 text-right font-bold">{stats.wickets}</td>
                <td className="px-4 py-3 text-right">{(stats.runs / (stats.balls/6 || 1)).toFixed(2)}</td>
              </tr>
            )
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 p-8 text-slate-900">
      <div className="max-w-5xl mx-auto space-y-6">
        
        <div className="flex items-center gap-3">
          <Trophy className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-black text-slate-800">Custom Match Simulator</h1>
        </div>
        <p className="text-slate-500">
          Simulate a full T20 match ball-by-ball. The AI dynamically calculates outcomes using empirical career stats for every batter vs bowler matchup.
        </p>

        {!result ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-2xl shadow-sm border">
            <div>
              <label className="font-bold flex items-center gap-2 mb-2 text-slate-700">
                <Users className="w-4 h-4 text-blue-500" /> Team 1 Lineup (1-11)
              </label>
              <textarea 
                rows={12} 
                className="w-full border rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                value={team1}
                onChange={e => setTeam1(e.target.value)}
              />
            </div>
            <div>
              <label className="font-bold flex items-center gap-2 mb-2 text-slate-700">
                <Users className="w-4 h-4 text-emerald-500" /> Team 2 Lineup (1-11)
              </label>
              <textarea 
                rows={12} 
                className="w-full border rounded-lg p-3 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
                value={team2}
                onChange={e => setTeam2(e.target.value)}
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="font-bold block mb-2 text-slate-700">Venue</label>
              <input 
                type="text" 
                className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500 outline-none"
                value={venue}
                onChange={e => setVenue(e.target.value)}
              />
            </div>
            
            <div className="md:col-span-2 mt-4">
              <button 
                onClick={handleSimulate}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg transition-all"
              >
                {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Play className="w-6 h-6 fill-current" />}
                {loading ? "Simulating 240 Deliveries..." : "PLAY MATCH"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="bg-gradient-to-r from-blue-900 to-slate-900 text-white rounded-2xl p-8 shadow-xl text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 p-16 bg-blue-500/10 rounded-full blur-3xl"></div>
              <div className="text-sm font-bold text-blue-300 uppercase tracking-widest mb-2">{venue}</div>
              <h2 className="text-4xl font-black mb-4">RESULT</h2>
              <div className="text-xl text-slate-300 font-semibold mb-6">
                Team 1 scored {result.team1_innings.total_runs} <span className="mx-4">|</span> Team 2 scored {result.team2_innings.total_runs}
              </div>
              <div className="inline-block bg-blue-500 text-white font-black text-2xl px-8 py-3 rounded-full shadow-[0_0_20px_rgba(59,130,246,0.5)]">
                {result.winner} WON
              </div>
              <button 
                onClick={() => setResult(null)} 
                className="block mx-auto mt-8 text-sm text-slate-400 hover:text-white transition-colors"
              >
                ← Simulate Another Match
              </button>
            </div>

            {renderInnings(result.team1_innings, "Team 1")}
            {renderInnings(result.team2_innings, "Team 2")}
          </div>
        )}
      </div>
    </div>
  );
}
