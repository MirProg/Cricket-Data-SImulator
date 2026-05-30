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
    <div className="app-container">
      <header className="header">
        <h1>Ultimate Cricket Hub</h1>
        <p>The definitive archive of every cricket match in history.</p>
      </header>

      {loading ? (
        <div className="loading">Loading Historical Data...</div>
      ) : (
        <div className="match-grid">
          {matches.map((match) => (
            <div key={match.match_id} className="glass-container match-card">
              <div className="match-date">{match.date} &bull; {match.format}</div>
              <div className="match-teams">
                {match.team1} vs {match.team2}
              </div>
              <div className="match-venue">
                {match.venue}{match.city ? `, ${match.city}` : ''}
              </div>
              {match.winner && (
                <div className="match-result">
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
