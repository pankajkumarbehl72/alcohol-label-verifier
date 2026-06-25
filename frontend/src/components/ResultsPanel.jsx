function statusIcon(status) {
  if (status === "PASS") return "✅";
  if (status === "WARNING") return "⚠️";
  return "❌";
}

function statusLabel(status) {
  if (status === "PASS") return "Pass";
  if (status === "WARNING") return "Needs Review";
  return "Fail";
}

export default function ResultsPanel({ result, error, isLoading }) {
  if (isLoading) {
    return (
      <section className="card results-card">
        <h2>Review Results</h2>
        <div className="loading">Processing label...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="card results-card">
        <h2>Review Results</h2>
        <div className="error">{error}</div>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="card results-card empty">
        <h2>Review Results</h2>
        <p>Results will appear here after you upload and verify a label.</p>
      </section>
    );
  }

  return (
    <section className="card results-card">
      <div className={`overall ${result.overall_status.toLowerCase()}`}>
        <span className="overall-icon">{statusIcon(result.overall_status)}</span>
        <div>
          <p className="eyebrow">Overall Result</p>
          <h2>{statusLabel(result.overall_status)}</h2>
          <p className="helper">
            Completed in {result.processing_time_seconds} seconds using{" "}
            {result.extracted_fields.extraction_method}.
          </p>
        </div>
      </div>

      <h3>Field Checks</h3>
      <div className="checks">
        {result.checks.map((check) => (
          <article className={`check ${check.status.toLowerCase()}`} key={check.field}>
            <div className="check-header">
              <strong>{statusIcon(check.status)} {check.field}</strong>
              <span>{statusLabel(check.status)}</span>
            </div>
            <p>{check.message}</p>
            <dl>
              <dt>Expected</dt>
              <dd>{check.expected || "—"}</dd>
              <dt>Found</dt>
              <dd>{check.found || "—"}</dd>
              <dt>Score</dt>
              <dd>{check.score ?? "—"}</dd>
            </dl>
          </article>
        ))}
      </div>

      <details className="raw">
        <summary>Show extracted fields</summary>
        <pre>{JSON.stringify(result.extracted_fields, null, 2)}</pre>
      </details>
    </section>
  );
}
