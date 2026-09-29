# AI Document Assistant

> A chatbot that answers patient questions using a clinic's own documents, and cites its sources.

🚧 Work in progress. Full README coming as the project takes shape.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
cp .env.example .env            # then fill in your keys
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health, or the interactive API docs at http://127.0.0.1:8000/docs.

Run the tests:

```bash
pytest
```

---

*Demo project built for portfolio purposes. BrightSmile Dental is a fictional company with sample data.*
