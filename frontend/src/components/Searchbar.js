"use client";

import { useState } from "react";

export default function Searchbar() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setIsOpen(true);
    setResult(null);

    try {
      const res = await fetch("http://localhost:8000/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setResult({ answer: "Error connecting to AI Search Service." });
    }
    setLoading(false);
  };

  return (
    <div className="relative z-50">
      <form onSubmit={handleSearch} className="relative hidden md:block">
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="AskCricDB (e.g. Most runs in Test?)" 
          className="bg-gray-100 text-gray-900 border border-gray-300 rounded-md px-4 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-80 transition-all font-medium"
        />
        <button type="submit" className="absolute right-2 top-1.5 text-gray-400 hover:text-blue-600 transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </button>
      </form>

      {isOpen && (
        <div className="absolute right-0 top-12 w-96 bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden text-sm">
          <div className="p-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex justify-between items-center">
            <h3 className="font-bold flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              AskCricDB AI
            </h3>
            <button onClick={() => setIsOpen(false)} className="text-white hover:text-gray-200">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>
          
          <div className="p-5 max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-6 text-gray-500">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3"></div>
                <p className="animate-pulse font-medium text-xs uppercase tracking-wider">Translating Text to SQL...</p>
              </div>
            ) : result ? (
              <div className="space-y-4">
                <div className="bg-blue-50 border-l-4 border-blue-500 p-3 rounded text-gray-800 leading-relaxed font-medium">
                  {result.answer.split('**').map((text, i) => i % 2 === 1 ? <strong key={i} className="text-blue-700 font-bold">{text}</strong> : text)}
                </div>
                {result.sql && (
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Executed Database Query</p>
                    <div className="bg-gray-900 text-gray-300 p-3 rounded-lg font-mono text-xs overflow-x-auto shadow-inner whitespace-pre-wrap">
                      {result.sql}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
