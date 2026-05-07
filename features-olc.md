# Ollama Rocket WebTools v9 - Feature Analysis

Source analyzed: `ollama_rocket_webtools_v9.py`

## Executive summary

This script is a terminal-based Ollama chat client that combines:

- local model selection and conversational chat
- optional multi-model workflows
- web search and lightweight web crawling
- defensive security analysis helpers
- file upload and document parsing
- document generation and data visualization
- voice input, translation, and limited code execution

It is positioned as a power-user CLI assistant for local AI workflows, with notable additions in **V7-V9** around web-assisted answering, security workflows, and multi-model reasoning.

---

## 1) High-level architecture

### Core runtime
- Uses `ollama.Client(host="http://localhost:11434")` to call local Ollama models.
- Runs as an interactive command-line loop.
- Stores chat history in memory and optionally on disk under:
  - `~/.ollama_ai_chat`
- Maintains a rolling conversational context using the last `CONTEXT_WINDOW_SIZE = 5` exchanges.

### Main modes
1. **Normal chat mode** - prompt goes directly to selected model.
2. **Default web-assisted mode** - normal prompts can automatically invoke web tools.
3. **Multi-chat mode** - send the same prompt to selected models.
4. **Security mode** - wraps prompts in a defensive OWASP-style persona.
5. **Vision mode** - image prompts for compatible vision model names.

---

## 2) Core chat capabilities

### Model management
- Lists available local models from Ollama.
- Lets the user select a model interactively.
- Can switch models during a session with `/t`.
- Persists per-model conversation history filenames using a sanitized model name.

### Conversational context
- Stores conversation as a list of `{user, model}` entries.
- Builds a rolling prompt from the most recent messages.
- Supports custom context size via `/ctx` by updating `num_ctx`.

### Response streaming
- Streams model output incrementally.
- Shows a loading spinner while waiting for a response.

---

## 3) User commands implemented

### Session and conversation commands
- `/help` - show command list
- `/clear` - clear terminal screen
- `/models` - list local Ollama models
- `/history` - show current session history
- `/delete` - clear current conversation in memory
- `/export` - save conversation to JSON
- `/load` - intended to load a prior conversation
- `/new` - start a fresh chat session
- `/s` - save conversation as Markdown
- `/t` - switch model
- `/bye`, `/quit`, `/exit` - exit and auto-save current conversation

### Analysis and interaction commands
- `/summary` - summarize the conversation
- `/sentiment` - intended to analyze conversation sentiment
- `/prompt` - set a custom prompt value
- `/upload` - upload file content for analysis
- `/search` - run a web search
- `/crawl` - crawl a website and optionally analyze the results
- `/run` - execute a restricted Python snippet
- `/translate` - translate text with GoogleTranslator
- `/tool` - enable/select embedding model
- `/voice` - capture a voice command using speech recognition
- `/multi` - enable multi-model chat mode
- `/compare` - ask multiple models the same question
- `/router` - auto-pick a model based on question type
- `/doublecheck` - get a second model to review a first answer
- `/solve` - solve math step by step
- `/checksolution` - critique a user's math solution
- `/generate` - export latest answer as pdf/docx/txt/md
- `/visualize` - make a bar/line/pie chart from dictionary data
- `/analyze` - analyze an image with a vision model
- `/ctx` - update context window size

### Web and security commands
- `/webai` - force a web-assisted answer
- `/webmode` - toggle default web-assisted answering for normal prompts
- `/searchbackend` - choose default backend from duckduckgo/searxng/bing/google
- `/verify` - show evidence snippets before answering in web mode
- `/websources` - print the last search summary used
- `/secmode` - toggle defensive OWASP-style prompt wrapper
- `/owasp` - generate a high-level OWASP-style assessment
- `/securl` - fetch a URL and build a security header report
- `/zapfile` - analyze an exported OWASP ZAP report
- `/nmapxml` - analyze an Nmap XML report

---

## 4) Multi-model reasoning features

### `/multi`
Lets the user select several models and then choose which selected models receive a prompt.

### `/compare`
Runs the same question against multiple chosen models and prints each answer one after another.

### `/router`
Implements a lightweight heuristic router:
- **math questions** -> prefers model names containing keywords such as `math`, `qwen`, `mistral`, `llama`
- **security questions** -> prefers names containing `sec`, `security`, `cyber`, `shield`
- **general questions** -> prefers `chat`, `general`, `gemma`, `llama`, `mistral`

### `/doublecheck`
- gets a primary answer from current model
- chooses a reviewer model (manual or automatic)
- asks the reviewer to critique correctness, omissions, and provide an improved final answer

### Math workflows
- `/solve` standardizes step-by-step math solving
- `/checksolution` reviews a pasted student solution and corrects it if necessary

