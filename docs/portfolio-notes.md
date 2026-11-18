# Explaining this project in an interview

## Short introduction

"I built a document assistant with FastAPI, React and PostgreSQL/pgvector. It ingests PDFs, preserves page references, retrieves relevant passages and returns citations that users can inspect. The project has a free deterministic retrieval demo and an optional OpenAI pipeline for semantic embeddings and answer generation. I added database integration tests, a small evaluation dataset, browser tests, Docker and GitHub Actions."

Adjust this wording to reflect what you have personally run, reviewed and understood.

## Useful discussion points

- Why retrieval is needed: provide document context instead of expecting an LLM to know private business information.
- Why citations need application checks: a model-generated reference is not evidence until it maps to a stored source.
- Why model namespaces matter: mixing embedding spaces silently breaks similarity search.
- Why a lexical demo is useful: reproducible behavior and no API cost during reviews.
- What is measured: retrieval ranking, expected facts and explicit refusals on a small fixture.
- What is not proven: broad answer correctness, production reliability or complete prompt injection resistance.
- What to improve next: hybrid retrieval, reranking, larger evaluations, background ingestion and user isolation.

## CV example

**Document Assistant — RAG portfolio project:** Developed document ingestion, pgvector retrieval and source-linked question answering with Python/FastAPI, React/TypeScript, PostgreSQL and Docker; added optional OpenAI integration, retrieval evaluation and GitHub Actions checks.

Do not add latency, accuracy or user-count claims until you have measured them in a stated environment.
