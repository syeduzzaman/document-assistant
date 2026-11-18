# Architecture and engineering decisions

## Ingestion

1. Validate the extension and upload size. Reject invalid PDF headers, encrypted PDFs and documents without extractable text.
2. Extract each PDF page independently; UTF-8 TXT and Markdown have a single logical page.
3. Create 150-word chunks with 25-word overlap, preserving page and chunk index.
4. Embed the chunks using the configured provider.
5. In a database transaction, insert the document and all chunks. A unique checksum/embedding-space constraint makes duplicate uploads idempotent.

A failed embedding call cannot leave a partially indexed document. Database insertion rolls back if any chunk fails. A repeated upload currently computes embeddings before discovering the duplicate; checking the checksum before the provider call would reduce cost, while retaining the database constraint for concurrent requests.

Extracted document text and vectors are persisted; raw PDF binaries are not. Deleting a document cascades to its chunks.

## Retrieval

Query and document vectors share one embedding-space identifier. Changing the provider, model or implementation version uses a different namespace. Scores from incompatible spaces are never mixed.

The SQL query applies the namespace and optional document filter before ordering by pgvector cosine distance. User values are bound as SQL parameters. The demo adds a token-overlap check to reduce false matches from hash collisions.

A minimum cosine score is a heuristic. It is not calibrated across datasets or providers and does not reliably identify every unanswerable question. A larger labeled evaluation set should guide provider-specific thresholds.

Exact search is appropriate for a small portfolio corpus. An HNSW index becomes useful at larger scale, after comparing its recall and latency against this exact baseline.

## Answers and citations

The demo chooses the sentence with the highest query-token overlap from each retrieved passage. Its output is explicitly labeled as extracted matching passages.

OpenAI mode uses the Responses API with a strict JSON schema. A provider response contains an answer, cited source IDs and an insufficient-context flag. The application checks that every citation marker refers to a retrieved source and that the marker set agrees with the returned IDs. Invalid responses return a provider error rather than exposing broken citations.

The source list always comes from the database. The model cannot supply its own filenames, source text or page numbers. Source validation checks citation identity, not entailment: a model can cite a real source while making an unsupported claim. Claim-level verification and prompt injection tests are future work.

## API and interface

FastAPI synchronous handlers run blocking PDF parsing, PostgreSQL operations and provider calls outside the event loop. Small files are indexed synchronously so the UI receives a ready-to-search result. Heavy or concurrent ingestion needs background workers.

The React interface uses a single question at a time. Selected document checkboxes restrict retrieval. Source cards show exact passages and PDF pages. Errors, duplicate uploads, loading states and provider mode are visible.

Nginx serves the built React app and proxies the API on the same origin. Vite provides the equivalent proxy in development. The frontend never receives an OpenAI key.

## Operations

Compose waits for the database and API to become healthy. Database content lives in a named volume. API and web containers run as non-root users. Public ports bind to localhost.

Startup creates the small initial schema idempotently. A project with evolving deployed data should use versioned migrations. This project does not claim multi-tenant or production readiness.

## Evaluation boundaries

The checked-in dataset deliberately separates answerable and unanswerable cases. Document Recall@3 answers whether the relevant file is retrieved; MRR@3 captures ranking. Expected answer-fragment checks detect loss of known facts. Refusal accuracy covers two explicit out-of-domain examples.

These checks do not measure semantic correctness broadly. The next evaluation set should add paraphrases, conflicting revisions, unrelated documents sharing keywords, malicious instructions, multi-page questions and multilingual queries. OpenAI behavior is mocked in unit tests so CI is deterministic and does not require secrets or paid calls.
