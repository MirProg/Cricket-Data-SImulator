import { useEffect, useState } from 'react'
import './index.css'

interface Match {
  match_id: string;
  date: string;
  venue: string;
  city: string;
  format: string;
  team1: string;
  team2: string;
  winner: string;
  win_margin_runs: number;
  win_margin_wickets: number;
}

function App() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch from FastAPI Backend
    fetch('http://localhost:8000/api/v1/matches')
      .then(res => res.json())
      .then(data => {
        if (data.matches) {
          setMatches(data.matches);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch matches:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="max-w-7xl mx-auto py-10 px-5">
      <header className="text-center mb-10">
        <h1 className="text-5xl font-extrabold bg-gradient-to-r from-primary to-[#0096ff] bg-clip-text text-transparent mb-2">
          Ultimate Cricket Hub
        </h1>
        <p className="text-text-secondary text-lg">The definitive archive of every cricket match in history.</p>
      </header>

      {loading ? (
        <div className="text-center text-2xl text-primary py-10 animate-pulse">Loading Historical Data...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {matches.map((match) => (
            <div key={match.match_id} className="bg-glass-bg backdrop-blur-md border border-glass-border rounded-2xl p-6 shadow-xl transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_12px_40px_0_rgba(0,255,204,0.2)] hover:border-[rgba(0,255,204,0.3)] cursor-pointer">
              <div className="text-sm text-primary font-semibold mb-2">{match.date} &bull; {match.format}</div>
              <div className="text-xl font-bold mb-3">
                {match.team1} <span className="text-text-secondary font-normal mx-2">vs</span> {match.team2}
              </div>
              <div className="text-text-secondary text-sm mb-4 flex items-center">
                <svg className="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                {match.venue}{match.city ? `, ${match.city}` : ''}
              </div>
              {match.winner && (
                <div className="bg-[rgba(0,255,204,0.1)] text-primary px-3 py-1.5 rounded-lg text-sm font-medium inline-block">
                  {match.winner} won by {match.win_margin_runs > 0 ? `${match.win_margin_runs} runs` : `${match.win_margin_wickets} wickets`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default App
