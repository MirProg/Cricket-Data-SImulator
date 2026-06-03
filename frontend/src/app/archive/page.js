"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function ArchivePage() {
  const [seasons, setSeasons] = useState([]);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [tournaments, setTournaments] = useState([]);
  const [selectedTournament, setSelectedTournament] = useState(null);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/archive/seasons")
      .then(res => res.json())
      .then(data => {
        setSeasons(data.seasons || []);
        if (data.seasons?.length > 0) {
          fetchTournaments(data.seasons[0].id);
        }
        setLoading(false);
      });
  }, []);

  const fetchTournaments = async (seasonId) => {
    setSelectedSeason(seasonId);
    setSelectedTournament(null);
    setMatches([]);
    const res = await fetch(`http://localhost:8000/api/archive/seasons/${seasonId}/tournaments`);
    const data = await res.json();
    setTournaments(data.tournaments || []);
  };

  const fetchMatches = async (tournamentId) => {
    setSelectedTournament(tournamentId);
    const res = await fetch(`http://localhost:8000/api/archive/tournaments/${tournamentId}/matches`);
    const data = await res.json();
    setMatches(data.matches || []);
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar Hierarchy */}
      <div className="w-64 bg-white border-r border-gray-200 overflow-y-auto h-screen sticky top-0">
        <div className="p-4 bg-gray-800 text-white font-bold text-lg">
          Master Archive
        </div>
        <div className="p-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Seasons</h3>
          <ul className="space-y-1">
            {seasons.map(s => (
              <li key={s.id}>
                <button 
                  onClick={() => fetchTournaments(s.id)}
                  className={`w-full text-left px-3 py-2 text-sm rounded ${selectedSeason === s.id ? 'bg-blue-50 text-blue-700 font-bold' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  {s.year}
                </button>
                
                {/* Nested Tournaments */}
                {selectedSeason === s.id && (
                  <ul className="ml-4 mt-1 border-l-2 border-gray-100 pl-2 space-y-1">
                    {tournaments.map(t => (
                      <li key={t.id}>
                        <button
                          onClick={() => fetchMatches(t.id)}
                          className={`w-full text-left px-2 py-1 text-xs rounded truncate ${selectedTournament === t.id ? 'text-blue-600 font-bold' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
                          title={t.name}
                        >
                          {t.name}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-8">
        {!selectedTournament ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
            <h2 className="text-xl font-medium">Select a Tournament</h2>
            <p className="text-sm mt-2">Browse the hierarchical archive to view matches.</p>
          </div>
        ) : (
          <div>
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900">
                {tournaments.find(t => t.id === selectedTournament)?.name}
              </h1>
              <p className="text-gray-500 text-sm mt-1">Showing all matches for this series.</p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Date</th>
                    <th className="px-6 py-3 font-semibold">Match Info</th>
                    <th className="px-6 py-3 font-semibold">Venue</th>
                    <th className="px-6 py-3 font-semibold">Result</th>
                    <th className="px-6 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {matches.map(m => (
                    <tr key={m.match_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 text-gray-600 whitespace-nowrap">
                        <div className="font-medium text-gray-900">{m.month_string}</div>
                        <div className="text-xs">{m.date_string}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-bold text-gray-900">{m.title}</div>
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mt-1">
                          {m.format}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-600">{m.venue}</td>
                      <td className="px-6 py-4 font-medium text-gray-800">{m.result}</td>
                      <td className="px-6 py-4 text-right">
                        <Link href={`/archive/match/${m.match_id}`} className="text-blue-600 font-bold hover:underline">
                          View Scorecard &rarr;
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {matches.length === 0 && (
                    <tr>
                      <td colSpan="5" className="px-6 py-8 text-center text-gray-500">No matches found for this tournament.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