---

## 5) Web search and browsing features

### Supported search backends
The script can search with:
- DuckDuckGo Instant Answer API
- DuckDuckGo HTML results fallback
- SearXNG HTML POST search
- Bing Web Search API
- Google Custom Search JSON API

### Web helper design
`smart_web_search()`:
- accepts a requested backend
- uses backend-specific implementation when configured
- falls back to DuckDuckGo summary search
- stores the last result text in `last_web_search_summary`

### `/webai` workflow
1. take a user question
2. run search with configured backend
3. optionally show evidence snippets when verification mode is on
4. build a grounded prompt from the search summary
5. ask the selected model to answer using that context
6. if search fails, optionally fetch a specific URL directly and answer from its content

### Automatic tool-selection workflow
`ask_with_web_search()` lets the model propose one of these JSON tool requests:
- `{"tool": "web_search", "query": "..."}`
- `{"tool": "web_page", "url": "..."}`
- `{"tool": "web_crawl", "url": "...", "depth": 1}`
- `{"tool": "none"}`

That creates a primitive agent/tool-use loop for web-assisted answering.

### Website crawling
- checks `robots.txt` with `RobotFileParser`
- crawls internal links only
- extracts headings, paragraphs, links, images, and flattened text
- supports configurable crawl depth and max pages

---

## 6) Security-focused capabilities

This is one of the strongest feature areas in the script.

### Security persona mode
When `/secmode` is enabled, prompts are wrapped so the model behaves like a defensive security assistant focused on:
- OWASP Top 10 themes
- secure design
- detection and mitigation
- avoiding exploit code or offensive guidance

### URL security report
`/securl` fetches a page and reports:
- requested URL and final URL
- status code
- HTTP vs HTTPS
- presence/absence of key headers:
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
  - Strict-Transport-Security
  - Permissions-Policy
- `Set-Cookie` header
- truncated response body snippet

### Defensive file analysis
- `/zapfile` reads an exported OWASP ZAP report and asks the model for defensive remediation-focused analysis
- `/nmapxml` reads an Nmap XML report and asks for exposed services, risks, and hardening recommendations
- `/owasp` generates a high-level safe assessment for an application or website

---

## 7) File upload and content extraction

### Supported upload types
- images: `.png`, `.jpg`, `.jpeg`
- text: `.txt`
- documents: `.pdf`, `.docx`, `.pptx`, `.xlsx`

### Extraction behavior
- images are encoded to base64 for vision prompting
- PDFs are read with `PyPDF2.PdfReader`
- DOCX files are read with `python-docx`
- PPTX files are attempted through `python-pptx`
- XLSX files are read with `openpyxl`

### Upload analysis behavior
- for vision model names starting with `granite3.2-vision:latest`, image uploads become multimodal prompts
- otherwise file content is converted to text and prepended to an analysis question

---

## 8) Document generation and reporting

### Output formats
The `/generate` path can export the last model answer as:
- `pdf`
- `docx`
- `txt`
- `md`

### PDF generation
Two PDF pathways are supported:
- **Markdown -> Pandoc -> XeLaTeX** using the `eisvogel` template
- **LaTeX -> pdflatex**

### Content sanitization
`sanitize_content()` performs some math-friendly text cleanup:
- converts `\( ... \)` to `$...$`
- converts `\[ ... \]` to `$$...$$`
- unescapes math dollar signs where applicable
- escapes `#` and `%` in LaTeX mode
- repairs `\fracddx` to `\frac{d}{dx}`

### DOCX/TXT/MD generation
- DOCX: line-by-line paragraph insertion
- TXT: direct text write
- MD: direct text write

---

## 9) Data, voice, translation, and code utilities

### Visualization
`/visualize` accepts dictionary input and plots:
- bar chart
- line chart
- pie chart

### Translation
`/translate` uses `deep_translator.GoogleTranslator` with automatic source-language detection.

### Voice commands
`/voice`:
- records via microphone
- uses Google Speech Recognition
- forwards recognized speech to the selected model

### Code execution
`/run`:
- executes Python via `exec()`
- blocks code containing `import os`, `import sys`, or `import subprocess`
- runs with `__builtins__` emptied for restriction

### Text-to-speech
There is an optional TTS path using `pyttsx3`, but `ENABLE_SPEECH` is disabled by default.

---

## 10) Persistence and storage

### Conversation storage
Saved under `~/.ollama_ai_chat`

### Save formats
- JSON conversation export via `save_conversation()`
- Markdown conversation export via `save_to_markdown()`

### Auto-save behavior
On exit commands, the current conversation is saved automatically.

---

## 11) Dependencies and stack

### AI / inference
- `ollama`

### CLI and rendering
- `colorama`
- `rich`
- `readline`

