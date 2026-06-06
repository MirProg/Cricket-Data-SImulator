"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function MatchScorecard() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(1);

  useEffect(() => {
    const fetchMatch = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/match/${params.id}`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (err) {
        console.error("Failed to fetch match", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMatch();
  }, [params.id]);

  if (loading) return <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-12 text-center text-zinc-400">Loading Scorecard Data...</div>;
  if (!data || data.error) return <div className="min-h-screen bg-zinc-950 p-12 text-center text-red-500 font-bold">Match not found in database.</div>;

  const { match_meta: info, innings } = data;
  
  // Format result
  const resultStr = info.result || info.series || "";

  return (
    <div className="min-h-screen bg-zinc-950 py-10 px-4 sm:px-6 lg:px-8 text-zinc-200">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Match Header Ribbon */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl">
          <div className="bg-zinc-800/50 px-6 py-4 flex flex-col sm:flex-row justify-between items-center border-b border-zinc-800">
            <span className="text-xs font-bold tracking-widest text-emerald-500 uppercase">{info.match_format || info.format} • {info.match_category}</span>
            <span className="text-xs text-zinc-400 mt-2 sm:mt-0">{info.tournament} • {info.season}</span>
          </div>
          
          <div className="px-8 py-10 flex flex-col items-center justify-center relative">
            <div className="absolute top-4 right-4 text-xs text-zinc-500">{info.ground_name || info.venue}</div>
            
            <div className="flex flex-col md:flex-row items-center justify-center gap-6 w-full">
              <div className="flex-1 flex justify-end">
                <h2 className="text-3xl font-black tracking-tight text-white">{info.team1 || info.title?.split('v')[0]?.strip() || "Team 1"}</h2>
              </div>
              <div className="flex flex-col items-center px-8">
                <span className="text-zinc-600 font-bold text-sm italic mb-2">VS</span>
              </div>
              <div className="flex-1 flex justify-start">
                <h2 className="text-3xl font-black tracking-tight text-white">{info.team2 || info.title?.split('v')[1]?.strip() || "Team 2"}</h2>
              </div>
            </div>
          </div>
          
          <div className="bg-emerald-950/30 border-t border-emerald-900/30 px-6 py-4 text-center">
            <p className="text-emerald-400 font-bold">{resultStr}</p>
          </div>
        </div>

        {/* Innings Tabs */}
        {innings.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {innings.map((inn) => (
              <button 
                key={inn.metadata.innings_number}
                onClick={() => setActiveTab(inn.metadata.innings_number)}
                className={`px-6 py-3 rounded-t-lg font-bold text-sm transition-colors ${activeTab === inn.metadata.innings_number ? 'bg-zinc-800 text-white border-t-2 border-emerald-500' : 'bg-zinc-900/50 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/80'}`}
              >
                {inn.metadata.team_name} ({inn.metadata.total_runs}/{inn.metadata.wickets})
              </button>
            ))}
          </div>
        )}

        {/* Scorecard Table */}
        {innings.map((inn) => {
          if (inn.metadata.innings_number !== activeTab) return null;
          const didNotBat = inn.batting.filter(b => b.dismissal?.toLowerCase() === 'did not bat');
          const batted = inn.batting.filter(b => b.dismissal?.toLowerCase() !== 'did not bat');
          
          return (
            <div key={inn.metadata.innings_number} className="bg-zinc-900 border border-zinc-800 rounded-b-xl rounded-tr-xl overflow-hidden shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-500">
              
              {/* Batting Header */}
              <div className="bg-zinc-800 px-6 py-3 border-b border-zinc-700 flex justify-between items-center">
                <h3 className="font-bold text-zinc-100">Batting</h3>
              </div>

              {/* Batting Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-zinc-900/50 text-zinc-400 text-xs uppercase tracking-wider border-b border-zinc-800">
                    <tr>
                      <th className="px-6 py-4 font-medium">Batter</th>
                      <th className="px-6 py-4 font-medium"></th>
                      <th className="px-6 py-4 text-right font-bold text-zinc-300">R</th>
                      <th className="px-6 py-4 text-right font-medium">B</th>
                      <th className="px-6 py-4 text-right font-medium">4s</th>
                      <th className="px-6 py-4 text-right font-medium">6s</th>
                      <th className="px-6 py-4 text-right font-medium">SR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    {batted.map((b, idx) => {
                      const sr = b.balls && parseInt(b.balls) > 0 ? ((b.runs / parseInt(b.balls)) * 100).toFixed(2) : '-';
                      return (
                        <tr key={idx} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="px-6 py-4 font-medium text-emerald-400 hover:text-emerald-300 whitespace-nowrap">
                            {b.player_name}
                          </td>
                          <td className="px-6 py-4 text-zinc-500 text-xs">{b.dismissal}</td>
                          <td className="px-6 py-4 text-right font-bold text-zinc-200">{b.runs}</td>
                          <td className="px-6 py-4 text-right text-zinc-400">{b.balls}</td>
                          <td className="px-6 py-4 text-right text-zinc-400">{b.fours}</td>
                          <td className="px-6 py-4 text-right text-zinc-400">{b.sixes}</td>
                          <td className="px-6 py-4 text-right text-zinc-500">{sr}</td>
                        </tr>
                      );
                    })}
                    
                    {/* Extras & Total */}
                    <tr className="bg-zinc-900/30">
                      <td className="px-6 py-4 font-medium text-zinc-300">Extras</td>
                      <td colSpan="6" className="px-6 py-4 font-bold text-zinc-300 flex items-center gap-2">
                        <span>{inn.metadata.extras_total}</span>
                        <span className="text-xs font-normal text-zinc-500">{inn.metadata.extras_detail}</span>
                      </td>
                    </tr>
                    <tr className="bg-zinc-800/50 border-t-2 border-zinc-700">
                      <td className="px-6 py-4 font-bold text-white uppercase tracking-wider text-xs">Total</td>
                      <td colSpan="6" className="px-6 py-4 font-bold text-white">
                        {inn.metadata.total_runs}/{inn.metadata.wickets} <span className="font-normal text-zinc-400 ml-2">({inn.metadata.overs} Overs)</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Did Not Bat */}
              {didNotBat.length > 0 && (
                <div className="px-6 py-4 bg-zinc-900 border-t border-zinc-800 text-sm">
                  <span className="font-bold text-zinc-400 mr-2 uppercase text-xs tracking-wider">Did not bat:</span>
                  <span className="text-emerald-500/80">
                    {didNotBat.map(d => d.player_name).join(', ')}
                  </span>
                </div>
              )}

              {/* Fall of Wickets */}
              {inn.fow && (
                <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-900/50">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-2">Fall of Wickets</h4>
                  <p className="text-sm text-zinc-400 leading-relaxed">
                    {inn.fow}
                  </p>
                </div>
              )}

              {/* Bowling Header */}
              <div className="bg-zinc-800 px-6 py-3 border-t border-zinc-700 flex justify-between items-center mt-4">
                <h3 className="font-bold text-zinc-100">Bowling</h3>
              </div>

              {/* Bowling Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-zinc-900/50 text-zinc-400 text-xs uppercase tracking-wider border-b border-zinc-800">
                    <tr>
                      <th className="px-6 py-4 font-medium">Bowler</th>
                      <th className="px-6 py-4 text-right font-medium">O</th>
                      <th className="px-6 py-4 text-right font-medium">M</th>
                      <th className="px-6 py-4 text-right font-medium">R</th>
                      <th className="px-6 py-4 text-right font-bold text-zinc-300">W</th>
                      <th className="px-6 py-4 text-right font-medium">ECON</th>
                      <th className="px-6 py-4 text-right font-medium">WD</th>
                      <th className="px-6 py-4 text-right font-medium">NB</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    {inn.bowling.map((b, idx) => {
                      const oversFloat = parseFloat(b.overs || "0");
                      const econ = oversFloat > 0 ? (b.runs / oversFloat).toFixed(2) : '-';
                      return (
                        <tr key={idx} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="px-6 py-4 font-medium text-emerald-400 hover:text-emerald-300 whitespace-nowrap">
                            {b.player_name}
                          </td>
                          <td className="px-6 py-4 text-right text-zinc-400">{b.overs}</td>
                          <td className="px-6 py-4 text-right text-zinc-400">{b.maidens}</td>
                          <td className="px-6 py-4 text-right text-zinc-400">{b.runs}</td>
                          <td className="px-6 py-4 text-right font-bold text-zinc-200">{b.wickets}</td>
                          <td className="px-6 py-4 text-right text-zinc-500">{econ}</td>
                          <td className="px-6 py-4 text-right text-zinc-500">{b.wides}</td>
                          <td className="px-6 py-4 text-right text-zinc-500">{b.no_balls}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

            </div>
          );
        })}
        
      </div>
    </div>
  );
}
