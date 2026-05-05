import base64
import io
import json
import mimetypes
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import gradio as gr
import requests

try:
    from google import genai
    from google.genai import types as genai_types
except Exception:
    genai = None
    genai_types = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document
except Exception:
    Document = None

APP_TITLE = "Multi-Provider Gradio Chat Pro"
DEFAULT_SYSTEM = (
    "You are a helpful assistant. Use uploaded files when relevant. "
    "If file parsing is partial or uncertain, say so clearly."
)
OLLAMA_DEFAULT_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_DEFAULT_URL = "https://api.openai.com/v1"
DEEPSEEK_DEFAULT_URL = "https://api.deepseek.com"

CSS = r'''
:root {
  --bg: #081018;
  --panel: #121d2d;
  --panel2: #18273d;
  --txt: #e8f0ff;
  --muted: #9fb2d6;
  --border: #2b4161;
  --good: #2fe07a;
  --warn: #f4c14b;
  --bad: #ef6a6a;
}
body, .gradio-container {
  background: radial-gradient(circle at top, #10223b 0%, #09121d 38%, #060b12 100%);
  color: var(--txt);
}
.gradio-container { max-width: 1550px !important; }
#hero {
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 16px 18px;
  background: linear-gradient(135deg, rgba(18,29,45,.95), rgba(9,18,29,.95));
  box-shadow: 0 14px 44px rgba(0,0,0,.28);
}
.cardish, .gr-box, .gr-group, .gr-form, .gr-accordion {
  border-color: var(--border) !important;
}
.statbox {
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 12px;
  background: rgba(10,16,25,.85);
  min-height: 80px;
}
.status-wrap {
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 12px 14px;
  background: rgba(10,16,25,.92);
  position: relative;
  overflow: hidden;
  min-height: 88px;
}
.status-title { font-weight: 700; margin-bottom: 8px; }
.status-sub { color: var(--muted); font-size: 13px; margin-top: 8px; }
.status-row { display:flex; align-items:center; gap: 14px; }
.badge {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--muted);
  font-size: 12px;
  background: rgba(255,255,255,.03);
}
.scanline::after {
  content:""; position:absolute; top:0; left:-25%; width:22%; height:100%;
  background: linear-gradient(90deg, transparent, rgba(47,224,122,.72), transparent);
  filter: blur(4px);
  animation: scan-run 1.25s linear infinite;
}
.status-idle.scanline::after, .status-done.scanline::after, .status-error.scanline::after { display:none; }
@keyframes scan-run { from { left:-25%; } to { left:110%; } }
.dot-grid { display:grid; grid-template-columns: repeat(8, 10px); gap:6px; }
.dot-grid span {
  width:10px; height:10px; border-radius:3px; background: rgba(159,178,214,.16);
  border: 1px solid rgba(159,178,214,.2); animation: dot-flash 1.1s infinite ease-in-out;
}
.dot-grid span:nth-child(2n){animation-delay:.1s} .dot-grid span:nth-child(3n){animation-delay:.2s}
.dot-grid span:nth-child(4n){animation-delay:.3s} .dot-grid span:nth-child(5n){animation-delay:.4s}
.status-idle .dot-grid span, .status-done .dot-grid span { animation:none; }
.status-error .dot-grid span { animation:none; background: rgba(239,106,106,.25); border-color: rgba(239,106,106,.35); }
@keyframes dot-flash { 0%,100% { transform:scale(.7); } 50% { transform:scale(1); background: rgba(47,224,122,.95); } }
.eq { display:flex; align-items:flex-end; gap:6px; height:30px; }
.eq span { width:8px; height:10px; border-radius:999px; background: rgba(47,224,122,.9); animation:eq-move 1s infinite ease-in-out; }
.eq span:nth-child(2){animation-delay:.1s} .eq span:nth-child(3){animation-delay:.2s} .eq span:nth-child(4){animation-delay:.3s} .eq span:nth-child(5){animation-delay:.4s}
.status-idle .eq span, .status-done .eq span { animation:none; height:12px; opacity:.55; }
.status-error .eq span { animation:none; background: rgba(239,106,106,.9); }
@keyframes eq-move { 0%,100% { height:8px; } 50% { height:28px; } }
.orbit { width:46px; height:46px; border-radius:999px; position:relative; border:1px solid rgba(159,178,214,.26); }
.orbit::before, .orbit::after { content:""; position:absolute; inset:0; border-radius:inherit; }
.orbit::before { border:2px solid transparent; border-top-color: rgba(47,224,122,.92); animation: spin 1s linear infinite; }
.orbit::after { width:8px; height:8px; background: rgba(47,224,122,.95); border-radius:999px; top:-4px; left:19px; box-shadow:0 0 12px rgba(47,224,122,.75); animation: spin 1s linear infinite; transform-origin: 4px 27px; }
.status-idle .orbit::before, .status-idle .orbit::after, .status-done .orbit::before, .status-done .orbit::after { animation:none; }
.status-error .orbit::before { border-top-color: rgba(239,106,106,.95); }
.status-error .orbit::after { background: rgba(239,106,106,.95); box-shadow:0 0 12px rgba(239,106,106,.7); }
@keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
.pulse-lines { display:flex; gap:6px; align-items:center; }
.pulse-lines span {
  width:4px; height:28px; border-radius:999px; background: rgba(47,224,122,.88);
  animation: pulse-lines 1.1s infinite ease-in-out;
}
.pulse-lines span:nth-child(2){animation-delay:.12s} .pulse-lines span:nth-child(3){animation-delay:.24s}
.pulse-lines span:nth-child(4){animation-delay:.36s} .pulse-lines span:nth-child(5){animation-delay:.48s}
.status-idle .pulse-lines span, .status-done .pulse-lines span { animation:none; height:12px; opacity:.55; }
.status-error .pulse-lines span { animation:none; background: rgba(239,106,106,.9); }
@keyframes pulse-lines { 0%,100% { transform:scaleY(.35); } 50% { transform:scaleY(1); } }
.file-pill {
  display:inline-block; margin: 4px 6px 0 0; padding: 3px 10px; border-radius:999px;
  border:1px solid var(--border); color: var(--muted); background: rgba(255,255,255,.03); font-size:12px;
}
.small-note { color: var(--muted); font-size: 12px; }
'''

