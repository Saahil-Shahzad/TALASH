import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCandidates } from "../services/api";

function Dashboard({ refreshKey }) {
  const [candidates, setCandidates] = useState([]);

  useEffect(() => {
    fetchCandidates().then(setCandidates).catch(() => setCandidates([]));
  }, [refreshKey]);

  const chartData = useMemo(() => {
    const total = candidates.length;
    const withEmail = candidates.filter((c) => c.email).length;
    const withSkills = candidates.filter((c) => c.skills_csv).length;
    return [
      { metric: "Total", value: total },
      { metric: "Email", value: withEmail },
      { metric: "Skills", value: withSkills },
    ];
  }, [candidates]);

  return (
    <section className="panel p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="pill">Snapshot</p>
          <h2 className="display-font text-xl font-semibold text-slate-900">Candidate Overview</h2>
        </div>
        <div className="text-right text-sm text-slate-600">
          <p className="font-semibold text-slate-900">{candidates.length}</p>
          <p>Total Profiles</p>
        </div>
      </div>
      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="metric" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="#0C4A6E" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default Dashboard;
