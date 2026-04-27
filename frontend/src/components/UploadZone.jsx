import { useRef, useState } from "react";

function formatBytes(bytes = 0) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export default function UploadZone({ onUpload, fileInfo, disabled }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (file) => {
    if (file && file.type === "application/pdf") onUpload(file);
  };

  return (
    <section
      className={`rounded-lg border-2 border-dashed bg-white p-8 shadow-sm transition ${
        isDragging ? "border-[#2447b8] bg-blue-50" : "border-slate-300"
      } ${disabled ? "opacity-70" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        handleFile(event.dataTransfer.files?.[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        disabled={disabled}
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-[#2447b8] text-2xl font-bold text-white shadow-lg">
          PDF
        </div>
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">Upload your bank statement</h2>
          <p className="mt-1 text-sm text-slate-600">Drag a file here or choose a PDF up to 200 pages.</p>
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="rounded-md bg-[#2447b8] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1d3892] disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          Choose PDF
        </button>
      </div>
      {fileInfo && (
        <div className="mt-6 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 sm:grid-cols-3">
          <div>
            <span className="block text-xs font-semibold uppercase text-slate-500">File</span>
            <span className="break-words">{fileInfo.file_name}</span>
          </div>
          <div>
            <span className="block text-xs font-semibold uppercase text-slate-500">Size</span>
            {formatBytes(fileInfo.file_size)}
          </div>
          <div>
            <span className="block text-xs font-semibold uppercase text-slate-500">Pages</span>
            {fileInfo.page_count}
          </div>
        </div>
      )}
    </section>
  );
}