HEADER_MD = """
<div id='hero'>
  <h1 style='margin:0 0 8px 0;'>Multi-Provider Gradio Chat Pro</h1>
  <div style='color:#9fb2d6;'>One app for local <b>Ollama</b>, hosted <b>Gemini</b>, <b>OpenAI</b>, and <b>DeepSeek</b>. Includes streaming, model discovery, native Gemini/OpenAI file sending, health checks, save/load/export, and animated request states.</div>
</div>
"""


@dataclass
class Attachment:
    path: str
    name: str
    mime: str
    size: int


def render_status(state: str, style: str, detail: str = "") -> str:
    labels = {
        "idle": ("Idle", "Ready for a new prompt."),
        "sending": ("Sending", "Preparing request and attachments."),
        "receiving": ("Receiving", "Streaming response from provider."),
        "done": ("Done", "Response complete."),
        "error": ("Error", "Request failed."),
    }
    title, sub = labels.get(state, labels["idle"])
    if detail:
        sub = detail
    if style == "Green Scan":
        anim = "<div style='flex:1'></div>"
        extra = "scanline"
    elif style == "Square Dots":
        anim = "<div class='dot-grid'>" + "".join("<span></span>" for _ in range(24)) + "</div>"
        extra = ""
    elif style == "Equalizer":
        anim = "<div class='eq'>" + "".join("<span></span>" for _ in range(5)) + "</div>"
        extra = ""
    elif style == "Pulse Lines":
        anim = "<div class='pulse-lines'>" + "".join("<span></span>" for _ in range(5)) + "</div>"
        extra = ""
    else:
        anim = "<div class='orbit'></div>"
        extra = ""
    return f"""
    <div class='status-wrap status-{state} {extra}'>
      <div class='status-title'>{title}</div>
      <div class='status-row'>
        <div class='badge'>{style}</div>
        {anim}
      </div>
      <div class='status-sub'>{sub}</div>
    </div>
    """


def provider_defaults(provider: str) -> Tuple[str, str, str]:
    if provider == "Ollama":
        return OLLAMA_DEFAULT_URL, "llama3.2", "Local Ollama API. API key usually not needed."
    if provider == "Gemini":
        return "https://generativelanguage.googleapis.com", "gemini-2.5-flash", "Use a Gemini API key. Some Gemini API usage has a free quota depending on account and limits."
    if provider == "OpenAI":
        return OPENAI_DEFAULT_URL, "gpt-5.4-mini", "Use an OpenAI API key. Model access and free usage depend on your account."
    return DEEPSEEK_DEFAULT_URL, "deepseek-chat", "Use a DeepSeek API key. Compatible with the OpenAI-style chat API."


