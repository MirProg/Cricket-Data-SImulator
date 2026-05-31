"use client";
import { useState } from "react";
import Link from "next/link";

export default function RecordsHub() {
  const [openAccordion, setOpenAccordion] = useState("Most wickets");

  const toggleAccordion = (title) => {
    setOpenAccordion(openAccordion === title ? null : title);
  };

  const recordsData = [
    {
      title: "Most wickets",
      links: [
        "Most wickets in career", "Best figures in an innings", "Best figures in a match",
        "Most wickets in a series", "Most wickets in a calendar year", "Outstanding bowling analyses in an innings",
        "Most wickets on a single ground", "Best figures in a innings by a captain", 
        "Best figures in a match by a captain", "Best figures in a innings when on the losing side", 
        "Best figures in a match when on the losing side"
      ]
    },
    {
      title: "Averages, strike rates and economy",
      links: [
        "Best career bowling average", "Best career economy rate", "Best career strike rate",
        "Best career bowling average (without qualification)", "Best economy rate in an innings",
        "Best strike rate in an innings", "Worst career bowling average", "Worst career economy rate",
        "Worst career strike rate", "Worst career bowling average (without qualification)",
        "Worst economy rate in an innings", "Worst strike rate in an innings"
      ]
    },
    {
      title: "Debuts and last match",
      links: ["Best figures in a innings on debut", "Best figures in a match on debut"]
    },
    {
      title: "Hauls",
      links: [
        "Most five-wickets-in-an-innings in a career", "Most ten-wickets-in-a-match in a career",
        "Most consecutive five-wickets-in-an-innings", "Most consecutive ten-wickets-in-a-match",
        "Youngest player to take five-wickets-in-an-innings", "Youngest player to take ten-wickets-in-a-match",
        "Oldest player to take five-wickets-in-an-innings", "Oldest player to take ten-wickets-in-a-match",
        "Oldest player to take a maiden five-wickets-in-an-innings"
      ]
    },
    {
      title: "Most balls bowled",
      links: ["Most balls bowled in career", "Most balls bowled in an innings", "Most balls bowled in a match"]
    },
    {
      title: "Most runs conceded",
      links: ["Most runs conceded in career", "Most runs conceded in an innings", "Most runs conceded in a match"]
    },
    {
      title: "Hat-tricks and similar",
      links: ["Hat-tricks", "Four wickets in five balls", "Three wickets in four balls"]
    },
    {
      title: "Dismissals",
      links: [
        "Bowler/Batter combinations", "Bowler/fielder combinations", "Most wickets taken bowled",
        "Most wickets taken caught", "Most wickets taken caught and bowled", "Most wickets taken caught by a fielder",
        "Most wickets taken caught by a wicketkeeper", "Most wickets taken lbw", "Most wickets taken stumped",
        "Most wickets taken hit wicket"
      ]
    },
    {
      title: "Miscellaneous",
      links: [
        "Wicket with first ball in career", "Dismissing all eleven batters in a match",
        "Bowlers unchanged in a completed innings", "No-balled for throwing"
      ]
    },
    {
      title: "Fastest career wickets",
      links: [
        "Fastest to 50 wickets", "Fastest to 100 wickets", "Fastest to 150 wickets", "Fastest to 200 wickets",
        "Fastest to 250 wickets", "Fastest to 300 wickets", "Fastest to 350 wickets", "Fastest to 400 wickets",
        "Fastest to 450 wickets", "Fastest to 500 wickets", "Fastest to 600 wickets", "Fastest to 700 wickets",
        "Fastest to 750 wickets", "Fastest to 800 wickets"
      ]
    }
  ];

  return (
    <div className="py-6 px-4 bg-[#f8fafc] min-h-screen">
      
      <div className="flex gap-6 max-w-7xl mx-auto">
        {/* Main Content (Accordions) */}
        <div className="flex-grow">
          <div className="bg-white border border-gray-200 rounded shadow-sm">
            <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
              <h2 className="font-bold text-gray-800 text-lg">Bowling records</h2>
            </div>
            
            <div className="divide-y divide-gray-100">
              {recordsData.map((category, idx) => (
                <div key={idx} className="bg-white">
                  <button 
                    onClick={() => toggleAccordion(category.title)}
                    className="w-full flex justify-between items-center px-4 py-3 text-left hover:bg-gray-50"
                  >
                    <span className="text-xs font-black text-gray-700 tracking-wider uppercase">
                      {category.title}
                    </span>
                    <span className="text-gray-400 text-xs">
                      {openAccordion === category.title ? "▲" : "▼"}
                    </span>
                  </button>
                  
                  {openAccordion === category.title && (
                    <div className="bg-white border-t border-gray-100">
                      <ul className="divide-y divide-gray-50">
                        {category.links.map((link, linkIdx) => (
                          <li key={linkIdx}>
                            <Link 
                              href={`/records/query?type=${encodeURIComponent(link)}`}
                              className="block px-6 py-2.5 text-sm text-blue-600 hover:underline hover:bg-blue-50"
                            >
                              {link}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="w-72 flex-shrink-0 flex flex-col gap-6">
          
          {/* Categories Sidebar */}
          <div className="bg-white border border-gray-200 rounded shadow-sm">
            <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
              <h3 className="font-bold text-gray-800 text-sm">Test matches</h3>
            </div>
            <ul className="text-sm divide-y divide-gray-50">
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">Team records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">Batting records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 font-bold bg-blue-50 text-blue-700 cursor-pointer border-l-4 border-blue-600">Bowling records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">Wicketkeeping records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">Fielding records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">All-round records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">Partnership records</li>
              <li className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">Individual records (captains, players, umpires)</li>
            </ul>
          </div>

          {/* Overall Records Sidebar */}
          <div className="bg-white border border-gray-200 rounded shadow-sm">
            <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
              <h3 className="font-bold text-gray-800 text-sm">Overall Records</h3>
            </div>
            <ul className="text-sm divide-y divide-gray-50 text-blue-600">
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">Test</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">ODI</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">T20I</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">FC</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">LA</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">T20</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">Women Test</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">Women ODI</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">Women T20I</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">Test+ODI+T20I</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">FC+LA+T20</li>
              <li className="px-4 py-2 hover:bg-blue-50 cursor-pointer hover:underline">All</li>
            </ul>
          </div>

        </div>
      </div>
    </div>
  );
}
