import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CandidateDetail from "../components/CandidateDetail";
import { fetchCandidates } from "../services/api";

function Analysis() {
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    fetchCandidates().then(setCandidates).catch(() => setCandidates([]));
  }, []);

  const candidateId = searchParams.get("candidate");
  const options = useMemo(
    () => candidates.map((candidate) => ({ value: candidate.id, label: candidate.full_name || candidate.source_file })),
    [candidates]
  );

  useEffect(() => {
    if (!candidates.length) return;
    const match = candidates.find((candidate) => candidate.id === candidateId) || candidates[0];
    setSelectedCandidate(match || null);
    if (!candidateId && match?.id) {
      setSearchParams({ candidate: match.id });
    }
  }, [candidateId, candidates, setSearchParams]);

  const handleSelect = (event) => {
    const value = event.target.value;
    const candidate = candidates.find((item) => item.id === value) || null;
    setSelectedCandidate(candidate);
    if (value) setSearchParams({ candidate: value });
  };

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="pill">Analysis Workspace</p>
            <h2 className="display-font text-xl font-semibold text-slate-900">Candidate Analysis</h2>
            <p className="mt-1 text-sm text-slate-600">
              Dive into educational analysis, professional gaps, and missing-info outreach for each profile.
            </p>
          </div>
          <div className="min-w-[240px]">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Candidate
            </label>
            <select
              value={selectedCandidate?.id || ""}
              onChange={handleSelect}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm shadow-sm"
            >
              {options.length === 0 ? (
                <option value="">No candidates yet</option>
              ) : (
                options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      </section>

      <CandidateDetail candidate={selectedCandidate} />
    </div>
  );
}

export default Analysis;