def update_provider(provider: str):
    base_url, model, help_text = provider_defaults(provider)
    base_visible = provider in {"Ollama", "OpenAI", "DeepSeek"}
    topk_visible = provider == "Ollama"
    return (
        gr.update(value=base_url, visible=base_visible),
        gr.update(value=model),
        gr.update(value=help_text),
        gr.update(visible=topk_visible),
    )


def attachment_from_paths(paths: Optional[List[str]]) -> List[Attachment]:
    items: List[Attachment] = []
    for path in paths or []:
        p = Path(path)
        if not p.exists():
            continue
        mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        items.append(Attachment(str(p), p.name, mime, p.stat().st_size))
    return items


def file_badges(paths: List[str]) -> str:
    if not paths:
        return ""
    return "<div>" + "".join(f"<span class='file-pill'>{Path(p).name}</span>" for p in paths) + "</div>"


def _read_text_file(path: str, max_chars: int = 20000) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(max_chars)


def _read_pdf(path: str, max_chars: int = 20000) -> str:
    if PdfReader is None:
        return "[PDF extraction unavailable: install pypdf]"
    reader = PdfReader(path)
    out = []
    total = 0
    for page in reader.pages:
        txt = page.extract_text() or ""
        if not txt:
            continue
        left = max_chars - total
        if left <= 0:
            break
        txt = txt[:left]
        out.append(txt)
        total += len(txt)
    return "\n\n".join(out)


def _read_docx(path: str, max_chars: int = 20000) -> str:
    if Document is None:
        return "[DOCX extraction unavailable: install python-docx]"
    doc = Document(path)
    parts = []
    total = 0
    for p in doc.paragraphs:
        txt = (p.text or "").strip()
        if not txt:
            continue
        left = max_chars - total
        if left <= 0:
            break
        txt = txt[:left]
        parts.append(txt)
        total += len(txt)
    return "\n".join(parts)


def extract_file_text(path: str, max_chars: int = 20000) -> str:
    ext = Path(path).suffix.lower()
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if ext in {".txt", ".md", ".py", ".json", ".csv", ".yaml", ".yml", ".xml", ".html", ".css", ".js", ".ts", ".log", ".ini", ".cfg", ".toml", ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".sh", ".sql", ".r", ".scala", ".kt"}:
        return _read_text_file(path, max_chars)
    if ext == ".pdf":
        return _read_pdf(path, max_chars)
    if ext == ".docx":
        return _read_docx(path, max_chars)
    if mime.startswith("text/"):
        return _read_text_file(path, max_chars)
    if mime.startswith("image/"):
        return f"[Image attached: {Path(path).name}]"
    return f"[Binary file attached: {Path(path).name} ({mime})]"


def simple_chunks(text: str, size: int = 1400, overlap: int = 200) -> List[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    out = []
    start = 0
    n = len(clean)
    while start < n:
        end = min(n, start + size)
        out.append(clean[start:end])
        if end >= n:
            break
        start = max(0, end - overlap)
    return out


def score_chunk(query: str, chunk: str) -> int:
    q_words = {w for w in query.lower().split() if len(w) > 2}
    c = chunk.lower()
    score = 0
    for w in q_words:
        if w in c:
            score += 2
    score += min(len(chunk), 800) // 400
    return score


def build_rag_context(user_text: str, attachments: List[Attachment], max_files: int = 4, top_chunks: int = 6) -> Tuple[str, List[str]]:
    selected_names = []
    collected: List[Tuple[int, str, str]] = []
    for att in attachments[:max_files]:
        try:
            raw = extract_file_text(att.path, max_chars=50000)
        except Exception as exc:
            raw = f"[Could not read {att.name}: {exc}]"
        chunks = simple_chunks(raw)
        if not chunks:
            continue
        selected_names.append(att.name)
        for ch in chunks:
            collected.append((score_chunk(user_text, ch), att.name, ch))
    collected.sort(key=lambda x: x[0], reverse=True)
    chosen = collected[:top_chunks]
    if not chosen:
        return "", selected_names
    merged = []
    for _, name, text in chosen:
        merged.append(f"--- FILE CHUNK: {name} ---\n{text}")
    return "\n\n".join(merged), selected_names



def coerce_content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float, bool)):
        return str(content)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # Gradio message content can sometimes be structured objects.
                txt = item.get("text") or item.get("content") or item.get("value") or item.get("path") or ""
                if txt:
                    parts.append(str(txt))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p).strip()
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or content.get("value") or content.get("path") or "")
    return str(content)


