import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import Processing from "./pages/Processing";
import Candidates from "./pages/Candidates";
import Analysis from "./pages/Analysis";

const navLinkBase =
  "rounded-full px-4 py-2 text-sm font-semibold uppercase tracking-wider transition duration-300";

function App() {
  return (
    <div className="min-h-screen px-4 pb-12 pt-6 md:px-8">
      <div className="app-backdrop">
        <div className="orb orb-a animate-float" />
        <div className="orb orb-b" />
        <div className="orb orb-c animate-float" />
      </div>

      <div className="mx-auto flex max-w-7xl flex-col gap-10">
        <nav className="panel flex flex-col gap-4 px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p className="pill">Smart HR Recruitment</p>
            <h1 className="display-font text-2xl font-semibold text-slate-900 md:text-3xl">
              TALASH Web Interface
            </h1>
            <p className="text-sm text-slate-600">
              Track CV ingestion, candidate analysis, and missing-information follow-up in one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `${navLinkBase} ${
                  isActive
                    ? "bg-slate-900 text-white"
                    : "bg-white/60 text-slate-700 hover:bg-slate-900 hover:text-white"
                }`
              }
            >
              Overview
            </NavLink>
            <NavLink
              to="/processing"
              className={({ isActive }) =>
                `${navLinkBase} ${
                  isActive
                    ? "bg-talashBlue text-white"
                    : "bg-white/60 text-slate-700 hover:bg-talashBlue hover:text-white"
                }`
              }
            >
              Processing
            </NavLink>
            <NavLink
              to="/candidates"
              className={({ isActive }) =>
                `${navLinkBase} ${
                  isActive
                    ? "bg-talashTeal text-white"
                    : "bg-white/60 text-slate-700 hover:bg-talashTeal hover:text-white"
                }`
              }
            >
              Candidates
            </NavLink>
            <NavLink
              to="/analysis"
              className={({ isActive }) =>
                `${navLinkBase} ${
                  isActive
                    ? "bg-slate-800 text-white"
                    : "bg-white/60 text-slate-700 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              Analysis
            </NavLink>
          </div>
        </nav>

        <main className="flex flex-col gap-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/processing" element={<Processing />} />
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/analysis" element={<Analysis />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
