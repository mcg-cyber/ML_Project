# Multi-Provider Gradio Chat Pro

A single Gradio app that can talk to:

- **Local Ollama**
- **Gemini**
- **OpenAI**
- **DeepSeek**

It includes:

- live streaming responses
- native file sending for **Gemini** and **OpenAI**
- file upload with fallback local extraction for other providers
- model auto-fetch
- provider health check
- system prompt
- temperature, context, max tokens, top_p, top_k controls
- animated request states with 5 styles
- stop generation button
- retry last reply
- save/load chat JSON
- export chat to **MD / TXT / JSON**
- simple document chunking for uploaded files

## Files in this package

- `app.py` — main Gradio app
- `requirements.txt` — Python dependencies
- `README.md` — setup and usage guide

## Python version

Recommended: **Python 3.10+**

## Install

Create and activate a virtual environment if you want:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:7860
```

## Provider setup

### 1) Ollama

Make sure Ollama is installed and running locally.

Default base URL:

```text
http://localhost:11434
```

Example:

```bash
ollama pull llama3.2
ollama serve
```

Then in the app:
- Provider = `Ollama`
- Base URL = `http://localhost:11434`
- Model = `llama3.2` or another pulled model

### 2) Gemini

You need a Gemini API key.

In the app:
- Provider = `Gemini`
- Paste your API key
- Pick or type a model name
- Click **Fetch models** if you want the current model list

### 3) OpenAI

You need an OpenAI API key.

In the app:
- Provider = `OpenAI`
- Paste your API key
- Base URL normally stays:

```text
https://api.openai.com/v1
```

### 4) DeepSeek

You need a DeepSeek API key.

In the app:
- Provider = `DeepSeek`
- Paste your API key
- Base URL normally stays:

```text
https://api.deepseek.com
```

## How file handling works

### Gemini
- uses native Gemini file upload for files you attach
- streams the answer back into Gradio

### OpenAI
- uses native OpenAI-style file/image input payloads
- images are sent as image inputs
- other files are sent as file inputs

### Ollama and DeepSeek
- uploaded files are read locally when possible
- the app extracts text from TXT/code/MD/JSON/CSV/PDF/DOCX and similar files
- a simple chunking step picks the most relevant chunks and appends them to the prompt

## Controls

- **Temperature**: creativity / randomness
- **Context / history budget**: local chat history trimming budget before sending
- **Max output tokens**: response length cap
- **top_p**: nucleus sampling
- **top_k**: Ollama-only sampling control
- **System prompt**: behavior instructions
- **Animation style**: request/response animation in the status panel

## Buttons

- **Fetch models** — pull model list from the selected provider
- **Health check** — test connectivity/API access
- **Send** — send message and start streaming
- **Stop** — cancel current generation
- **Retry last** — remove the last assistant answer so you can resend
- **Clear** — clear chat history
- **Save chat JSON** — save a reloadable chat file
- **Load chat** — load a previously saved chat JSON
- **Export MD/TXT/JSON** — export conversation in different formats

## Notes and limitations

- Native file sending is implemented for **Gemini** and **OpenAI**.
- Ollama and DeepSeek use local extraction/RAG fallback instead of native file APIs.
- Some providers may reject specific parameters or certain models depending on your account.
- Model availability changes over time, so **Fetch models** is useful.
- For very large files, provider limits still apply.
- PDF/DOCX extraction quality depends on the document structure.

## Troubleshooting

### App does not start

Check Python version:

```bash
python --version
```

Reinstall requirements:

```bash
pip install -U -r requirements.txt
```

### Ollama not reachable

Test directly:

```bash
curl http://localhost:11434/api/tags
```

### Hosted provider returns auth error

Usually means:
- wrong API key
- model not available to your account
- quota exhausted
- base URL changed incorrectly

### PDF or DOCX text looks incomplete

That can happen with scanned PDFs or heavily formatted DOCX files.

## Suggested future upgrades

- persistent provider presets saved locally
- token/cost panel when provider returns usage data
- image preview thumbnails before send
- multi-chat workspace / tabs
- semantic embedding search for uploaded document sets
- optional citations/snippets panel for retrieved file chunks
