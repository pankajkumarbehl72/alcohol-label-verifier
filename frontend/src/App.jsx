import { useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import ResultsPanel from "./components/ResultsPanel.jsx";
import { verifyLabel } from "./api/client.js";

export default function App() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleVerify(formValues, file) {
    setError("");
    setResult(null);
    setIsLoading(true);

    try {
      const data = await verifyLabel(formValues, file);
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Prototype</p>
          <h1>AI-Powered Alcohol Label Verification Assistant</h1>
          <p className="subtitle">
            Upload a label image, enter application fields, and get a clear pass / warning / fail review.
          </p>
        </div>
      </section>

      <section className="layout">
        <UploadForm onVerify={handleVerify} isLoading={isLoading} />
        <ResultsPanel result={result} error={error} isLoading={isLoading} />
      </section>
    </main>
  );
}
