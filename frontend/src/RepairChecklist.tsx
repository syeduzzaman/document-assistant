import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { request } from "./api";
import type { DocumentInfo, Health } from "./api";

type Category = "photos" | "documents" | "approvals";

type Requirement = {
  category: Category;
  action: string;
  citation: { filename: string; page: number; quote: string; revision: string | null };
};

type Checklist = {
  scenario: string;
  requirements: Requirement[];
  manual_checks: string[];
};

type Run = {
  checklist: Checklist;
  example: boolean;
  selection: string;
};

const categories: { key: Category; label: string }[] = [
  { key: "photos", label: "Photos" },
  { key: "documents", label: "Documents" },
  { key: "approvals", label: "Approvals" },
];

export default function RepairChecklist({ documents, mode }: {
  documents: DocumentInfo[];
  mode: Health["mode"] | undefined;
}) {
  const [scenario, setScenario] = useState("");
  const [result, setResult] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const documentIds = documents.map((document) => document.id);
  const selection = [...documentIds].sort().join(",");
  const visibleResult = result && (result.example || result.selection === selection) ? result : null;
  const resultSection = useRef<HTMLElement>(null);

  useEffect(() => {
    if (visibleResult) resultSection.current?.focus();
  }, [visibleResult]);

  async function runChecklist(example: boolean) {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const checklist = example
        ? await request<Checklist>("/repair-checklist/sample")
        : await request<Checklist>("/repair-checklist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario: scenario.trim(), document_ids: documentIds }),
        });
      setResult({ checklist, example, selection });
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!busy && mode === "openai" && documents.length > 0 && documents.length <= 20 && scenario.trim().length >= 10) {
      void runChecklist(false);
    }
  }

  return <div className="repair-workspace">
    <div className="intro">
      <h1>Repair estimate<br /><em>checklist</em></h1>
      <p>Turn workshop procedures into a list of photos, documents and approvals for a repair estimate.</p>
    </div>

    <section className="repair-example" aria-label="Fictional workshop case">
      <div>
        <h2>Front bumper replacement</h2>
        <p>Try a fictional estimate that rises by EUR 450 after teardown. The sample uses the current procedure revisions.</p>
      </div>
      <button className="secondary-button" type="button" disabled={busy || !mode} onClick={() => void runChecklist(true)}>
        Run sample case
      </button>
    </section>

    <section className="question-card repair-form" aria-labelledby="repair-case-heading">
      <div className="card-title"><h2 id="repair-case-heading">Your own repair case</h2></div>
      <p className="repair-scope">
        {mode === "demo" ? "Enable OpenAI mode to generate a checklist from uploaded files."
          : documents.length > 20 ? "Select up to 20 procedure files."
          : documents.length > 0
            ? <>Using only <strong>{documents.map((document) => document.filename).join(", ")}</strong></>
            : "Select the current procedure files in the document library."}
      </p>
      <form onSubmit={submit}>
        <label htmlFor="repair-scenario" className="visually-hidden">Repair scenario</label>
        <textarea id="repair-scenario" value={scenario} maxLength={2000} minLength={10} required disabled={busy}
          placeholder="Describe the repair, the estimate change and any facts that could affect approval."
          onChange={(event) => setScenario(event.target.value)} />
        <div className="composer-footer">
          <span>Verify each requirement against its source.</span>
          <button className="ask-button" type="submit" disabled={
            busy || mode !== "openai" || documents.length === 0 || documents.length > 20 || scenario.trim().length < 10
          }>Generate checklist</button>
        </div>
      </form>
    </section>

    {error && <div role="alert" className="alert">{error}</div>}
    {busy && <p role="status" className="loading"><span className="loading-dot" />Preparing checklist…</p>}
    {visibleResult && <section className="answer-section repair-result" aria-label="Checklist results" tabIndex={-1} ref={resultSection}>
      <div className="answer-title">
        <h2>{visibleResult.example ? "Sample checklist" : "Your repair checklist"}</h2>
      </div>
      <p className="asked-question">{visibleResult.checklist.scenario}</p>
      {categories.map(({ key, label }) => {
        const requirements = visibleResult.checklist.requirements.filter((item) => item.category === key);
        if (requirements.length === 0) return null;
        return <div className="repair-category" key={key}>
          <h3>{label}</h3>
          <ul>
            {requirements.map(({ citation, action }, index) => <li key={index}>
              <p>{action}</p>
              <details className="repair-citation">
                <summary><span>Source</span> {citation.filename} · Page {citation.page}
                  {citation.revision && " · " + citation.revision}</summary>
                <blockquote>{citation.quote}</blockquote>
              </details>
            </li>)}
          </ul>
        </div>;
      })}
      {visibleResult.checklist.manual_checks.length > 0 && <div className="repair-manual">
        <h3>Needs manual confirmation</h3>
        <ul>{visibleResult.checklist.manual_checks.map((check) => <li key={check}>{check}</li>)}</ul>
      </div>}
    </section>}

  </div>;
}