def trim_history(history: List[Dict[str, str]], approx_ctx: int) -> List[Dict[str, str]]:
    max_chars = max(1200, int(approx_ctx) * 4)
    kept = []
    total = 0
    for msg in reversed(history):
        text = coerce_content_to_text(msg.get("content", ""))
        kept.append({"role": msg.get("role", "user"), "content": text})
        total += len(text)
        if total >= max_chars:
            break
    return list(reversed(kept))


def build_history_for_chat(history: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
    msgs = []
    if system_prompt.strip():
        msgs.append({"role": "system", "content": system_prompt.strip()})
    msgs.extend({"role": m.get("role", "user"), "content": coerce_content_to_text(m.get("content", ""))} for m in history)
    return msgs


def b64_of_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def openai_input_items(history: List[Dict[str, str]], attachments: List[Attachment]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for idx, msg in enumerate(history):
        content_parts: List[Dict[str, Any]] = [{"type": "input_text", "text": msg["content"]}]
        if idx == len(history) - 1:
            for att in attachments:
                if att.mime.startswith("image/"):
                    data_url = f"data:{att.mime};base64,{b64_of_file(att.path)}"
                    content_parts.append({"type": "input_image", "image_url": data_url})
                else:
                    content_parts.append({
                        "type": "input_file",
                        "filename": att.name,
                        "file_data": f"data:{att.mime};base64,{b64_of_file(att.path)}",
                    })
        items.append({"role": msg["role"], "content": content_parts})
    return items


def serialize_conversation(history: List[Dict[str, str]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "app": APP_TITLE,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": metadata,
        "history": history,
    }


def save_chat_file(history: List[Dict[str, str]], provider: str, model: str, system_prompt: str) -> Tuple[Optional[str], str]:
    if not history:
        return None, "Nothing to save yet."
    payload = serialize_conversation(history, {"provider": provider, "model": model, "system_prompt": system_prompt})
    fd, path = tempfile.mkstemp(prefix="chat_save_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path, f"Saved chat to {Path(path).name}."


def load_chat_file(file_obj: Optional[str]):
    if not file_obj:
        return [], "No chat file selected."
    try:
        with open(file_obj, "r", encoding="utf-8") as f:
            data = json.load(f)
        history = data.get("history", [])
        if not isinstance(history, list):
            raise ValueError("Invalid history format")
        return history, f"Loaded {Path(file_obj).name}."
    except Exception as exc:
        return [], f"Failed to load chat: {exc}"


def export_chat(history: List[Dict[str, str]], fmt: str) -> Tuple[Optional[str], str]:
    if not history:
        return None, "Nothing to export yet."
    stamp = time.strftime("%Y%m%d_%H%M%S")
    if fmt == "json":
        fd, path = tempfile.mkstemp(prefix=f"chat_{stamp}_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return path, f"Exported JSON: {Path(path).name}"
    if fmt == "txt":
        fd, path = tempfile.mkstemp(prefix=f"chat_{stamp}_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for msg in history:
                f.write(f"{msg['role'].upper()}:\n{msg['content']}\n\n")
        return path, f"Exported TXT: {Path(path).name}"
    fd, path = tempfile.mkstemp(prefix=f"chat_{stamp}_", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# Chat Export\n\n")
        for msg in history:
            f.write(f"## {msg['role'].capitalize()}\n\n{msg['content']}\n\n")
    return path, f"Exported Markdown: {Path(path).name}"


def list_models(provider: str, api_key: str, base_url: str) -> Tuple[List[str], str]:
    try:
        if provider == "Ollama":
            r = requests.get(base_url.rstrip("/") + "/api/tags", timeout=30)
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
            return models, f"Fetched {len(models)} Ollama models."
        if provider == "Gemini":
            if not api_key.strip():
                raise RuntimeError("Gemini API key required to list models.")
            r = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key.strip()},
                timeout=45,
            )
            r.raise_for_status()
            models = []
            for item in r.json().get("models", []):
                name = item.get("name", "")
                if name.startswith("models/"):
                    name = name.split("/", 1)[1]
                if name:
                    models.append(name)
            return models, f"Fetched {len(models)} Gemini models."
        if provider == "OpenAI":
            if not api_key.strip():
                raise RuntimeError("OpenAI API key required to list models.")
            url = (base_url or OPENAI_DEFAULT_URL).rstrip("/") + "/models"
            r = requests.get(url, headers={"Authorization": f"Bearer {api_key.strip()}"}, timeout=45)
            r.raise_for_status()
            models = sorted(m.get("id", "") for m in r.json().get("data", []) if m.get("id"))
            return models, f"Fetched {len(models)} OpenAI models."
        if not api_key.strip():
            raise RuntimeError("DeepSeek API key required to list models.")
        url = (base_url or DEEPSEEK_DEFAULT_URL).rstrip("/") + "/models"
        r = requests.get(url, headers={"Authorization": f"Bearer {api_key.strip()}"}, timeout=45)
        r.raise_for_status()
        models = sorted(m.get("id", "") for m in r.json().get("data", []) if m.get("id"))
        return models, f"Fetched {len(models)} DeepSeek models."
    except Exception as exc:
        return [], f"Model list failed: {exc}"


def fetch_models_ui(provider: str, api_key: str, base_url: str):
    models, msg = list_models(provider, api_key, base_url)
    if not models:
        return gr.update(choices=[], value=None), msg
    return gr.update(choices=models, value=models[0]), msg


def provider_health(provider: str, api_key: str, base_url: str, model: str) -> str:
    started = time.time()
    try:
        if provider == "Ollama":
            r = requests.get(base_url.rstrip("/") + "/api/tags", timeout=15)
            r.raise_for_status()
            return f"✅ Ollama reachable in {int((time.time()-started)*1000)} ms."
        if provider == "Gemini":
            if not api_key.strip():
                raise RuntimeError("Gemini API key missing.")
            r = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}",
                params={"key": api_key.strip()},
                timeout=20,
            )
            r.raise_for_status()
            return f"✅ Gemini reachable in {int((time.time()-started)*1000)} ms."
        if provider == "OpenAI":
            if not api_key.strip():
                raise RuntimeError("OpenAI API key missing.")
            r = requests.get((base_url or OPENAI_DEFAULT_URL).rstrip("/") + "/models", headers={"Authorization": f"Bearer {api_key.strip()}"}, timeout=20)
            r.raise_for_status()
            return f"✅ OpenAI reachable in {int((time.time()-started)*1000)} ms."
        if not api_key.strip():
            raise RuntimeError("DeepSeek API key missing.")
        r = requests.get((base_url or DEEPSEEK_DEFAULT_URL).rstrip("/") + "/models", headers={"Authorization": f"Bearer {api_key.strip()}"}, timeout=20)
        r.raise_for_status()
        return f"✅ DeepSeek reachable in {int((time.time()-started)*1000)} ms."
    except Exception as exc:
        return f"❌ Health check failed: {exc}"




def fetch_model_choices(provider: str, base_url: str, api_key: str):
    return fetch_models_ui(provider, api_key, base_url)


def check_model_health(provider: str, model: str, api_key: str, base_url: str) -> str:
    return provider_health(provider, api_key, base_url, model)




def sync_model_from_picker(selected_model: str, current_model: str) -> str:
    selected_model = (selected_model or "").strip()
    if selected_model:
        return selected_model
    return (current_model or "").strip()


def update_provider_ui(provider: str):
    base_url, model, help_text = provider_defaults(provider)
    return (
        gr.update(value=base_url, visible=provider in {"Ollama", "OpenAI", "DeepSeek"}),
        gr.update(value=model),
        gr.update(value=help_text),
    )


def normalize_chat_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    last_role = None
    for msg in messages:
        role = str(msg.get("role") or "").strip()
        content = coerce_content_to_text(msg.get("content", "")).strip()
        if role not in {"system", "user", "assistant"} or not content:
            continue
        if role == "system":
            if cleaned and cleaned[0].get("role") == "system":
                cleaned[0]["content"] += "\n\n" + content
            elif not cleaned:
                cleaned.append({"role": "system", "content": content})
            else:
                # keep only one leading system prompt
                continue
            last_role = cleaned[-1]["role"]
            continue
        if not cleaned and role == "assistant":
            # Some Ollama models reject assistant-first histories.
            continue
        if last_role == role and role != "system":
            cleaned[-1]["content"] += "\n\n" + content
        else:
            cleaned.append({"role": role, "content": content})
        last_role = cleaned[-1]["role"]
    return cleaned


def stream_ollama(base_url: str, model: str, messages: List[Dict[str, str]], temperature: float, ctx: int, top_p: float, top_k: int, max_tokens: int) -> Generator[str, None, Dict[str, Any]]:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": normalize_chat_messages(messages),
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_ctx": int(ctx),
            "top_p": top_p,
            "num_predict": int(max_tokens) if max_tokens > 0 else -1,
        },
    }
    if top_k > 0:
        payload["options"]["top_k"] = int(top_k)
    with requests.post(url, json=payload, stream=True, timeout=600) as r:
        try:
            r.raise_for_status()
        except requests.HTTPError as exc:
            detail = ""
            try:
                data = r.json()
                detail = data.get("error") or data.get("message") or ""
            except Exception:
                try:
                    detail = r.text[:500]
                except Exception:
                    detail = ""
            if detail:
                raise RuntimeError(f"Ollama error: {detail}") from exc
            raise
        text = ""
        last_obj = {}
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            obj = json.loads(line)
            last_obj = obj
            text += obj.get("message", {}).get("content", "") or ""
            yield text
        return last_obj


def _iter_sse_lines(response: requests.Response) -> Iterable[str]:
    for raw in response.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if raw.startswith("data:"):
            yield raw[5:].strip()


def stream_openai(base_url: str, api_key: str, model: str, input_items: List[Dict[str, Any]], temperature: float, max_tokens: int, top_p: float) -> Generator[str, None, Dict[str, Any]]:
    url = base_url.rstrip("/") + "/responses"
    payload: Dict[str, Any] = {
        "model": model,
        "input": input_items,
        "stream": True,
        "temperature": temperature,
        "top_p": top_p,
    }
    if max_tokens > 0:
        payload["max_output_tokens"] = int(max_tokens)
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        text = ""
        final = {}
        for data in _iter_sse_lines(r):
            if data == "[DONE]":
                break
            event = json.loads(data)
            et = event.get("type", "")
            if et in {"response.output_text.delta", "output_text.delta"}:
                text += event.get("delta", "") or ""
                yield text
            elif et in {"response.completed", "response.failed"}:
                final = event
        return final


def stream_deepseek(base_url: str, api_key: str, model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int, top_p: float) -> Generator[str, None, Dict[str, Any]]:
    url = base_url.rstrip("/") + "/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "stream": True,
    }
    if max_tokens > 0:
        payload["max_tokens"] = int(max_tokens)
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        text = ""
        final = {}
        for data in _iter_sse_lines(r):
            if data == "[DONE]":
                break
            event = json.loads(data)
            final = event
            choices = event.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                piece = delta.get("content") or ""
                if piece:
                    text += piece
                    yield text
        return final


