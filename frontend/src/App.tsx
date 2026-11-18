import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { request } from "./api";
import RepairChecklist from "./RepairChecklist";
import type { Answer, DocumentInfo, Health } from "./api";

const suggestions = [
  "How many days of annual leave do employees receive?",
  "What is the first response target for a P1 incident?",
  "How often do database backups run?",
];

function Mark({ small = false }: { small?: boolean }) {
  return <svg width={small ? 22 : 42} height={small ? 22 : 42} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <rect width="40" height="40" rx="11" fill="#2563eb" />
    <path d="M12 9h11l6 6v16H12V9Z" stroke="white" strokeWidth="2" strokeLinejoin="round" />
    <path d="M23 9v7h6M17 22h7M17 27h5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="31" cy="9" r="5" fill="#38bdf8" />
  </svg>;
}

function FileGlyph() {
  return <svg width="20" height="22" viewBox="0 0 20 22" fill="none" aria-hidden="true">
    <path d="M4 1h8l5 5v15H4V1Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    <path d="M12 1v6h5M8 11h5M8 15h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>;
}

export default function App() {
  const [workspace, setWorkspace] = useState<"questions" | "repair">("questions");
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState<"upload" | "ask" | "delete" | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  async function refresh() {
    const [status, files] = await Promise.all([
      request<Health>("/health"), request<DocumentInfo[]>("/documents"),
    ]);
    setHealth(status);
    setDocuments(files);
    return files;
  }

  useEffect(() => {
    refresh().catch((cause: Error) => setError(cause.message));
  }, []);

  async function upload(file: File | undefined) {
    if (!file) return;
    if (file.size > (health?.max_upload_bytes ?? 10 * 1024 * 1024)) {
      setError("Please choose a file smaller than 10 MiB.");
      return;
    }
    setBusy("upload");
    setError("");
    setNotice("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await request<{ document: DocumentInfo; created: boolean }>("/documents", { method: "POST", body });
      await refresh();
      setNotice(result.created ? file.name + " is ready to search." : "This document has already been added.");
      setAnswer(null);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function removeDocument(document: DocumentInfo) {
    if (!window.confirm('Delete "' + document.filename + '" and its searchable passages?')) return;
    setBusy("delete");
    setError("");
    try {
      await request<void>("/documents/" + document.id, { method: "DELETE" });
      setSelected((current) => current.filter((id) => id !== document.id));
      setAnswer(null);
      await refresh();
      setNotice("Document deleted.");
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    setBusy("ask");
    setError("");
    setNotice("");
    setAnswer(null);
    setAsked(question.trim());
    try {
      const result = await request<Answer>("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), document_ids: selected, top_k: 3 }),
      });
      setAnswer(result);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(null);
    }
  }

  function chooseSuggestion(value: string) {
    setQuestion(value);
    textarea.current?.focus();
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="Document Assistant home"><Mark /><span>Document<br /><b>Assistant</b></span></a>
      <div className="workspace-label">YOUR WORKSPACE</div>
      <div className="library-heading"><h2>Documents</h2><span className="count">{documents.length}</span></div>
      <p className="sidebar-description">{workspace === "repair"
        ? "Select the current procedure files for your repair case."
        : "Add your files. Find the answers inside."}</p>
      <input ref={fileInput} id="document-upload" className="visually-hidden" type="file" accept=".pdf,.txt,.md"
        aria-label="Upload document" disabled={!!busy} onChange={(event) => upload(event.target.files?.[0])} />
      <button className="upload-button" disabled={!!busy} onClick={() => fileInput.current?.click()}>
        <span aria-hidden="true">＋</span>{busy === "upload" ? "Adding document…" : "Add a document"}
      </button>
      <p className="file-hint">PDF, TXT or Markdown · Up to 10 MiB</p>
      <div className="document-list" aria-label="Document library">
        {documents.map((document) => <div className="document-row" key={document.id}>
          <label title={document.filename}>
            <input type="checkbox" checked={selected.includes(document.id)} disabled={!!busy}
              onChange={() => {
                setAnswer(null);
                setSelected((current) => current.includes(document.id)
                  ? current.filter((id) => id !== document.id) : [...current, document.id]);
              }} />
            <span className="file-icon"><FileGlyph /></span>
            <span className="document-text"><strong>{document.filename}</strong>
              <small>{document.chunk_count} {document.chunk_count === 1 ? "passage" : "passages"} · {Math.max(1, Math.round(document.byte_size / 1024))} KB</small>
            </span>
          </label>
          <button className="delete-button" aria-label={"Delete " + document.filename} disabled={!!busy}
            onClick={() => removeDocument(document)}>×</button>
        </div>)}
        {documents.length === 0 && <p className="empty-library">Your documents will appear here.</p>}
      </div>
      {selected.length > 0 && <button className="text-button" disabled={!!busy}
        onClick={() => { setSelected([]); setAnswer(null); }}>Clear selection</button>}
      <div className="privacy-note">
        <span className="privacy-symbol" aria-hidden="true">◈</span>
        <strong>{health?.mode === "openai" ? "OpenAI mode" : health ? "Local demo mode" : "Connecting…"}</strong>
        <p>{health?.mode === "openai"
          ? "Document text and questions are sent to OpenAI for embeddings and answers."
          : "Search and extract passages locally. No API key needed."}</p>
      </div>
    </aside>

    <main>
      <header className="topbar">
        <span className="topbar-title"><span className="workspace-icon" aria-hidden="true">▦</span>Workspace<span className="topbar-divider" aria-hidden="true">/</span><strong>Documents</strong></span>
        <div className="workspace-status">
        <span className="indexed-count">{documents.length} {documents.length === 1 ? "document" : "documents"} indexed</span>
        <span className={"mode-badge " + (health ? "" : "connecting")}>
          <i aria-hidden="true" />{health ? health.mode === "demo" ? "Retrieval demo" : "AI answers" : "Connecting"}
        </span>
        </div>
      </header>
      <div className="main-content">
        <nav className="workspace-switch" aria-label="Workspace">
          <button type="button" aria-pressed={workspace === "questions"} onClick={() => setWorkspace("questions")}>
            Document Q&A
          </button>
          <button type="button" aria-pressed={workspace === "repair"} onClick={() => setWorkspace("repair")}>
            Repair Estimate Checklist
          </button>
        </nav>

        {workspace === "questions" && <div className="intro">
          <span className="eyebrow"><span aria-hidden="true">✦</span> ASK. EXPLORE. VERIFY.</span>
          <h1>Your documents.<br /><em>Clear answers.</em></h1>
          <p>Turn your files into answers you can verify.<br className="desktop-break" /> Every result leads back to the source.</p>
        </div>}

        {error && <div role="alert" className="alert">
          <span>{error}</span>
          {!health && <button onClick={() => { setError(""); refresh().catch((cause: Error) => setError(cause.message)); }}>Retry connection</button>}
          <button aria-label="Dismiss error" onClick={() => setError("")}>×</button>
        </div>}
        {notice && <p role="status" className="notice">{notice}</p>}

        {workspace === "repair" ? <RepairChecklist
          documents={documents.filter((document) => selected.includes(document.id))}
          mode={health?.mode}
        /> : <>
        <section className="question-card" aria-labelledby="question-heading">
          <div className="card-title"><h2 id="question-heading"><span className="question-symbol" aria-hidden="true">?</span>What would you like to know?</h2>
            <span>{selected.length ? selected.length + " selected" : "All documents"}</span>
          </div>
          <form onSubmit={ask}>
            <label htmlFor="question" className="visually-hidden">Your question</label>
            <textarea ref={textarea} id="question" value={question} maxLength={2000} minLength={3} required
              placeholder="Ask something about your documents…" disabled={!!busy}
              onChange={(event) => setQuestion(event.target.value)} />
            <div className="composer-footer"><span>Answers stay grounded in your sources.</span>
              <button className="ask-button" type="submit" disabled={!!busy || !health || documents.length === 0 || question.trim().length < 3}>
                {busy === "ask" ? "Searching…" : "Ask question"}<span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>
        </section>

        {!answer && !busy && <section className="suggestions" aria-label="Example questions">
          <h2>TRY IT WITH THE SAMPLE DOCUMENTS</h2>
          <div>{suggestions.map((suggestion, index) => <button key={suggestion} onClick={() => chooseSuggestion(suggestion)}>
            <span className="suggestion-number" aria-hidden="true">0{index + 1}</span><span className="suggestion-copy">{suggestion}</span><span className="suggestion-arrow" aria-hidden="true">↗</span>
          </button>)}</div>
        </section>}

        {busy === "ask" && <div role="status" className="loading"><span className="loading-dot" />Finding relevant passages…</div>}

        {answer && <section className="answer-section" aria-label="Answer" aria-live="polite">
          <div className="answer-title"><span className="answer-mark"><Mark small /></span>
            <h2>{answer.refused ? "More information needed" : answer.mode === "demo" ? "Matching passages" : "Answer"}</h2>
            <span>{answer.elapsed_ms} ms</span>
          </div>
          <p className="asked-question">{asked}</p>
          <div className="answer-text">{answer.answer}</div>
          {!answer.refused && <p className="answer-caption">{answer.mode === "demo"
            ? "Extracted sentences from your files. Open a source below to read the full passage."
            : "AI-generated from the passages below. Check the sources before relying on the answer."}</p>}
          {answer.sources.length > 0 && <div className="sources">
            <h3>Sources <span>{answer.sources.length}</span></h3>
            {answer.sources.map((source) => <details key={source.id}>
              <summary><span className="citation-number">[{source.id}]</span><strong>{source.filename}</strong>
                <span className="source-meta">Page {source.page} · Similarity {source.score.toFixed(2)}</span>
              </summary>
              <blockquote>{source.text}</blockquote>
            </details>)}
          </div>}
        </section>}

        </>}

        <footer className="workspace-footer"><span>BUILT TO SHOW ITS SOURCES</span><p>PDF page references · Inspectable passages · Focused document search</p></footer>
      </div>
    </main>
  </div>;
}
