import { useState } from "react";
import { processFolder } from "../services/api";

function Upload({ folderPath, onFolderPathChange, onProcessed, onProcessingStateChange }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    onProcessingStateChange?.(true);
    try {
      const data = await processFolder(folderPath, true);
      setResult(data);
      onProcessed?.(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
      onProcessingStateChange?.(false);
    }
  };

  return (
    <section className="panel p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="pill">Folder Monitoring</p>
          <h2 className="display-font text-xl font-semibold text-slate-900">CV Folder Processing</h2>
          <p className="mt-1 text-sm text-slate-600">
            Point to the folder that contains new CV PDFs and trigger a processing run.
          </p>
        </div>
      </div>
      <form onSubmit={handleSubmit} className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto]">
        <input
          value={folderPath}
          onChange={(e) => onFolderPathChange?.(e.target.value)}
          placeholder="Absolute or relative folder path containing PDFs"
          className="w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-talashBlue px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-200/60 transition hover:-translate-y-0.5 hover:bg-sky-900 disabled:opacity-60"
        >
          {loading ? "Processing..." : "Process Folder"}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      {result ? (
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
            Processed: {result.processed_count}
          </div>
          <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-700">
            Skipped: {result.skipped_count}
          </div>
          <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            Failed: {result.failed_count}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default Upload;
