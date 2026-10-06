export default function Home() {
  const panels = [
    "NQTS Equity", "NQTS Monitoring", "Account Health", "Canary Status",
    "Deploy Slots", "Studio Experiments", "Validations", "Ladder State", "Approvals",
  ];
  return (
    <main style={{ padding: 24 }}>
      <h1>NestQuant Admin</h1>
      <p style={{ color: "var(--accent)" }}>Unified operator view — NQTS ops + Studio admin (placeholder).</p>
      <div className="grid">
        {panels.map((p) => (
          <div key={p} className="card">
            <h3 style={{ marginTop: 0 }}>{p}</h3>
            <p style={{ color: "var(--accent)" }}>coming soon</p>
          </div>
        ))}
      </div>
    </main>
  );
}
