"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function ArchiveYearPage() {
  const params = useParams();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/archives/${params.year}`)
      .then(r => r.json())
      .then(d => { setMatches(d); setLoading(false); });
  }, [params.year]);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading archives for {params.year}...</div>;

  return (
    <div className="py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Match Archives: {params.year}</h1>
      <div className="grid grid-cols-1 gap-4">
        {matches.map(m => (
          <Link href={`/match/${m.match_id}`} key={m.match_id} className="block p-4 border rounded-lg bg-white hover:shadow">
            <div className="text-sm text-gray-500 mb-2">{m.date} &bull; {m.venue} &bull; {m.format}</div>
            <div className="font-bold flex justify-between">
              <span>{m.team1_name} vs {m.team2_name}</span>
              <span className="text-blue-600">{m.winner_name} won by {m.win_margin_runs} runs</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
