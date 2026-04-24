import { useEffect, useState } from "react";
import CandidateDetail from "../components/CandidateDetail";
import CandidateTable from "../components/CandidateTable";
import { fetchProcessingStatus } from "../services/api";

const DEFAULT_FOLDER = "backend/data/raw_cvs";

function Candidates() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [statusMap, setStatusMap] = useState({});
  const [statusError, setStatusError] = useState("");

  useEffect(() => {
    fetchProcessingStatus(DEFAULT_FOLDER)
      .then((data) => {
        const map = {};
        (data.items || []).forEach((item) => {
          if (item.file) map[item.file] = item.status;
        });
        setStatusMap(map);
        setStatusError("");
      })
      .catch((err) => setStatusError(err.response?.data?.detail || err.message));
  }, [refreshKey]);

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="pill">Candidate Registry</p>
            <h2 className="display-font text-xl font-semibold text-slate-900">Candidates</h2>
            <p className="mt-1 text-sm text-slate-600">
              Review extracted profiles and verify processing status before analysis.
            </p>
          </div>
          <button
            onClick={() => setRefreshKey((value) => value + 1)}
            className="rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:bg-white"
          >
            Refresh Table
          </button>
        </div>
        {statusError ? <p className="mt-3 text-sm text-rose-600">{statusError}</p> : null}
      </section>

      <CandidateTable
        refreshKey={refreshKey}
        onSelectCandidate={setSelectedCandidate}
        statusMap={statusMap}
      />

      <CandidateDetail candidate={selectedCandidate} />
    </div>
  );
}

export default Candidates;