def stream_gemini(api_key: str, model: str, history: List[Dict[str, str]], attachments: List[Attachment], system_prompt: str, temperature: float, max_tokens: int, top_p: float) -> Generator[str, None, Dict[str, Any]]:
    if genai is None or genai_types is None:
        raise RuntimeError("google-genai package is not installed")
    client = genai.Client(api_key=api_key)
    contents: List[Any] = []
    for msg in history[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        msg_text = coerce_content_to_text(msg.get("content", "")).strip()
        if not msg_text:
            continue
        contents.append(
            genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=msg_text)],
            )
        )

    last = history[-1]
    last_text = coerce_content_to_text(last.get("content", "")).strip()
    user_parts: List[Any] = []
    if last_text:
        user_parts.append(genai_types.Part(text=last_text))

    uploaded_refs = []
    for att in attachments:
        uploaded = client.files.upload(file=att.path)
        uploaded_refs.append(uploaded)
        user_parts.append(uploaded)

    if not user_parts:
        raise RuntimeError("Gemini request has no text or files to send.")

    contents.append(genai_types.Content(role="user", parts=user_parts))

    cfg = genai_types.GenerateContentConfig(
        system_instruction=system_prompt.strip() if system_prompt.strip() else None,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=int(max_tokens) if max_tokens > 0 else None,
    )
    text = ""
    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=cfg):
        piece = getattr(chunk, "text", None) or ""
        if piece:
            text += piece
            yield text
    return {"uploaded_files": [u.name for u in uploaded_refs if getattr(u, 'name', None)]}


