# ollama-api

**A tool-using agent on a local LLM, served by FastAPI.** Built as my project for the Hugging Face Agents Course
(2025), which I completed with certification.

The agent is a [`smolagents`](https://github.com/huggingface/smolagents) `CodeAgent`: it answers a question by
writing and running Python, calling tools as it goes. The model runs locally under [Ollama](https://ollama.com), and
a small adapter makes the Ollama API look like a `smolagents` model.

## What the agent can do

| Tool | What it does |
|---|---|
| `web_search`, `visit_webpage`, `search_wikipedia` | DuckDuckGo search, page visits, Wikipedia summaries |
| `web_scrape` | Page text through headless Playwright for JavaScript-heavy sites, falling back to plain requests (the Docker image doesn't install Playwright's browsers, so it always falls back there) |
| `file_download` | Fetch a file from a URL |
| `file_reader` | Text, CSV, JSON, Excel and PDF; optionally asks the LLM to analyse a table |
| `extract_text_ocr` | OCR with Tesseract |
| `speech_to_text` | Audio transcription through the Hugging Face Inference API (needs `HF_TOKEN`) |
| `image_to_text` | Image description through the OpenAI API (needs `OPEN_AI_KEY`) |

The two hosted tools switch on only when their key is set; the others need no key.

**The agent checks its own work.** After a run, a second LLM call reads the question, the agent's reasoning and
code steps, and its final answer, and replies PASS or FAIL. A failed check retries the run, up to three attempts.

## Running it

You need Ollama serving a model, by default at `http://host.docker.internal:11434`.

```bash
ollama pull qwen2.5-coder:14b
cp .env.example .env              # set LLM_API_URL, DEFAULT_MODEL and, optionally, HF_TOKEN / OPEN_AI_KEY
docker compose --profile lite up --build
```

Then try `GET http://localhost:8000/ask?prompt=...` for a plain completion, or `POST /code-agent` with
`{"prompt": "..."}` to run the agent. `python app.py` opens a Gradio UI for the agent instead.

Docker build targets and compose profiles:

| Profile | What runs |
|---|---|
| `lite` | The API only, no telemetry |
| `full` | The API with OpenTelemetry tracing and metrics, plus Prometheus (port 9090) |
| `monitoring` | Prometheus and Grafana (port 3000) |
| `dev` | The full build with dev tools and auto-reload |

Other endpoints: `/health`, `/health/simple`, `/telemetry`, `/metrics` and `/stats`.

## What I learned

- **Model choice decides whether a code agent works at all.** `mistral` 7B struggled to keep to the response format
  the agent loop expects, so the default became `qwen2.5-coder:14b`.
- **The agent loop needs its pattern spelled out.** The system prompt moved from a long one to a short one that
  states the required pattern (gather information, then call `final_answer(...)`) and lists every tool with its
  arguments.
- **Telemetry should be optional.** Tracing lives behind an interface with a no-op default, so the lite build has no
  OpenTelemetry dependency.

## Not finished

- `GET /toolkit-test` and `core/test_toolkit.py` are stubs: the per-tool benchmark was planned, not written.
- There are no automated tests yet.
