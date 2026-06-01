"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function MatchScorecard() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

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

  if (loading) return <div className="p-12 text-center text-gray-500">Loading scorecard...</div>;
  if (!data || data.error) return <div className="p-12 text-center text-red-500">Match not found.</div>;

  const { info, innings } = data;

  return (
    <div className="py-6 px-4 sm:px-0">
      
      {/* Match Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex justify-between items-start mb-4">
          <span className="text-sm font-bold text-gray-500 uppercase">{info.format} &bull; {info.date}</span>
          <span className="text-sm text-gray-500">{info.venue}</span>
        </div>
        <div className="flex justify-center items-center gap-12 mb-6">
          <div className="text-center">
            <h2 className="text-2xl font-black text-gray-800">{info.team1_name}</h2>
          </div>
          <div className="text-gray-400 font-italic text-sm">vs</div>
          <div className="text-center">
            <h2 className="text-2xl font-black text-gray-800">{info.team2_name}</h2>
          </div>
        </div>
        <div className="text-center text-blue-700 font-bold bg-blue-50 py-2 rounded">
          {info.winner_name} {info.win_margin_text ? info.win_margin_text : "won"}
        </div>
      </div>

      {/* Innings Accordions */}
      <div className="flex flex-col gap-6">
        {innings.map((inn, idx) => (
          <div key={idx} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            
            {/* Innings Header */}
            <div className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
              <h3 className="font-bold">{inn.batting_team} 1st Innings</h3>
              <span className="font-bold">{inn.runs}/{inn.wickets} <span className="text-gray-400 font-normal ml-2">({inn.overs} Overs)</span></span>
            </div>

            {/* Batting Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3">Batter</th>
                    <th className="px-4 py-3"></th>
                    <th className="px-4 py-3 text-right font-bold text-gray-800">R</th>
                    <th className="px-4 py-3 text-right">B</th>
                    <th className="px-4 py-3 text-right">4s</th>
                    <th className="px-4 py-3 text-right">6s</th>
                    <th className="px-4 py-3 text-right">SR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {inn.batting.map(b => (
                    <tr key={b.batter_name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-blue-600 hover:underline whitespace-nowrap">
                        <Link href={`/player/${b.batter_name}`}>{b.batter_name}</Link>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{b.dismissal_text}</td>
                      <td className="px-4 py-3 text-right font-bold text-gray-800">{b.runs}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{b.balls}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{b.fours}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{b.sixes}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.strike_rate !== null ? b.strike_rate : '-'}</td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-gray-700">Extras</td>
                    <td colSpan="6" className="px-4 py-3 font-bold text-gray-800">{inn.extras_total}</td>
                  </tr>
                  <tr className="bg-gray-100 border-t-2 border-gray-200">
                    <td className="px-4 py-3 font-bold text-gray-900 uppercase text-xs">Total</td>
                    <td colSpan="6" className="px-4 py-3 font-bold text-gray-900">
                      {inn.runs}/{inn.wickets} <span className="font-normal text-gray-600">({inn.overs} Overs)</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Fall of Wickets */}
            <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
              <h4 className="text-xs font-bold uppercase text-gray-500 mb-2">Fall of Wickets</h4>
              <p className="text-sm text-gray-700 leading-relaxed">
                {inn.fow.map((f, i) => (
                  <span key={i}>
                    {f.score}-{f.wicket_num} ({f.player_out}, {f.overs} ov){i < inn.fow.length - 1 ? ', ' : ''}
                  </span>
                ))}
              </p>
            </div>

            {/* Bowling Table */}
            <div className="overflow-x-auto border-t border-gray-200">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3">Bowler</th>
                    <th className="px-4 py-3 text-right">O</th>
                    <th className="px-4 py-3 text-right">M</th>
                    <th className="px-4 py-3 text-right">R</th>
                    <th className="px-4 py-3 text-right font-bold text-gray-800">W</th>
                    <th className="px-4 py-3 text-right">ECON</th>
                    <th className="px-4 py-3 text-right">WD</th>
                    <th className="px-4 py-3 text-right">NB</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {inn.bowling.map(b => (
                    <tr key={b.bowler_name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-blue-600 hover:underline whitespace-nowrap">
                        <Link href={`/player/${b.bowler_name}`}>{b.bowler_name}</Link>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">{b.overs}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{b.maidens}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{b.runs}</td>
                      <td className="px-4 py-3 text-right font-bold text-gray-800">{b.wickets}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.econ !== null ? b.econ : '-'}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.wides}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{b.no_balls}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

          </div>
        ))}
      </div>
    </div>
  );
}
