"use client";
import { useState } from "react";
import Link from "next/link";

const categories = [
  {
    title: "Current Matches",
    links: [
      { label: "Current & Future Series", href: "/series" },
      { label: "Matches By Day", href: "/matches/day" },
      { label: "Teams", href: "/teams" }
    ]
  },
  {
    title: "Series Archive",
    links: [
      { label: "Cricket Match Archives", href: "/archives" },
      { label: "2026", href: "/archives/2026" }
    ]
  },
  {
    title: "International",
    links: [
      { label: "Asian Games Qualifier 2026", href: "/series/asian-games" },
      { label: "Australia tour of Pakistan 2026", href: "/series/aus-pak" },
      { label: "New Zealand tour of Ireland 2026", href: "/series/nz-ire" },
      { label: "ICC Men's T20 World Cup 2026", href: "/series/t20-wc" }
      // Truncated for brevity, dynamic in production
    ]
  },
  {
    title: "League",
    links: [
      { label: "T20 Blast 2026", href: "/league/t20-blast" },
      { label: "Indian Premier League 2026", href: "/league/ipl" },
      { label: "Pakistan Super League 2026", href: "/league/psl" }
    ]
  },
  {
    title: "Seasons",
    links: [
      { label: "2020s", href: "/seasons/2020s" },
      { label: "2010s", href: "/seasons/2010s" },
      { label: "2000s", href: "/seasons/2000s" },
      { label: "1990s", href: "/seasons/1990s" },
      { label: "1870s", href: "/seasons/1870s" }
    ]
  },
  {
    title: "Teams",
    links: [
      { label: "India", href: "/team/india" },
      { label: "Australia", href: "/team/australia" },
      { label: "England", href: "/team/england" },
      { label: "Pakistan", href: "/team/pakistan" },
      { label: "South Africa", href: "/team/south-africa" },
      { label: "New Zealand", href: "/team/new-zealand" }
    ]
  },
  {
    title: "Cricket Records",
    links: [
      { label: "Test matches", href: "/records/test" },
      { label: "One-Day Internationals", href: "/records/odi" },
      { label: "T20I", href: "/records/t20i" },
      { label: "Other Formats", href: "/records/other" }
    ]
  },
  {
    title: "Trophies",
    links: [
      { label: "Border-Gavaskar Trophy", href: "/trophy/bgt" },
      { label: "The Ashes", href: "/trophy/ashes" },
      { label: "Asia Cup", href: "/trophy/asia-cup" }
    ]
  }
];

export default function Sidebar() {
  const [openSections, setOpenSections] = useState({
    "Current Matches": true,
    "International": true,
    "Cricket Records": true
  });

  const toggleSection = (title) => {
    setOpenSections(prev => ({ ...prev, [title]: !prev[title] }));
  };

  return (
    <aside className="w-64 flex-shrink-0 bg-white border-r border-gray-200 min-h-screen hidden lg:block overflow-y-auto">
      <div className="py-4">
        {categories.map((category) => (
          <div key={category.title} className="mb-2">
            <button
              onClick={() => toggleSection(category.title)}
              className="w-full flex items-center justify-between px-4 py-2 text-sm font-bold text-gray-800 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              {category.title}
              <span className="text-gray-400 text-xs">{openSections[category.title] ? '▼' : '▶'}</span>
            </button>
            
            {openSections[category.title] && (
              <ul className="py-1">
                {category.links.map(link => (
                  <li key={link.label}>
                    <Link 
                      href={link.href}
                      className="block px-6 py-1.5 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
