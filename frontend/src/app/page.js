"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function DatabaseHome() {
  const [matches, setMatches] = useState([]);
  const [topBatsmen, setTopBatsmen] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("recent");

  useEffect(() => {
    const fetchDbData = async () => {
      setLoading(true);
      try {
        const [matchesRes, batsmenRes] = await Promise.all([
          fetch(`http://localhost:8000/api/matches?limit=12&category=${activeCategory}`),
          fetch("http://localhost:8000/api/records")
        ]);
        
        if (matchesRes.ok) setMatches(await matchesRes.json());
        if (batsmenRes.ok) {
           const records = await batsmenRes.json();
           setTopBatsmen(records.top_run_scorers || []);
        }
      } catch (err) {
        console.error("Failed to fetch DB data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDbData();
  }, [activeCategory]);

  return (
    <div className="py-8 px-4 sm:px-0">
      {/* Header */}
      <div className="mb-8 border-b border-gray-200 pb-6">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">Global Cricket Archive</h1>
        <p className="text-gray-500 mt-2 text-lg">Explore the complete database of historical matches and dynamic statistics.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        
        {/* Main Feed: Recent Matches */}
        <div className="lg:col-span-2">
          
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 gap-4">
            <h2 className="text-2xl font-bold text-gray-800">Match Feed</h2>
            
            {/* Category Navigator */}
            <div className="flex bg-gray-100 p-1 rounded-lg shadow-inner">
              <button 
                onClick={() => setActiveCategory("recent")}
                className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-all ${activeCategory === "recent" ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
              >
                All Recent
              </button>
              <button 
                onClick={() => setActiveCategory("international")}
                className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-all ${activeCategory === "international" ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
              >
                International
              </button>
              <button 
                onClick={() => setActiveCategory("domestic")}
                className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-all ${activeCategory === "domestic" ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
              >
                Domestic Leagues
              </button>
            </div>
          </div>

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5, 6].map(i => <div key={i} className="h-32 bg-gray-200 animate-pulse rounded-xl"></div>)}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {matches.map((match) => (
                <Link key={match.match_id} href={`/match/${match.match_id}`} className="block bg-white border border-gray-200 rounded-xl p-5 hover:shadow-lg transition-all group hover:border-blue-300">
                  <div className="flex justify-between items-center mb-3">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${match.match_category === 'International' ? 'bg-indigo-100 text-indigo-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {match.match_format || match.format} &bull; {match.match_category || "Domestic"}
                    </span>
                    <span className="text-xs text-gray-400 truncate ml-2 font-medium">{match.date}</span>
                  </div>
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between font-bold text-gray-900 text-sm">
                      <span>{match.team1_name}</span>
                      {match.winner_name === match.team1_name && <span className="text-blue-600 text-[10px] uppercase tracking-wider bg-blue-50 px-2 py-0.5 rounded">Winner</span>}
                    </div>
                    <div className="flex justify-between font-bold text-gray-900 text-sm">
                      <span>{match.team2_name}</span>
                      {match.winner_name === match.team2_name && <span className="text-blue-600 text-[10px] uppercase tracking-wider bg-blue-50 px-2 py-0.5 rounded">Winner</span>}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 border-t border-gray-100 pt-3 flex justify-between items-center">
                    <span className="truncate pr-2">{match.winner_name} won</span>
                    <span className="text-blue-600 font-semibold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Scorecard &rarr;</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Global Records */}
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 shadow-xl text-white">
            <div className="flex justify-between items-center mb-6 border-b border-slate-700 pb-3">
              <h3 className="text-lg font-bold tracking-wide">Live AI Calculations</h3>
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            </div>
            
            <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-4">Highest Career Runs</h4>
            
            {loading && topBatsmen.length === 0 ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-8 bg-slate-700 animate-pulse rounded"></div>)}
              </div>
            ) : (
              <div className="divide-y divide-slate-700/50">
                {topBatsmen.map((batsman, idx) => (
                  <div key={idx} className="py-2.5 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="text-slate-500 font-mono text-xs w-4">{idx + 1}</span>
                      <div>
                        <Link href={`/player/${batsman.name}`} className="font-semibold hover:text-blue-400 transition-colors text-sm">
                          {batsman.name}
                        </Link>
                      </div>
                    </div>
                    <div className="font-mono font-bold text-emerald-400 text-sm">
                      {batsman.bat_runs.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <Link href="/records" className="block text-center w-full mt-6 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm font-medium transition-colors text-blue-300 hover:text-blue-200 shadow-inner">
              Explore All Records &rarr;
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