### Documents and files
- `PyPDF2`
- `python-docx`
- `python-pptx`
- `openpyxl`
- `Pillow`
- `fpdf`
- `pandoc`, `xelatex`, `pdflatex` (external tools expected for PDF path)

### Web and parsing
- `requests`
- `beautifulsoup4`
- `urllib.robotparser`

### Data and plots
- `pandas`
- `matplotlib`

### Speech and translation
- `pyttsx3`
- `speech_recognition`
- `deep_translator`

---

## 12) Notable strengths

1. **Broad feature surface** for a single CLI script.
2. **Strong web-assistance design** with multiple search backends and fallback behavior.
3. **Good defensive security orientation** rather than purely offensive use.
4. **Useful multi-model workflows** (`/compare`, `/router`, `/doublecheck`).
5. **Practical output utilities** for exporting answers and creating charts.
6. **Local-first model usage** through Ollama.

---

## 13) Gaps, risks, and likely bugs

### Missing or broken functions
The script references some functions that do not appear to be implemented in the analyzed file:
- `load_conversation()`
- `analyze_sentiment()`

That means `/load` and `/sentiment` are likely broken at runtime.

### `custom_prompt` appears unused
The script lets the user set a custom prompt, but the value is not integrated into the prompt-building path.

### `context_window` global appears unused
A separate `context_window` list exists, but the actual context logic uses `conversation[-CONTEXT_WINDOW_SIZE:]`.

### `ask_question()` has unreachable TTS code
The function returns `full_response` before the text-to-speech block, so speech playback after generation will never run.

### Potential PPTX extraction issue
`upload_file()` uses:
- `" ".join(slide.text for slide in prs.slides)`

`python-pptx` slides do not normally expose a `.text` property directly, so PPTX upload handling is likely faulty.

### Signal comment mismatch
The script comments say Ctrl+S, but `signal.SIGTSTP` is typically associated with Ctrl+Z on Unix-like systems.

### Restricted execution may be too restrictive
Because `exec()` runs with empty builtins, many normal Python snippets will fail even if they are safe.

### Security limitations of code execution
Simple string checks for `import os`, `import sys`, and `import subprocess` are not a robust sandbox.

### Web scraping robustness
- search scraping may break if HTML structure changes
- some flows depend on optional environment variables
- no retry/backoff logic is implemented

### Hardcoded vision model check
Vision behavior is tied to model names beginning with `granite3.2-vision:latest`, which limits flexibility.

### Low default output length
`max_tokens = 100` may truncate useful answers unless manually increased elsewhere.

### Unused imports / code clutter
Likely includes unused imports such as `FPDF`, `Markdown`, and others depending on final runtime paths.

---

## 14) Recommended improvements

### Reliability
- implement `load_conversation()` and `analyze_sentiment()`
- fix PPTX extraction by iterating shapes/text frames
- move speech playback before `return` in `ask_question()`
- make signal handling platform-aware

### Security
- remove raw `exec()` or replace with a real sandbox/subprocess isolation strategy
- add allowlist-based execution instead of string matching
- validate URLs and file sizes before crawling/fetching

### UX
- actually apply `custom_prompt`
- expose temperature/top_p/max_tokens as commands
- add better status/error messages for missing API keys and missing binaries
- show selected default modes in prompt header or startup summary

### Architecture
- split the monolithic script into modules:
  - `chat.py`
  - `web.py`
  - `security.py`
  - `files.py`
  - `documents.py`
  - `cli.py`
- replace long `if/elif` command chain with a command registry
- add unit tests for parser, search, and export functions

### Product evolution
- add RAG/document indexing instead of only one-shot file extraction
- add response citation formatting for web-assisted answers
- support per-model settings and saved profiles
- add structured config file instead of many globals

---

## 15) Final assessment

**Ollama Rocket WebTools v9** is an ambitious all-in-one local AI CLI assistant. Its standout value is the combination of:
- Ollama-based local chat
- multi-backend web augmentation
- defensive security tooling
- multi-model comparison and review workflows
- basic document/report generation

The concept is strong and feature-rich, but the implementation would benefit from cleanup, modularization, and bug fixing before being treated as production-grade.

## Quick feature inventory

### Core AI
- local Ollama chat
- context-aware prompting
- model switching
- multi-model chat
- response streaming

### Web
- DuckDuckGo
- SearXNG
- Bing
- Google CSE
- page fetch
- crawl
- web evidence summary

### Security
- OWASP persona mode
- OWASP assessment
- header inspection
- ZAP report analysis
- Nmap XML analysis

### Productivity
- upload/analyze files
- summarize conversations
- translate text
- voice input
- visualize data
- generate docs

### Advanced reasoning
- compare answers
- route by topic
- double-check with second model
- solve math
- review math solutions