def compose_user_message(text: str, file_names: List[str]) -> str:
    msg = text.strip() or "Please analyze the uploaded file(s)."
    if file_names:
        msg += "\n\nAttached files: " + ", ".join(file_names)
    return msg


def usage_summary(provider: str, started: float, sent_files: List[str], model: str) -> str:
    ms = int((time.time() - started) * 1000)
    files = ", ".join(sent_files) if sent_files else "none"
    return f"Provider: {provider}<br>Model: {model}<br>Latency: {ms} ms<br>Files: {files}"


def retry_last(history: List[Dict[str, str]]):
    if len(history) < 2:
        return history, "Nothing to retry."
    if history[-1].get("role") != "assistant":
        return history, "Last turn is not a completed assistant response."
    return history[:-1], "Removed last assistant reply. Send again to retry."


def export_buttons(history: List[Dict[str, str]], fmt: str):
    return export_chat(history, fmt)


def run_chat(
    user_text: str,
    file_paths: Optional[List[str]],
    history: List[Dict[str, str]],
    provider: str,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    ctx: int,
    system_prompt: str,
    anim_style: str,
    model_choice: Optional[str] = None,
    max_tokens: int = 1024,
    top_p: float = 0.95,
    top_k: int = 40,
):
    effective_model = (model_choice or model or "").strip()
    history = history or []
    attachments = attachment_from_paths(file_paths)
    if not (user_text or attachments):
        yield history, render_status("error", anim_style, "Type a message or upload at least one file."), gr.update(value=""), None
        return

    rag_context, rag_names = build_rag_context(user_text or "analyze files", attachments)
    user_message = compose_user_message(user_text, [a.name for a in attachments])
    model_user_message = user_message
    if attachments and provider not in {"Gemini", "OpenAI"}:
        if rag_context:
            model_user_message += "\n\nUse the following extracted file context if relevant:\n" + rag_context

    visible_history = list(history) + [{"role": "user", "content": user_message}]
    yield visible_history, render_status("sending", anim_style, "Preparing request, files, and retrieval context."), gr.update(value=""), None

    model_history = trim_history(list(history) + [{"role": "user", "content": model_user_message}], ctx)
    chat_messages = build_history_for_chat(model_history, system_prompt)
    started = time.time()
    final_text = ""

    try:
        yield visible_history + [{"role": "assistant", "content": ""}], render_status("receiving", anim_style, f"Streaming from {provider} / {effective_model}."), gr.update(value=""), None
        if provider == "Ollama":
            streamer = stream_ollama(base_url or OLLAMA_DEFAULT_URL, effective_model, chat_messages, temperature, ctx, top_p, top_k, max_tokens)
        elif provider == "Gemini":
            if not api_key.strip():
                raise RuntimeError("Gemini API key is required.")
            streamer = stream_gemini(api_key.strip(), effective_model, model_history, attachments, system_prompt, temperature, max_tokens, top_p)
        elif provider == "OpenAI":
            if not api_key.strip():
                raise RuntimeError("OpenAI API key is required.")
            input_items = openai_input_items(chat_messages, attachments)
            streamer = stream_openai(base_url or OPENAI_DEFAULT_URL, api_key.strip(), effective_model, input_items, temperature, max_tokens, top_p)
        elif provider == "DeepSeek":
            if not api_key.strip():
                raise RuntimeError("DeepSeek API key is required.")
            streamer = stream_deepseek(base_url or DEEPSEEK_DEFAULT_URL, api_key.strip(), effective_model, chat_messages, temperature, max_tokens, top_p)
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")

        for partial in streamer:
            final_text = partial
            yield visible_history + [{"role": "assistant", "content": final_text}], render_status("receiving", anim_style, f"Streaming from {provider} / {effective_model}."), gr.update(value=""), None

    except Exception as exc:
        err = f"Error: {exc}"
        failed = visible_history + [{"role": "assistant", "content": err}]
        yield failed, render_status("error", anim_style, err), gr.update(value=""), None
        return

    final_history = visible_history + [{"role": "assistant", "content": final_text or "[Empty response]"}]
    status_detail = f"Completed with {provider} / {effective_model}."
    notes = []
    if rag_names and provider not in {"Gemini", "OpenAI"}:
        notes.append("RAG context used: " + ", ".join(rag_names))
    if attachments and provider in {"Gemini", "OpenAI"}:
        notes.append("Native file send used.")
    note_text = " | ".join(notes) if notes else "Response complete."
    yield final_history, render_status("done", anim_style, status_detail), gr.update(value=""), None


