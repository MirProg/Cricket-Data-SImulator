"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function RecordsHub() {
  const [activeTab, setActiveTab] = useState("batting");
  const [topBatsmen, setTopBatsmen] = useState([]);
  const [topBowlers, setTopBowlers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/records")
      .then(res => res.json())
      .then(data => {
        setTopBatsmen(data.top_run_scorers || []);
        setTopBowlers(data.top_wicket_takers || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="py-6 px-4 bg-[#f8fafc] min-h-screen">
      
      <div className="flex gap-6 max-w-7xl mx-auto">
        {/* Main Content */}
        <div className="flex-grow">
          <div className="bg-white border border-gray-200 rounded shadow-sm">
            <div className="bg-gray-800 text-white border-b border-gray-200 px-6 py-4 flex gap-6">
              <button 
                onClick={() => setActiveTab("batting")}
                className={`font-bold text-lg pb-1 ${activeTab === 'batting' ? 'border-b-2 border-white' : 'text-gray-400 hover:text-gray-200'}`}
              >
                Highest Career Runs
              </button>
              <button 
                onClick={() => setActiveTab("bowling")}
                className={`font-bold text-lg pb-1 ${activeTab === 'bowling' ? 'border-b-2 border-white' : 'text-gray-400 hover:text-gray-200'}`}
              >
                Most Career Wickets
              </button>
            </div>
            
            <div className="p-0">
              {loading ? (
                <div className="p-12 text-center text-gray-500">Calculating records dynamically...</div>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-gray-700 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-3 font-semibold w-16">Rank</th>
                      <th className="px-6 py-3 font-semibold">Player Name</th>
                      <th className="px-6 py-3 font-semibold text-right">{activeTab === 'batting' ? 'Total Runs' : 'Total Wickets'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(activeTab === 'batting' ? topBatsmen : topBowlers).map((player, idx) => (
                      <tr key={idx} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 font-mono text-gray-400">{idx + 1}</td>
                        <td className="px-6 py-4 font-bold text-blue-700">{player.name}</td>
                        <td className="px-6 py-4 font-black text-gray-900 text-right text-lg">
                          {activeTab === 'batting' ? player.bat_runs : player.wickets}
                        </td>
                      </tr>
                    ))}
                    {(activeTab === 'batting' ? topBatsmen : topBowlers).length === 0 && (
                      <tr>
                        <td colSpan="3" className="px-6 py-8 text-center text-gray-500">No records found. Are scorecards extracted yet?</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar (Simplified) */}
        <div className="w-72 flex-shrink-0 flex flex-col gap-6">
          <div className="bg-white border border-gray-200 rounded shadow-sm p-4">
            <h3 className="font-bold text-gray-800 text-sm mb-2">Live AI Calculation</h3>
            <p className="text-xs text-gray-500">
              Unlike static record pages, these stats are calculated dynamically in real-time from the extracted SQLite database tables (ScrapedBatting & ScrapedBowling).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
