export default function ProgressTracker({ status }) {
  if (!status) return null;
  const progress = Math.max(0, Math.min(status.progress || 0, 100));

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Processing</h2>
          <p className="text-sm text-slate-600">{status.message}</p>
        </div>
        <span className="rounded-md bg-slate-100 px-3 py-1 text-sm font-medium capitalize text-slate-700">
          {status.status}
        </span>
      </div>
      <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-[#2447b8] transition-all" style={{ width: `${progress}%` }} />
      </div>
      <div className="mt-3 flex flex-wrap justify-between gap-2 text-sm text-slate-600">
        <span>{progress}% complete</span>
        <span>
          Page {status.current_page || 0} of {status.total_pages || status.page_count || 0}
        </span>
      </div>
    </section>
  );
}
