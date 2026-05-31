"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function RecordsHub() {
  const [records, setRecords] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/records");
        if (res.ok) {
          setRecords(await res.json());
        }
      } catch (err) {
        console.error("Failed to fetch records", err);
      } finally {
        setLoading(false);
      }
    };
    fetchRecords();
  }, []);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading global records...</div>;
  if (!records) return <div className="p-12 text-center text-red-500">Failed to load records.</div>;

  return (
    <div className="py-8 px-4 sm:px-0">
      
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-gray-900">Global Records Hub</h1>
        <p className="text-gray-600 mt-2">The pinnacle of cricketing achievements across all formats.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        
        {/* Top Run Scorers */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
          <div className="bg-blue-600 text-white px-4 py-3">
            <h3 className="font-bold text-lg">Most Career Runs</h3>
          </div>
          <div className="p-0">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 w-8">#</th>
                  <th className="px-4 py-3">Player</th>
                  <th className="px-4 py-3 text-right">Runs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {records.top_run_scorers?.map((player, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-400 font-mono">{idx + 1}</td>
                    <td className="px-4 py-3 font-semibold text-blue-600 hover:underline">
                      <Link href={`/player/${player.name}`}>{player.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-gray-800">{player.bat_runs}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Wicket Takers */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
          <div className="bg-emerald-600 text-white px-4 py-3">
            <h3 className="font-bold text-lg">Most Career Wickets</h3>
          </div>
          <div className="p-0">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 w-8">#</th>
                  <th className="px-4 py-3">Player</th>
                  <th className="px-4 py-3 text-right">Wkts</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {records.top_wicket_takers?.map((player, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-400 font-mono">{idx + 1}</td>
                    <td className="px-4 py-3 font-semibold text-blue-600 hover:underline">
                      <Link href={`/player/${player.name}`}>{player.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-gray-800">{player.bowl_wickets}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Highest Averages */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
          <div className="bg-purple-600 text-white px-4 py-3">
            <h3 className="font-bold text-lg">Highest Batting Average</h3>
          </div>
          <div className="p-0">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 w-8">#</th>
                  <th className="px-4 py-3">Player</th>
                  <th className="px-4 py-3 text-right">Avg</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {records.highest_averages?.map((player, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-400 font-mono">{idx + 1}</td>
                    <td className="px-4 py-3 font-semibold text-blue-600 hover:underline">
                      <Link href={`/player/${player.name}`}>{player.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-gray-800">{player.bat_avg ? player.bat_avg.toFixed(2) : '-'}</td>
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
