# AI Document Assistant

> A chatbot that answers patient questions using a clinic's own documents, and cites its sources.

🚧 Work in progress. Full README coming as the project takes shape.

## Run locally

You need free accounts on [Anthropic](https://console.anthropic.com), [Voyage AI](https://dash.voyageai.com) and [Neon](https://neon.tech) (Postgres with pgvector).

```bash
python -m venv .venv
.venv\Scripts\activate               # Windows
# source .venv/bin/activate          # macOS / Linux
pip install -e ".[dev]"
cp .env.example .env                 # then fill in your keys

python scripts/check_setup.py        # verify database, embeddings and chat credentials
python scripts/ingest.py             # index the sample documents (safe to re-run)
python scripts/check_retrieval.py    # verify search finds the right document per question

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health, or the interactive API docs at http://127.0.0.1:8000/docs.

Run the tests (no API keys needed):

```bash
pytest
```

---

*Demo project built for portfolio purposes. BrightSmile Dental is a fictional company with sample data.*
