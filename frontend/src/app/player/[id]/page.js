"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function PlayerProfile() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const playerName = decodeURIComponent(params.id);

  useEffect(() => {
    fetch(`http://localhost:8000/api/player/${playerName}`)
      .then(res => res.json())
      .then(fetchedData => {
        if (fetchedData.error || !fetchedData.career_stats) {
          setData(null);
        } else {
          const formattedBatting = fetchedData.career_stats.map(s => ({
            format: s.format, mat: s.matches, inns: s.bat_innings, no: s.not_outs, runs: s.bat_runs,
            hs: s.highest_score_not_out ? `${s.highest_score}*` : s.highest_score,
            ave: s.bat_avg ? s.bat_avg.toFixed(2) : "-", bf: s.balls_faced, sr: s.bat_sr ? s.bat_sr.toFixed(2) : "-",
            "100s": s.hundreds, "50s": s.fifties, "4s": s.fours, "6s": s.sixes, ct: s.catches, st: s.stumpings
          }));
          
          const formattedBowling = fetchedData.career_stats.map(s => ({
            format: s.format, mat: s.matches, inns: s.bowl_innings, balls: s.bowl_balls, runs: s.bowl_runs, wkts: s.bowl_wickets,
            bbi: s.best_bowl_innings || "-", bbm: s.best_bowl_match || "-", ave: s.bowl_avg ? s.bowl_avg.toFixed(2) : "-",
            econ: s.bowl_econ ? s.bowl_econ.toFixed(2) : "-", sr: s.bowl_sr ? s.bowl_sr.toFixed(2) : "-", "4w": s.four_wickets, "5w": s.five_wickets, "10w": s.ten_wickets
          }));
          
          setData({
            name: fetchedData.name,
            country: fetchedData.team_name || "International Player",
            role: "Cricket Player",
            battingStyle: "-",
            bowlingStyle: "-",
            batting: formattedBatting,
            bowling: formattedBowling
          });
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [playerName]);

  if (loading) return <div className="p-12 text-center text-gray-500 min-h-screen bg-[#f8fafc]">Loading profile...</div>;

  return (
    <div className="py-8 px-4 bg-[#f8fafc] min-h-screen">
      <div className="max-w-6xl mx-auto">
        
        {/* Personal Information Card */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-8 flex items-center gap-6">
          <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center text-4xl text-gray-400">
            👤
          </div>
          <div>
            <h1 className="text-3xl font-black text-gray-900 mb-1">{data.name}</h1>
            <div className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-3">{data.country}</div>
            <div className="flex gap-6 text-sm text-gray-700">
              <div><span className="font-bold text-gray-500 mr-1">Playing Role:</span> {data.role}</div>
              <div><span className="font-bold text-gray-500 mr-1">Batting Style:</span> {data.battingStyle}</div>
              <div><span className="font-bold text-gray-500 mr-1">Bowling Style:</span> {data.bowlingStyle}</div>
            </div>
          </div>
        </div>

        {/* BATTING & FIELDING STATS */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden mb-8">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex justify-between items-center">
            <h2 className="font-bold text-gray-800 text-sm uppercase">Batting & Fielding</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-right">
              <thead className="bg-white text-gray-500 text-xs font-semibold border-b">
                <tr>
                  <th className="px-4 py-3 text-left">Format</th>
                  <th className="px-3 py-3">Mat</th>
                  <th className="px-3 py-3">Inns</th>
                  <th className="px-3 py-3">NO</th>
                  <th className="px-3 py-3 font-bold text-gray-800">Runs</th>
                  <th className="px-3 py-3">HS</th>
                  <th className="px-3 py-3 font-bold text-gray-800">Ave</th>
                  <th className="px-3 py-3">BF</th>
                  <th className="px-3 py-3">SR</th>
                  <th className="px-3 py-3">100s</th>
                  <th className="px-3 py-3">50s</th>
                  <th className="px-3 py-3">4s</th>
                  <th className="px-3 py-3">6s</th>
                  <th className="px-3 py-3">Ct</th>
                  <th className="px-3 py-3">St</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.batting.map((stat, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-left font-bold text-gray-700">{stat.format}</td>
                    <td className="px-3 py-2.5">{stat.mat}</td>
                    <td className="px-3 py-2.5">{stat.inns}</td>
                    <td className="px-3 py-2.5">{stat.no}</td>
                    <td className="px-3 py-2.5 font-bold text-gray-900">{stat.runs}</td>
                    <td className="px-3 py-2.5">{stat.hs}</td>
                    <td className="px-3 py-2.5 font-bold text-gray-900">{stat.ave}</td>
                    <td className="px-3 py-2.5">{stat.bf}</td>
                    <td className="px-3 py-2.5">{stat.sr}</td>
                    <td className="px-3 py-2.5">{stat["100s"]}</td>
                    <td className="px-3 py-2.5">{stat["50s"]}</td>
                    <td className="px-3 py-2.5">{stat["4s"]}</td>
                    <td className="px-3 py-2.5">{stat["6s"]}</td>
                    <td className="px-3 py-2.5">{stat.ct}</td>
                    <td className="px-3 py-2.5">{stat.st}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* BOWLING STATS */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex justify-between items-center">
            <h2 className="font-bold text-gray-800 text-sm uppercase">Bowling</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-right">
              <thead className="bg-white text-gray-500 text-xs font-semibold border-b">
                <tr>
                  <th className="px-4 py-3 text-left">Format</th>
                  <th className="px-3 py-3">Mat</th>
                  <th className="px-3 py-3">Inns</th>
                  <th className="px-3 py-3">Balls</th>
                  <th className="px-3 py-3">Runs</th>
                  <th className="px-3 py-3 font-bold text-gray-800">Wkts</th>
                  <th className="px-3 py-3">BBI</th>
                  <th className="px-3 py-3">BBM</th>
                  <th className="px-3 py-3 font-bold text-gray-800">Ave</th>
                  <th className="px-3 py-3 font-bold text-gray-800">Econ</th>
                  <th className="px-3 py-3">SR</th>
                  <th className="px-3 py-3">4w</th>
                  <th className="px-3 py-3">5w</th>
                  <th className="px-3 py-3">10w</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.bowling.map((stat, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-left font-bold text-gray-700">{stat.format}</td>
                    <td className="px-3 py-2.5">{stat.mat}</td>
                    <td className="px-3 py-2.5">{stat.inns}</td>
                    <td className="px-3 py-2.5">{stat.balls}</td>
                    <td className="px-3 py-2.5">{stat.runs}</td>
                    <td className="px-3 py-2.5 font-bold text-gray-900">{stat.wkts}</td>
                    <td className="px-3 py-2.5">{stat.bbi}</td>
                    <td className="px-3 py-2.5">{stat.bbm}</td>
                    <td className="px-3 py-2.5 font-bold text-gray-900">{stat.ave}</td>
                    <td className="px-3 py-2.5 font-bold text-gray-900">{stat.econ}</td>
                    <td className="px-3 py-2.5">{stat.sr}</td>
                    <td className="px-3 py-2.5">{stat["4w"]}</td>
                    <td className="px-3 py-2.5">{stat["5w"]}</td>
                    <td className="px-3 py-2.5">{stat["10w"]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
