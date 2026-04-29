import { useEffect, useMemo, useState } from "react";
import { fetchProcessingStatus } from "../services/api";
import StatusBadge from "./StatusBadge";

function ProcessingStatusBoard({ folderPath, refreshKey, isProcessing, compact = false }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      try {
        const data = await fetchProcessingStatus(folderPath);
        if (mounted) {
          setItems(data.items || []);
          setError("");
        }
      } catch (err) {
        if (mounted) setError(err.response?.data?.detail || err.message);
      }
    };

    load();
    if (!isProcessing) return () => {
      mounted = false;
    };

    const interval = setInterval(load, 2000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [folderPath, refreshKey, isProcessing]);

  const counts = useMemo(() => {
    const summary = { awaiting: 0, processing: 0, processed: 0, failed: 0, skipped: 0 };
    items.forEach((item) => {
      const status = item.status || "awaiting";
      if (summary[status] === undefined) summary[status] = 0;
      summary[status] += 1;
    });
    return summary;
  }, [items]);

  return (
    <section className={compact ? "panel-muted p-5" : "panel p-6"}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="pill">Processing Queue</p>
          <h2 className="display-font text-xl font-semibold text-slate-900">
            CV Folder Status
          </h2>
          <p className="text-sm text-slate-600">{folderPath}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-emerald-100 px-3 py-1 font-semibold text-emerald-800">
            Processed: {counts.processed || 0}
          </span>
          <span className="rounded-full bg-blue-100 px-3 py-1 font-semibold text-blue-800">
            Processing: {counts.processing || 0}
          </span>
          <span className="rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-800">
            Awaiting: {counts.awaiting || 0}
          </span>
          <span className="rounded-full bg-rose-100 px-3 py-1 font-semibold text-rose-800">
            Failed: {counts.failed || 0}
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-700">
            Skipped: {counts.skipped || 0}
          </span>
        </div>
      </div>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
      {!error && items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">No CV files detected yet.</p>
      ) : null}
      {!error && items.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-sm">
            <thead className="text-left text-slate-600">
              <tr>
                <th className="px-3 py-2">File</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Last Update</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.file} className="rounded-xl bg-white/70 shadow-sm">
                  <td className="px-3 py-2 font-medium text-slate-800">{item.file}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {item.updated_at || "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default ProcessingStatusBoard;
