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
    // We fetch from the team matches API as a fallback, but a dedicated /api/player_stats would be ideal.
    // For now we simulate the detailed stat fetch.
    setTimeout(() => {
      setData({
        name: playerName,
        country: "India",
        role: "Top-order batter",
        battingStyle: "Right-hand bat",
        bowlingStyle: "Right-arm medium",
        formats: ["Test", "ODI", "T20I", "FC", "List A", "T20"],
        // Mocking the detailed columns for UI representation until backend strictly supports all 25 columns
        batting: [
          { format: "Test", mat: 113, inns: 191, no: 11, runs: 8848, hs: "254*", ave: 49.15, bf: 15924, sr: 55.56, "100s": 29, "50s": 30, "4s": 991, "6s": 26, ct: 111, st: 0 },
          { format: "ODI", mat: 292, inns: 280, no: 44, runs: 13848, hs: "183", ave: 58.67, bf: 14797, sr: 93.58, "100s": 50, "50s": 72, "4s": 1294, "6s": 151, ct: 151, st: 0 },
          { format: "T20I", mat: 117, inns: 109, no: 31, runs: 4037, hs: "122*", ave: 51.75, bf: 2922, sr: 138.15, "100s": 1, "50s": 37, "4s": 361, "6s": 117, ct: 53, st: 0 },
        ],
        bowling: [
          { format: "Test", mat: 113, inns: 11, balls: 175, runs: 84, wkts: 0, bbi: "-", bbm: "-", ave: "-", econ: 2.88, sr: "-", "4w": 0, "5w": 0, "10w": 0 },
          { format: "ODI", mat: 292, inns: 50, balls: 653, runs: 673, wkts: 5, bbi: "1/15", bbm: "1/15", ave: 134.60, econ: 6.18, sr: 130.6, "4w": 0, "5w": 0, "10w": 0 },
          { format: "T20I", mat: 117, inns: 13, balls: 152, runs: 204, wkts: 4, bbi: "1/13", bbm: "1/13", ave: 51.00, econ: 8.05, sr: 38.0, "4w": 0, "5w": 0, "10w": 0 },
        ]
      });
      setLoading(false);
    }, 500);
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
