"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function DatabaseHome() {
  const [matches, setMatches] = useState([]);
  const [topBatsmen, setTopBatsmen] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDbData = async () => {
      try {
        const [matchesRes, batsmenRes] = await Promise.all([
          fetch("http://localhost:8000/api/matches?limit=12"),
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
  }, []);

  return (
    <div className="py-8 px-4 sm:px-0">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-gray-900">Global Cricket Archive</h1>
        <p className="text-gray-600 mt-2">Explore over 900,000 matches and millions of player statistics.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Main Feed: Recent Matches */}
        <div className="lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-800">Recent Scorecards</h2>
            <Link href="/records" className="text-blue-600 text-sm font-semibold hover:underline">View All &rarr;</Link>
          </div>

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-gray-200 animate-pulse rounded-md"></div>)}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {matches.map((match) => (
                <Link key={match.match_id} href={`/match/${match.match_id}`} className="block bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow group">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-gray-500 bg-gray-100 px-2 py-1 rounded">{match.format}</span>
                    <span className="text-xs text-gray-400">{match.date} &bull; {match.venue}</span>
                  </div>
                  <div className="space-y-1 mb-3">
                    <div className="flex justify-between font-semibold text-gray-800">
                      <span>{match.team1_name}</span>
                      {match.winner_name === match.team1_name && <span className="text-blue-600 text-xs">WINNER</span>}
                    </div>
                    <div className="flex justify-between font-semibold text-gray-800">
                      <span>{match.team2_name}</span>
                      {match.winner_name === match.team2_name && <span className="text-blue-600 text-xs">WINNER</span>}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 border-t border-gray-100 pt-2 flex justify-between">
                    <span>{match.winner_name} won by {match.win_margin_runs} runs</span>
                    <span className="text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">Scorecard &rarr;</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Global Records */}
        <div className="space-y-8">
          
          {/* Top Batsmen Table */}
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h3 className="text-lg font-bold text-gray-800 mb-4 border-b border-gray-100 pb-2">
              Highest Career Runs
            </h3>
            
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-8 bg-gray-100 animate-pulse rounded"></div>)}
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {topBatsmen.map((batsman, idx) => (
                  <div key={idx} className="py-2 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="text-gray-400 font-mono text-sm">{idx + 1}</span>
                      <div>
                        <Link href={`/player/${batsman.name}`} className="text-blue-600 font-semibold hover:underline text-sm">
                          {batsman.name}
                        </Link>
                        <div className="text-xs text-gray-500">{batsman.team_name}</div>
                      </div>
                    </div>
                    <div className="font-bold text-gray-800 text-sm">
                      {batsman.bat_runs}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <Link href="/records" className="block text-center w-full mt-4 py-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-md text-sm text-gray-600 transition-colors">
              View All Records
            </Link>
          </div>

        </div>

      </div>
    </div>
  );
}
