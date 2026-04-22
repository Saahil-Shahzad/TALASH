function StatusBadge({ status }) {
  const normalized = status || "awaiting";
  const styles = {
    awaiting: "border-amber-200 bg-amber-50 text-amber-800",
    processing: "border-blue-200 bg-blue-50 text-blue-800",
    processed: "border-emerald-200 bg-emerald-50 text-emerald-800",
    failed: "border-rose-200 bg-rose-50 text-rose-800",
    skipped: "border-slate-200 bg-slate-50 text-slate-700",
  };

  const labelMap = {
    awaiting: "Awaiting",
    processing: "Processing",
    processed: "Processed",
    failed: "Failed",
    skipped: "Skipped",
  };

  const style = styles[normalized] || styles.awaiting;
  const label = labelMap[normalized] || labelMap.awaiting;

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${style}`}>
      {label}
    </span>
  );
}

export default StatusBadge;
