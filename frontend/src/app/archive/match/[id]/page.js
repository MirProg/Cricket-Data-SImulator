"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function ArchiveMatchScorecard() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/archive/matches/${id}`)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return <div className="p-12 text-center text-gray-500">Loading comprehensive scorecard...</div>;
  }

  if (!data || data.error) {
    return <div className="p-12 text-center text-red-500 font-bold">Error loading match data.</div>;
  }

  const { metadata, scorecards } = data;

  const calculateStrikeRate = (runs, balls) => {
    try {
      const r = parseInt(runs);
      const b = parseInt(balls);
      if (b === 0) return "-";
      return ((r / b) * 100).toFixed(2);
    } catch {
      return "-";
    }
  };

  const calculateEcon = (runs, overs) => {
    try {
      const r = parseInt(runs);
      const o = parseFloat(overs);
      if (o === 0) return "-";
      return (r / o).toFixed(2);
    } catch {
      return "-";
    }
  };

  return (
    <div className="bg-gray-100 min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        <Link href="/archive" className="text-blue-600 hover:underline text-sm font-semibold mb-4 inline-block">&larr; Back to Archive</Link>

        {/* Match Header */}
        <div className="bg-white rounded-xl shadow p-6 border-t-4 border-blue-900">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-black text-gray-900">{metadata.title}</h1>
              <p className="text-gray-500 mt-2 font-medium">{metadata.series || metadata.venue}</p>
              <div className="mt-4 flex gap-2">
                <span className="px-3 py-1 bg-gray-100 text-gray-800 text-xs font-bold rounded-full">{metadata.format || "Match"}</span>
                {metadata.toss && <span className="px-3 py-1 bg-gray-100 text-gray-800 text-xs font-bold rounded-full">Toss: {metadata.toss}</span>}
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-green-700 bg-green-50 px-4 py-2 rounded border border-green-200">
                {metadata.result || "Result Pending"}
              </div>
            </div>
          </div>
        </div>

        {/* Innings Iterate */}
        {scorecards.length === 0 ? (
          <div className="bg-white p-12 text-center text-gray-500 rounded-xl shadow">
            Scorecard details are not available or are currently being extracted.
          </div>
        ) : (
          scorecards.map((inn, idx) => (
            <div key={idx} className="bg-white rounded-xl shadow overflow-hidden border border-gray-200">
              <div className="bg-gray-800 text-white px-6 py-3 flex justify-between items-center">
                <h2 className="text-lg font-bold">{inn.details.batting_team}</h2>
              </div>

              {/* Batting Table */}
              {inn.batting.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-700 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-2 font-semibold">Batter</th>
                        <th className="px-6 py-2 font-semibold">Dismissal</th>
                        <th className="px-4 py-2 text-right font-semibold">R</th>
                        <th className="px-4 py-2 text-right font-semibold">B</th>
                        <th className="px-4 py-2 text-right font-semibold">M</th>
                        <th className="px-4 py-2 text-right font-semibold">4s</th>
                        <th className="px-4 py-2 text-right font-semibold">6s</th>
                        <th className="px-4 py-2 text-right font-semibold">SR</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {inn.batting.map((b, bIdx) => (
                        <tr key={bIdx} className="hover:bg-gray-50">
                          <td className="px-6 py-3 font-medium text-blue-700">{b.player_name}</td>
                          <td className="px-6 py-3 text-gray-500 text-xs">{b.dismissal}</td>
                          <td className="px-4 py-3 text-right font-bold text-gray-900">{b.runs}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{b.balls}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{b.mins}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{b.fours}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{b.sixes}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{calculateStrikeRate(b.runs, b.balls)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Bowling Table */}
              {inn.bowling.length > 0 && (
                <div className="border-t-4 border-gray-100 overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-700 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-2 font-semibold">Bowler</th>
                        <th className="px-4 py-2 text-right font-semibold">O</th>
                        <th className="px-4 py-2 text-right font-semibold">M</th>
                        <th className="px-4 py-2 text-right font-semibold">R</th>
                        <th className="px-4 py-2 text-right font-semibold">W</th>
                        <th className="px-4 py-2 text-right font-semibold">Wides</th>
                        <th className="px-4 py-2 text-right font-semibold">NBs</th>
                        <th className="px-4 py-2 text-right font-semibold">ECON</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {inn.bowling.map((bw, bwIdx) => (
                        <tr key={bwIdx} className="hover:bg-gray-50">
                          <td className="px-6 py-3 font-medium text-blue-700">{bw.player_name}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{bw.overs}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{bw.maidens}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{bw.runs}</td>
                          <td className="px-4 py-3 text-right font-bold text-gray-900">{bw.wickets}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{bw.wides}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{bw.no_balls}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{calculateEcon(bw.runs, bw.overs)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
            </div>
          ))
        )}

      </div>
    </div>
  );
}
