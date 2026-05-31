"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

export default function SeriesPage() {
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/series")
      .then(r => r.json())
      .then(d => { setSeries(d); setLoading(false); });
  }, []);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading series...</div>;

  return (
    <div className="py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Current & Future Series</h1>
      <div className="bg-white border rounded-lg shadow-sm">
        <ul className="divide-y">
          {series.map(s => (
            <li key={s.id} className="p-4 hover:bg-gray-50">
              <div className="font-bold text-blue-700">{s.name}</div>
              <div className="text-sm text-gray-500">{s.date}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
