import { useEffect, useState } from "react";
import { getPreview, getStatus, uploadPdf } from "./api";
import DownloadPanel from "./components/DownloadPanel";
import ProgressTracker from "./components/ProgressTracker";
import TransactionPreview from "./components/TransactionPreview";
import UploadZone from "./components/UploadZone";

const emptyUser = { name: "", number: "", email: "" };

function getSavedUser() {
  try {
    return JSON.parse(localStorage.getItem("bankscanUser") || "null");
  } catch {
    return null;
  }
}

export default function App() {
  const [user, setUser] = useState(getSavedUser());
  const [jobId, setJobId] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [status, setStatus] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  function handleLogin(nextUser) {
    localStorage.setItem("bankscanUser", JSON.stringify(nextUser));
    setUser(nextUser);
  }

  async function handleUpload(file) {
    setError("");
    setPreview(null);
    setStatus(null);
    setIsUploading(true);
    try {
      const uploaded = await uploadPdf(file);
      setFileInfo(uploaded);
      setJobId(uploaded.job_id);
      setStatus({ status: "queued", progress: 0, message: "Queued for processing...", total_pages: uploaded.page_count });
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed. Please try another PDF.");
    } finally {
      setIsUploading(false);
    }
  }

  useEffect(() => {
    if (!jobId) return undefined;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const nextStatus = await getStatus(jobId);
        if (cancelled) return;
        setStatus(nextStatus);
        if (nextStatus.status === "failed") {
          setError(nextStatus.error || "Processing failed.");
          clearInterval(timer);
        }
        if (nextStatus.status === "completed") {
          clearInterval(timer);
          const nextPreview = await getPreview(jobId);
          if (!cancelled) setPreview(nextPreview);
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || "Unable to fetch job status.");
      }
    }, 1200);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [jobId]);

  if (!user) return <LoginPage onLogin={handleLogin} />;

  return (
    <main className="min-h-screen bg-[#eef4fb]">
      <div className="overflow-hidden bg-[#2447b8] text-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1fr_390px] lg:px-8">
          <div className="flex min-h-[320px] flex-col justify-between">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-200">BankScan Pro</p>
                <h1 className="mt-4 max-w-2xl text-4xl font-bold leading-tight sm:text-5xl">
                  Smart bank statement analysis
                </h1>
              </div>
              <button
                type="button"
                onClick={() => {
                  localStorage.removeItem("bankscanUser");
                  setUser(null);
                }}
                className="hidden rounded-md border border-white/20 px-3 py-2 text-sm font-semibold text-white hover:bg-white/10 sm:block"
              >
                Change user
              </button>
            </div>
            <div>
              <p className="mt-5 max-w-2xl text-base leading-7 text-blue-100">
                Upload your PDF, protect debit and credit columns, preview clean transactions, and export a professional Excel workbook.
              </p>
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <MiniStat value="1004" label="rows tested" />
                <MiniStat value="43" label="pages handled" />
                <MiniStat value="XLSX" label="ready output" />
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="rounded-[32px] border border-white/15 bg-slate-950 p-4 shadow-2xl">
              <div className="mx-auto mb-4 h-7 w-28 rounded-full bg-black" />
              <div className="rounded-[24px] bg-[#152055] p-5">
                <div className="rounded-2xl border border-cyan-300/30 bg-cyan-300/10 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200">Welcome</p>
                  <h2 className="mt-3 text-2xl font-bold leading-snug">Hi {user.name}</h2>
                  <p className="mt-3 text-sm leading-6 text-blue-100">
                    This is Mimshad Uddin, the builder of this site. Hope this site helps you on your bank analysis.
                  </p>
                </div>
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-white p-4 text-slate-950">
                    <p className="text-xs font-semibold uppercase text-slate-500">Debit safety</p>
                    <p className="mt-2 text-2xl font-bold text-red-600">DR</p>
                  </div>
                  <div className="rounded-2xl bg-white p-4 text-slate-950">
                    <p className="text-xs font-semibold uppercase text-slate-500">Credit safety</p>
                    <p className="mt-2 text-2xl font-bold text-emerald-600">CR</p>
                  </div>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                localStorage.removeItem("bankscanUser");
                setUser(null);
              }}
              className="mt-4 rounded-md border border-white/20 px-3 py-2 text-sm font-semibold text-white hover:bg-white/10 sm:hidden"
            >
              Change user
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        <section className="grid gap-4 md:grid-cols-3">
          <InfoCard title="Hybrid reading" body="Digital PDF tables are read first, with OCR fallback for scanned pages." />
          <InfoCard title="Debit/Credit protection" body="Bank columns are preserved so withdrawals and deposits stay on the correct side." />
          <InfoCard title="Excel ready" body="Download a formatted workbook with totals, preview rows, and summary metrics." />
        </section>

        <UploadZone onUpload={handleUpload} fileInfo={fileInfo} disabled={isUploading || status?.status === "processing"} />

        {error && (
          <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <strong className="font-semibold">Error:</strong> {error}
          </section>
        )}

        <ProgressTracker status={status} />
        <DownloadPanel jobId={jobId} status={status} preview={preview} />

        {status?.warnings?.length > 0 && (
          <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
            <h2 className="font-semibold">Validation warnings</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {status.warnings.slice(0, 10).map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </section>
        )}

        <TransactionPreview preview={preview} />
      </div>
    </main>
  );
}

