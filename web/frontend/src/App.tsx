import { useEffect, useState } from 'react'
import SimulatorPage from './Simulator'
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
  const [activeTab, setActiveTab] = useState('database');

  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    // Fetch Historical Matches
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

    // Poll Spider Status Every 3 Seconds
    const fetchStatus = () => {
      fetch('http://localhost:8000/api/v1/system/status')
        .then(res => res.json())
        .then(data => setStatus(data))
        .catch(err => console.error(err));
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-7xl mx-auto py-10 px-5">
      <header className="text-center mb-10">
        <h1 className="text-5xl font-extrabold bg-gradient-to-r from-primary to-[#0096ff] bg-clip-text text-transparent mb-2">
          CricMatrix Platform
        </h1>
        <p className="text-text-secondary text-lg">The definitive archive and simulation engine.</p>
        
        <div className="flex justify-center gap-4 mt-8">
          <button 
            onClick={() => setActiveTab('database')}
            className={`px-6 py-2 rounded-full font-bold transition-all ${activeTab === 'database' ? 'bg-primary text-black' : 'bg-bg-dark text-slate-400 border border-slate-700'}`}
          >
            Database Portal
          </button>
          <button 
            onClick={() => setActiveTab('simulator')}
            className={`px-6 py-2 rounded-full font-bold transition-all ${activeTab === 'simulator' ? 'bg-[#3B82F6] text-white' : 'bg-bg-dark text-slate-400 border border-slate-700'}`}
          >
            AI Simulator
          </button>
        </div>
        
        {/* Search Bar */}
        {activeTab === 'database' && (
          <div className="mt-8 max-w-2xl mx-auto relative">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search canonical player database..."
                className="w-full bg-bg-dark border border-glass-border rounded-full py-3 pl-12 pr-4 text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-lg transition-all"
                onChange={(e) => {
                  const val = e.target.value;
                  if (val.length > 2) {
                    fetch(`http://localhost:8000/search/players?q=${val}`)
                      .then(res => res.json())
                      .then(data => {
                        // In a real app we'd show a dropdown of results
                        console.log("Search Results:", data.results);
                      });
                  }
                }}
              />
            </div>
          </div>
        )}
      </header>

      {activeTab === 'simulator' ? (
        <SimulatorPage />
      ) : (
        <>
      {/* Live Spider Dashboard */}
      {status && status.database && (
        <div className="mb-12 bg-glass-bg backdrop-blur-md border border-primary/30 rounded-2xl p-6 shadow-[0_0_20px_rgba(0,255,204,0.15)] relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-[#0096ff] animate-pulse"></div>
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse mr-3"></span>
            Live Spider Dashboard
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-bg-dark rounded-lg p-4 border border-glass-border text-center">
              <div className="text-text-secondary text-sm mb-1">Total Matches Ingested</div>
              <div className="text-3xl font-bold text-primary">{status.database.total_matches?.toLocaleString() || 0}</div>
            </div>
            <div className="bg-bg-dark rounded-lg p-4 border border-glass-border text-center">
              <div className="text-text-secondary text-sm mb-1">Total Deliveries Mapped</div>
              <div className="text-3xl font-bold text-primary">{status.database.total_balls_delivered?.toLocaleString() || 0}</div>
            </div>
            <div className="bg-bg-dark rounded-lg p-4 border border-glass-border text-center">
              <div className="text-text-secondary text-sm mb-1">Network Scraper Protocol</div>
              <div className="text-xl font-bold text-[#0096ff] mt-1">Cricinfo/Cricbuzz</div>
            </div>
          </div>
          
          <div className="bg-black/50 rounded-lg p-4 font-mono text-xs text-green-400 overflow-hidden h-32 flex flex-col justify-end border border-white/5">
            {status.scraper_logs && status.scraper_logs.length > 0 ? (
              status.scraper_logs.map((log: string, i: number) => (
                <div key={i} className="whitespace-pre-wrap">{log}</div>
              ))
            ) : (
              <div className="text-gray-500 italic">Waiting for distributed spiders to ping the terminal...</div>
            )}
          </div>
        </div>
      )}

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
      </>
      )}
    </div>
  )
}

export default App