def clear_chat(anim_style: str = "Green Scan"):
    return [], render_status("idle", anim_style, "Ready for a new prompt."), "", None


with gr.Blocks(title=APP_TITLE) as demo:
    history_state = gr.State([])

    gr.HTML(HEADER_MD)

    with gr.Group():
        with gr.Row(equal_height=True):
            provider = gr.Dropdown(
                choices=["Ollama", "Gemini", "OpenAI", "DeepSeek"],
                value="Ollama",
                label="Provider",
                scale=1,
                min_width=150,
            )
            current_model = gr.Textbox(value="llama3.2", label="Current model", interactive=False, scale=2, min_width=220)
        provider_help = gr.Markdown("Local Ollama. API key is optional and usually not needed.")

    with gr.Row(equal_height=False):
        with gr.Column(scale=1):
            with gr.Accordion("🧠 Model picker", open=True):
                with gr.Row():
                    model_picker = gr.Dropdown(
                        choices=["llama3.2"],
                        value="llama3.2",
                        label="Available models",
                        allow_custom_value=True,
                        scale=3
                    )
                    fetch_models_btn = gr.Button("Fetch", scale=1, min_width=80)
                model = gr.Textbox(value="llama3.2", label="Model name")
                model_fetch_status = gr.Markdown("Fetch models to populate the list, then pick one or type manually.")
            with gr.Accordion("📎 Files", open=False):
                files = gr.File(label="Upload files", file_count="multiple", type="filepath")
            with gr.Accordion("⚙️ Settings", open=False):
                api_key = gr.Textbox(type="password", label="API key", placeholder="Paste API key here when needed")
                base_url = gr.Textbox(value="http://localhost:11434", label="Base URL", visible=True)
                temperature = gr.Slider(0.0, 2.0, value=0.7, step=0.05, label="Temperature")
                ctx = gr.Slider(1024, 131072, value=8192, step=1024, label="Context / num_ctx")
                system_prompt = gr.Textbox(value=DEFAULT_SYSTEM, lines=4, label="System prompt")
                anim_style = gr.Dropdown(
                    choices=["Green Scan", "Square Dots", "Equalizer", "Orbit Ring"],
                    value="Green Scan",
                    label="Animation style",
                )
                model_health_btn = gr.Button("Check model health")
                model_health_text = gr.Markdown("Model health has not been checked yet.")
                gr.Markdown(
                    "For Ollama, **Context / num_ctx** is sent as `num_ctx`. For hosted APIs, the same slider is used as a local history trim budget before sending requests."
                )

        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Chat", height=430)
            status = gr.HTML(render_status("idle", "Green Scan", "Ready for a new prompt."))
            msg = gr.Textbox(label="Message", placeholder="Ask a question, summarize files, compare documents, explain code...", lines=3)
            with gr.Row():
                send_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear")

    provider.change(update_provider_ui, inputs=[provider], outputs=[base_url, model, provider_help]).then(lambda m: m, inputs=[model], outputs=[current_model])
    provider.change(lambda p: gr.update(value=provider_defaults(p)[1], choices=[provider_defaults(p)[1]]), inputs=[provider], outputs=[model_picker])
    provider.change(lambda: "Fetch models to populate the list, then pick one or type manually.", outputs=[model_fetch_status])
    provider.change(lambda: "Model health has not been checked yet.", outputs=[model_health_text])

    fetch_models_btn.click(
        fetch_model_choices,
        inputs=[provider, base_url, api_key],
        outputs=[model_picker, model_fetch_status],
    )
    model_picker.change(sync_model_from_picker, inputs=[model_picker, model], outputs=[model]).then(lambda m: m, inputs=[model], outputs=[current_model])
    model.change(lambda m: m, inputs=[model], outputs=[current_model])

    model_health_btn.click(
        check_model_health,
        inputs=[provider, model, api_key, base_url],
        outputs=[model_health_text],
    )

    send_event = send_btn.click(
        run_chat,
        inputs=[msg, files, history_state, provider, model, api_key, base_url, temperature, ctx, system_prompt, anim_style],
        outputs=[chatbot, status, msg, files],
    )
    send_event.then(lambda x: x, inputs=[chatbot], outputs=[history_state])

    msg.submit(
        run_chat,
        inputs=[msg, files, history_state, provider, model, api_key, base_url, temperature, ctx, system_prompt, anim_style],
        outputs=[chatbot, status, msg, files],
    ).then(lambda x: x, inputs=[chatbot], outputs=[history_state])

    clear_btn.click(clear_chat, outputs=[chatbot, status, msg, files]).then(lambda: [], outputs=[history_state])


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=8).launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")), theme=gr.themes.Soft(), css=CSS)
