"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function MatchScorecard() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMatch = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/match/${params.id}`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (err) {
        console.error("Failed to fetch match", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMatch();
  }, [params.id]);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading scorecard...</div>;
  if (!data || data.error) return <div className="p-12 text-center text-red-500">Match not found.</div>;

  const { info, scorecard } = data;
  
  // Separate players into teams (based on seed data logic)
  const team1Players = scorecard.filter(p => p.team === info.team1_name);
  const team2Players = scorecard.filter(p => p.team === info.team2_name);

  return (
    <div className="py-6 px-4 sm:px-0">
      
      {/* Match Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex justify-between items-start mb-4">
          <span className="text-sm font-bold text-gray-500 uppercase">{info.format} &bull; {info.date}</span>
          <span className="text-sm text-gray-500">{info.venue}</span>
        </div>
        <div className="flex justify-center items-center gap-12 mb-6">
          <div className="text-center">
            <h2 className="text-2xl font-black text-gray-800">{info.team1_name}</h2>
          </div>
          <div className="text-gray-400 font-italic text-sm">vs</div>
          <div className="text-center">
            <h2 className="text-2xl font-black text-gray-800">{info.team2_name}</h2>
          </div>
        </div>
        <div className="text-center text-blue-700 font-bold bg-blue-50 py-2 rounded">
          {info.winner_name} won by {info.win_margin_runs} runs
        </div>
      </div>

      {/* Scorecards Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* Team 1 Scorecard */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-100 border-b border-gray-200 px-4 py-3">
            <h3 className="font-bold text-gray-800">{info.team1_name} Innings</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3">Batter</th>
                  <th className="px-4 py-3 text-right">R</th>
                  <th className="px-4 py-3 text-right">B</th>
                  <th className="px-4 py-3 text-right">SR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {team1Players.map(p => (
                  <tr key={p.player_name} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-blue-600 hover:underline">
                      <Link href={`/player/${p.player_name}`}>{p.player_name}</Link>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-gray-800">{p.runs_scored}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{p.balls_faced}</td>
                    <td className="px-4 py-3 text-right text-gray-500">
                      {p.balls_faced > 0 ? ((p.runs_scored / p.balls_faced) * 100).toFixed(2) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Team 2 Scorecard */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-100 border-b border-gray-200 px-4 py-3">
            <h3 className="font-bold text-gray-800">{info.team2_name} Innings</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3">Batter</th>
                  <th className="px-4 py-3 text-right">R</th>
                  <th className="px-4 py-3 text-right">B</th>
                  <th className="px-4 py-3 text-right">SR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {team2Players.map(p => (
                  <tr key={p.player_name} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-blue-600 hover:underline">
                      <Link href={`/player/${p.player_name}`}>{p.player_name}</Link>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-gray-800">{p.runs_scored}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{p.balls_faced}</td>
                    <td className="px-4 py-3 text-right text-gray-500">
                      {p.balls_faced > 0 ? ((p.runs_scored / p.balls_faced) * 100).toFixed(2) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
