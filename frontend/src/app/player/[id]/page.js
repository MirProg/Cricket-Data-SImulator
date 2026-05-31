"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function PlayerProfile() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlayer = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/player/${params.id}`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (err) {
        console.error("Failed to fetch player", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlayer();
  }, [params.id]);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading player profile...</div>;
  if (!data || data.error) return <div className="p-12 text-center text-red-500">Player not found.</div>;

  const decodedName = decodeURIComponent(params.id);

  return (
    <div className="py-6 px-4 sm:px-0">
      
      {/* Player Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 flex items-center gap-6">
        <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center text-3xl">
          👤
        </div>
        <div>
          <h1 className="text-3xl font-black text-gray-900">{decodedName}</h1>
          <p className="text-gray-500 font-semibold mt-1">{data.team_name || "National Team"}</p>
        </div>
      </div>

      {/* Career Stats Grid */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden mb-6">
        <div className="bg-gray-100 border-b border-gray-200 px-4 py-3">
          <h3 className="font-bold text-gray-800">Career Statistics (All Formats)</h3>
        </div>
        
        <div className="p-6">
          <h4 className="text-sm font-bold text-gray-500 uppercase mb-4 border-b pb-2">Batting & Fielding</h4>
          <div className="overflow-x-auto mb-8">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3">M</th>
                  <th className="px-4 py-3">Runs</th>
                  <th className="px-4 py-3">HS</th>
                  <th className="px-4 py-3">Avg</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-gray-800">{data.matches}</td>
                  <td className="px-4 py-3 font-bold text-blue-700">{data.bat_runs}</td>
                  <td className="px-4 py-3 text-gray-800">{data.highest_score || '-'}</td>
                  <td className="px-4 py-3 text-gray-800">{data.bat_avg ? data.bat_avg.toFixed(2) : '-'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h4 className="text-sm font-bold text-gray-500 uppercase mb-4 border-b pb-2">Bowling</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3">M</th>
                  <th className="px-4 py-3">Wkts</th>
                  <th className="px-4 py-3">Avg</th>
                  <th className="px-4 py-3">Econ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-gray-800">{data.matches}</td>
                  <td className="px-4 py-3 font-bold text-blue-700">{data.bowl_wickets}</td>
                  <td className="px-4 py-3 text-gray-800">{data.bowl_avg ? data.bowl_avg.toFixed(2) : '-'}</td>
                  <td className="px-4 py-3 text-gray-800">{data.bowl_econ ? data.bowl_econ.toFixed(2) : '-'}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      <Link href="/" className="text-blue-600 hover:underline text-sm font-semibold">&larr; Back to Dashboard</Link>
    </div>
  );
}
