function money(value) {
  if (value === null || value === undefined) return "";
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function TransactionPreview({ preview }) {
  if (!preview?.transactions?.length) return null;

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 p-5">
        <h2 className="text-lg font-semibold text-slate-950">Transaction Preview</h2>
        <p className="text-sm text-slate-600">Showing first {preview.transactions.length} of {preview.total} rows.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-900 text-white">
            <tr>
              {["TRANSACTION DATE", "PARTICULARS", "WITHDRAW", "DEPOSIT", "BALANCE"].map((header) => (
                <th key={header} className="px-4 py-3 text-left font-semibold">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {preview.transactions.map((tx, index) => (
              <tr key={`${tx.transaction_date}-${index}`} className={index % 2 ? "bg-slate-50" : "bg-white"}>
                <td className="whitespace-nowrap px-4 py-3">{tx.transaction_date}</td>
                <td className="min-w-80 px-4 py-3">{tx.particulars}</td>
                <td className="whitespace-nowrap px-4 py-3 text-red-700">{money(tx.withdraw)}</td>
                <td className="whitespace-nowrap px-4 py-3 text-emerald-700">{money(tx.deposit)}</td>
                <td className="whitespace-nowrap px-4 py-3">{money(tx.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
