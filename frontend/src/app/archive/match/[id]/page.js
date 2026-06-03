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

  return (
    <div className="bg-gray-100 min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        <Link href="/archive" className="text-blue-600 hover:underline text-sm font-semibold mb-4 inline-block">&larr; Back to Archive</Link>

        {/* Match Header */}
        <div className="bg-white rounded-xl shadow p-6 border-t-4 border-blue-900">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-black text-gray-900">{metadata.title}</h1>
              <p className="text-gray-500 mt-2 font-medium">{metadata.date_string} &bull; {metadata.venue}</p>
              <div className="mt-4 flex gap-2">
                <span className="px-3 py-1 bg-gray-100 text-gray-800 text-xs font-bold rounded-full">{metadata.format}</span>
                {metadata.toss_decision && <span className="px-3 py-1 bg-gray-100 text-gray-800 text-xs font-bold rounded-full">Toss: {metadata.toss_decision}</span>}
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-green-700 bg-green-50 px-4 py-2 rounded border border-green-200">
                {metadata.result}
              </div>
              <div className="text-xs text-gray-400 mt-2 max-w-xs">{metadata.win_margin_text}</div>
            </div>
          </div>
        </div>

        {/* Innings Iterate */}
        {scorecards.map((inn, idx) => (
          <div key={idx} className="bg-white rounded-xl shadow overflow-hidden border border-gray-200">
            <div className="bg-gray-800 text-white px-6 py-3 flex justify-between items-center">
              <h2 className="text-lg font-bold">Innings {inn.details.innings_number}</h2>
              <span className="font-mono bg-gray-900 px-3 py-1 rounded">Score: {inn.details.runs}/{inn.details.wickets} ({inn.details.overs} ov)</span>
            </div>

            {/* Batting Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-700 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-2 font-semibold">Batter</th>
                    <th className="px-6 py-2 font-semibold">Dismissal</th>
                    <th className="px-4 py-2 text-right font-semibold">R</th>
                    <th className="px-4 py-2 text-right font-semibold">B</th>
                    <th className="px-4 py-2 text-right font-semibold">4s</th>
                    <th className="px-4 py-2 text-right font-semibold">6s</th>
                    <th className="px-4 py-2 text-right font-semibold">SR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {inn.batting.map((b, bIdx) => (
                    <tr key={bIdx} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-blue-700">{b.name}</td>
                      <td className="px-6 py-3 text-gray-500 text-xs">{b.dismissal_text}</td>
                      <td className="px-4 py-3 text-right font-bold text-gray-900">{b.runs}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.balls}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.fours}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.sixes}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.strike_rate}</td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 border-t border-gray-200 font-bold text-gray-800">
                    <td className="px-6 py-3">Extras</td>
                    <td className="px-6 py-3 text-xs text-gray-500 font-normal">
                      (b {inn.details.extras_b}, lb {inn.details.extras_lb}, w {inn.details.extras_wd}, nb {inn.details.extras_nb})
                    </td>
                    <td className="px-4 py-3 text-right">{inn.details.extras_total}</td>
                    <td colSpan="4"></td>
                  </tr>
                  <tr className="bg-gray-100 border-t border-gray-200 font-bold text-gray-900">
                    <td className="px-6 py-3 uppercase tracking-wider text-xs">Total</td>
                    <td className="px-6 py-3 text-xs text-gray-500 font-normal">
                      ({inn.details.wickets} wickets, {inn.details.overs} overs)
                    </td>
                    <td className="px-4 py-3 text-right text-lg">{inn.details.runs}</td>
                    <td colSpan="4"></td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Bowling Table */}
            <div className="border-t-4 border-gray-100 overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-700 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-2 font-semibold">Bowler</th>
                    <th className="px-4 py-2 text-right font-semibold">O</th>
                    <th className="px-4 py-2 text-right font-semibold">M</th>
                    <th className="px-4 py-2 text-right font-semibold">R</th>
                    <th className="px-4 py-2 text-right font-semibold">W</th>
                    <th className="px-4 py-2 text-right font-semibold">ECON</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {inn.bowling.map((bw, bwIdx) => (
                    <tr key={bwIdx} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-blue-700">{bw.name}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{bw.overs}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{bw.maidens}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{bw.runs}</td>
                      <td className="px-4 py-3 text-right font-bold text-gray-900">{bw.wickets}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{bw.econ}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Fall of Wickets */}
            {inn.fow && inn.fow.length > 0 && (
              <div className="p-4 border-t border-gray-200 bg-gray-50 text-xs text-gray-600">
                <span className="font-bold text-gray-800 uppercase tracking-wider block mb-2">Fall of wickets</span>
                <div className="flex flex-wrap gap-4">
                  {inn.fow.map((f, fIdx) => (
                    <span key={fIdx}>
                      <strong className="text-gray-900">{f.score}-{f.wicket_num}</strong> ({f.name}, {f.overs} ov)
                    </span>
                  ))}
                </div>
              </div>
            )}
            
          </div>
        ))}

      </div>
    </div>
  );
}
