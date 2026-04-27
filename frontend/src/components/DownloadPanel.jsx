import { downloadUrl } from "../api";

export default function DownloadPanel({ jobId, status, preview }) {
  if (!status) return null;
  const complete = status.status === "completed";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Pages processed" value={status.pages_processed || status.total_pages || 0} />
        <Stat label="Transactions" value={status.transactions_found || preview?.total || 0} />
        <Stat label="OCR pages" value={status.ocr_pages || 0} />
        <Stat label="Digital pages" value={status.digital_pages || 0} />
      </div>
      {complete && (
        <a
          href={downloadUrl(jobId)}
          className="mt-5 inline-flex rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
        >
          Download Excel
        </a>
      )}
    </section>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-950">{value}</div>
    </div>
  );
}
