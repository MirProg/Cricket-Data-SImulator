"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function TeamPage() {
  const params = useParams();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  const teamName = decodeURIComponent(params.id).replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());

  useEffect(() => {
    fetch(`http://localhost:8000/api/team/${params.id}`)
      .then(r => r.json())
      .then(d => { setMatches(d); setLoading(false); });
  }, [params.id]);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading {teamName} matches...</div>;

  return (
    <div className="py-8 px-4">
      <div className="flex items-center gap-4 mb-6">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center text-2xl">🏏</div>
        <h1 className="text-3xl font-black">{teamName}</h1>
      </div>
      <h2 className="text-xl font-bold mb-4 text-gray-700">Recent Matches</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {matches.length === 0 && <p className="text-gray-500">No matches found for this team.</p>}
        {matches.map(m => (
          <Link href={`/match/${m.match_id}`} key={m.match_id} className="block p-4 border rounded-lg bg-white hover:shadow">
            <div className="text-xs font-bold text-gray-500 bg-gray-100 px-2 py-1 rounded w-max mb-2">{m.format}</div>
            <div className="font-bold">{m.team1_name} vs {m.team2_name}</div>
            <div className="text-sm mt-2 text-blue-600">{m.winner_name} won</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
