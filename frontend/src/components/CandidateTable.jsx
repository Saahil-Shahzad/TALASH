import { useEffect, useState } from "react";
import { fetchCandidates } from "../services/api";
import StatusBadge from "./StatusBadge";

function CandidateTable({ refreshKey, onSelectCandidate, statusMap = {} }) {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchCandidates()
      .then((rows) => {
        if (mounted) setCandidates(rows);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [refreshKey]);

  return (
    <section className="panel p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="pill">Candidate Registry</p>
          <h2 className="display-font text-xl font-semibold text-slate-900">Candidate List</h2>
        </div>
      </div>
      {loading ? <p className="mt-3 text-sm text-slate-600">Loading candidates...</p> : null}
      {!loading && candidates.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">No candidates found yet.</p>
      ) : null}
      {!loading && candidates.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-sm">
            <thead>
              <tr className="text-left text-slate-600">
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Skills</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((row) => {
                const status = statusMap[row.source_file] || "processed";
                return (
                  <tr key={row.id} className="rounded-xl bg-white/80 shadow-sm">
                    <td className="px-3 py-2 text-xs text-slate-500">{row.id}</td>
                    <td className="px-3 py-2 font-medium text-slate-800">{row.full_name || "-"}</td>
                    <td className="px-3 py-2 text-slate-600">{row.email || "-"}</td>
                    <td className="px-3 py-2 text-slate-600">{row.skills_csv || "-"}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={status} />
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => onSelectCandidate?.(row)}
                        className="rounded-full bg-talashTeal px-4 py-1 text-xs font-semibold text-white transition hover:bg-emerald-900"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default CandidateTable;