function LoginPage({ onLogin }) {
  const [form, setForm] = useState(emptyUser);
  const [error, setError] = useState("");

  function submit(event) {
    event.preventDefault();
    if (!form.name.trim() || !form.number.trim() || !form.email.trim()) {
      setError("Please enter your name, number, and email address.");
      return;
    }
    onLogin({
      name: form.name.trim(),
      number: form.number.trim(),
      email: form.email.trim(),
    });
  }

  return (
    <main className="min-h-screen bg-[#eef4fb] px-4 py-8 text-slate-950">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[36px] bg-[#2447b8] p-8 text-white shadow-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-200">BankScan Pro</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">
            Clean bank statement analysis, ready for Excel.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-blue-100">
            Upload PDF statements, preserve debit and credit columns, preview transactions, and export a polished workbook for analysis.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <MiniStat value="200" label="page PDF support" />
            <MiniStat value="OCR" label="for scanned pages" />
            <MiniStat value="XLSX" label="formatted export" />
          </div>
          <div className="mt-8 rounded-[28px] border border-white/15 bg-slate-950 p-4">
            <div className="mx-auto mb-4 h-6 w-24 rounded-full bg-black" />
            <div className="rounded-2xl bg-white/10 p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-200">Analysis dashboard</p>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-white p-4 text-slate-950">
                  <p className="text-xs font-semibold uppercase text-slate-500">Withdraw</p>
                  <p className="mt-2 text-2xl font-bold text-red-600">DR</p>
                </div>
                <div className="rounded-xl bg-white p-4 text-slate-950">
                  <p className="text-xs font-semibold uppercase text-slate-500">Deposit</p>
                  <p className="mt-2 text-2xl font-bold text-emerald-600">CR</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white p-6 text-slate-950 shadow-2xl">
          <h2 className="text-2xl font-bold">Enter your details</h2>
          <p className="mt-1 text-sm text-slate-600">This helps personalize your BankScan Pro workspace.</p>
          <form className="mt-6 flex flex-col gap-4" onSubmit={submit}>
            <Field label="Name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} placeholder="Enter your name" />
            <Field label="Number" value={form.number} onChange={(value) => setForm({ ...form, number: value })} placeholder="Enter your mobile number" />
            <Field label="Email address" type="email" value={form.email} onChange={(value) => setForm({ ...form, email: value })} placeholder="Enter your email" />
            {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            <button type="submit" className="rounded-md bg-cyan-700 px-4 py-3 text-sm font-semibold text-white hover:bg-cyan-800">
              Continue to BankScan Pro
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
      />
    </label>
  );
}

function InfoCard({ title, body }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="font-semibold text-slate-950">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

function MiniStat({ value, label }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-4">
      <div className="text-2xl font-bold text-cyan-200">{value}</div>
      <div className="mt-1 text-sm text-slate-300">{label}</div>
    </div>
  );
}
