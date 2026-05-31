"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

export default function LeaguePage() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/league/${params.id}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); });
  }, [params.id]);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading league data...</div>;

  return (
    <div className="py-8 px-4">
      <h1 className="text-3xl font-black mb-2 text-indigo-900">{data.name}</h1>
      <span className="bg-green-100 text-green-800 text-xs font-bold px-3 py-1 rounded-full uppercase">
        {data.status}
      </span>
      <div className="mt-8 bg-white border p-6 rounded-lg shadow-sm">
        <p className="text-gray-500 text-center py-10">Fixtures and Points Table will be populated here.</p>
      </div>
    </div>
  );
}
