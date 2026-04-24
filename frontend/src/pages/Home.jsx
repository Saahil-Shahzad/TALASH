import { useState } from "react";
import { Link } from "react-router-dom";
import Dashboard from "../components/Dashboard";
import ProcessingStatusBoard from "../components/ProcessingStatusBoard";

const DEFAULT_FOLDER = "backend/data/raw_cvs";

function Home() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="grid gap-6">
      <section className="panel p-6 animate-rise">
        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="pill">Milestone 2 Ready</p>
            <h2 className="display-font text-3xl font-semibold text-slate-900">
              Smart HR Recruitment, Fully Instrumented
            </h2>
            <p className="mt-3 text-sm text-slate-600">
              Monitor ingestion, track processing progress, and review candidate readiness with instant
              summaries and missing-information alerts.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/processing"
                className="rounded-full bg-talashBlue px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-sky-200/60 transition hover:-translate-y-0.5 hover:bg-sky-900"
              >
                Start Processing
              </Link>
              <Link
                to="/candidates"
                className="rounded-full border border-slate-200 bg-white/70 px-5 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-white"
              >
                Review Candidates
              </Link>
            </div>
          </div>
          {/* <div className="panel-muted p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Milestone 2 Checklist</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              <li>Folder-based CV ingestion with monitoring</li>
              <li>Educational + professional profile analysis</li>
              <li>Missing-info detection and email drafting</li>
              <li>Initial charts, tabular outputs, and summaries</li>
            </ul>
          </div> */}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <Dashboard refreshKey={refreshKey} />
        <ProcessingStatusBoard
          folderPath={DEFAULT_FOLDER}
          refreshKey={refreshKey}
          isProcessing={false}
          compact
        />
      </section>

      <section className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="pill">Quick Actions</p>
            <h3 className="display-font text-xl font-semibold text-slate-900">Refresh the Live Snapshot</h3>
            <p className="mt-1 text-sm text-slate-600">
              Pull the latest candidates and processing status in one click.
            </p>
          </div>
          <button
            onClick={() => setRefreshKey((value) => value + 1)}
            className="rounded-full border border-slate-200 bg-white/80 px-5 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-white"
          >
            Refresh Dashboard
          </button>
        </div>
      </section>
    </div>
  );
}

export default Home;
