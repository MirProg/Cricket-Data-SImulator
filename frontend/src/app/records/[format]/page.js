"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function FormatRecordsPage() {
  const params = useParams();
  const [records, setRecords] = useState(null);
  const [loading, setLoading] = useState(true);

  const formatName = params.format.toUpperCase();

  useEffect(() => {
    fetch(`http://localhost:8000/api/records/${params.format}`)
      .then(r => r.json())
      .then(d => { setRecords(d); setLoading(false); });
  }, [params.format]);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading {formatName} records...</div>;

  return (
    <div className="py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">{formatName} Cricket Records</h1>
      
      <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
        <div className="bg-blue-600 text-white px-4 py-3">
          <h3 className="font-bold text-lg">Most Career Runs ({formatName})</h3>
        </div>
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b">
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
  );
}
