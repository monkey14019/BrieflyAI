import html
import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Bundled FFmpeg for yt-dlp + Whisper (no system install required)
from utils.ffmpeg_tools import configure_ffmpeg
from utils.ui_theme import inject_theme

configure_ffmpeg()

st.set_page_config(
    page_title="ClipMind",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# ─── Session State Init ──────────────────────────────────────────────────────────
for key, default in {
    "result": None,
    "chat_history": [],
    "processing": False,
    "pipeline_done": False,
    "pipeline_steps": {},
    "pipeline_mode": None,       # "audio" or "document"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Helpers ────────────────────────────────────────────────────────────────────
def step_status(steps: dict, key: str) -> str:
    s = steps.get(key, "pending")
    if s == "active":  return "dot-active"
    if s == "done":    return "dot-done"
    return "dot-pending"

def render_step_bar(label: str, key: str, icon: str):
    css = step_status(st.session_state.pipeline_steps, key)
    st.markdown(f"""
    <div class="status-bar">
        <div class="status-dot {css}"></div>
        <span>{icon} {label}</span>
    </div>""", unsafe_allow_html=True)


def esc(text: str) -> str:
    return html.escape(str(text or ""), quote=True).replace("\n", "<br>")

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="hero-title" style="font-size:1.75rem;line-height:1.2">🧠 ClipMind</div>
        <div class="hero-sub" style="letter-spacing:0.25em;margin-top:0.6rem">Video & Document Intelligence</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<span class="badge badge-teal">✦ &nbsp; Input Source</span>', unsafe_allow_html=True)
    source = st.text_input("YouTube URL or File Path", placeholder="https://youtube.com/watch?v=... or /path/to/file.mp4")

    language = st.selectbox("Language", ["english", "hinglish"], index=0)

    run_btn = st.button("⚡  Launch Analysis", use_container_width=True)

    if st.session_state.pipeline_done:
        st.markdown("---")
        st.markdown('<span class="badge badge-green">⚡ Live Pipeline</span>', unsafe_allow_html=True)

        if st.session_state.pipeline_mode == "document":
            # Document pipeline steps
            for step, icon, label in [
                ("doc_parse",  "📄", "Document Parsing"),
                ("title",      "🏷️", "Title Generation"),
                ("summary",    "📋", "Summarisation"),
                ("extract",    "🔍", "Extraction"),
                ("rag",        "🧠", "RAG Engine"),
            ]:
                render_step_bar(label, step, icon)
        else:
            # Audio pipeline steps
            for step, icon, label in [
                ("audio",      "🔊", "Audio Processing"),
                ("transcript", "📝", "Transcription"),
                ("title",      "🏷️", "Title Generation"),
                ("summary",    "📋", "Summarisation"),
                ("extract",    "🔍", "Extraction"),
                ("rag",        "🧠", "RAG Engine"),
            ]:
                render_step_bar(label, step, icon)

# ─── Hero Banner ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">ClipMind</div>
    <div class="hero-sub">Transcribe · Summarise · Extract · Chat</div>
    <div class="hero-pills">
        <span class="badge badge-teal">Whisper AI</span>
        <span class="badge badge-amber">Mistral LLM</span>
        <span class="badge badge-indigo">RAG Engine</span>
        <span class="badge badge-green">Doc Upload</span>
    </div>
</div>""", unsafe_allow_html=True)

# ─── File Upload Section (top of page) ──────────────────────────────────────────
st.markdown("""
<div class="card" style="border:1px dashed rgba(94,234,212,0.4);margin-bottom:1rem">
    <div class="card-title">📄 Upload Transcript / Document</div>
    <div class="card-content" style="opacity:0.7;font-size:0.85rem">
        Upload PDF, TXT, DOCX, or Markdown files to analyse directly — no audio processing needed.
    </div>
</div>""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "txt", "docx", "text", "md"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    key="doc_uploader",
)

doc_run_btn = False
if uploaded_files:
    file_names = ", ".join(f.name for f in uploaded_files)
    st.info(f"📎 **{len(uploaded_files)}** file(s) ready: {file_names}")
    doc_run_btn = st.button("📄  Analyse Document(s)", use_container_width=True, type="primary")

st.markdown("---")

# ── Run Document Pipeline ───────────────────────────────────────────────────────
if doc_run_btn and uploaded_files:
    st.session_state.pipeline_done = False
    st.session_state.result = None
    st.session_state.chat_history = []
    st.session_state.pipeline_steps = {}
    st.session_state.pipeline_mode = "document"

    progress_placeholder = st.empty()
    status_text = st.empty()
    progress_bar = st.progress(0)

    # Document pipeline: 5 steps
    DOC_STEPS = [
        ("doc_parse", "📄 Parsing documents…"),
        ("title",     "🏷️ Generating title…"),
        ("summary",   "📋 Summarising content…"),
        ("extract",   "🔍 Extracting insights…"),
        ("rag",       "🧠 Building RAG index…"),
    ]
    TOTAL_DOC_STEPS = len(DOC_STEPS)

    def update_step(key, state):
        st.session_state.pipeline_steps[key] = state

    def advance_progress(step_idx, label):
        pct = int((step_idx / TOTAL_DOC_STEPS) * 100)
        progress_bar.progress(pct, text=label)
        status_text.markdown(f"**Step {step_idx}/{TOTAL_DOC_STEPS}** — {label}")

    try:
        from core.doc_loader import extract_text
        from core.summarizer import summarize, generate_title
        from core.extractor import (
            extract_action_items,
            extract_key_decisions,
            extract_questions,
        )
        from core.rag_engine import build_rag_chain_from_docs

        with progress_placeholder.container():
            st.info("✨ Document pipeline running — watch the sidebar light up…")

        # ── Step 1: Parse documents ──────────────────────────────────────
        advance_progress(1, DOC_STEPS[0][1])
        update_step("doc_parse", "active")
        all_texts: list[str] = []
        source_labels: list[str] = []
        for f in uploaded_files:
            raw = f.read()
            text = extract_text(f.name, raw)
            all_texts.append(text)
            source_labels.append(f.name)
        combined_text = "\n\n".join(all_texts)
        update_step("doc_parse", "done")

        # ── Step 2: Title ────────────────────────────────────────────────
        advance_progress(2, DOC_STEPS[1][1])
        update_step("title", "active")
        title = generate_title(combined_text)
        update_step("title", "done")

        # ── Step 3: Summary ─────────────────────────────────────────────
        advance_progress(3, DOC_STEPS[2][1])
        update_step("summary", "active")
        summary = summarize(combined_text)
        update_step("summary", "done")

        # ── Step 4: Extraction ──────────────────────────────────────────
        advance_progress(4, DOC_STEPS[3][1])
        update_step("extract", "active")
        action_items = extract_action_items(combined_text)
        decisions = extract_key_decisions(combined_text)
        questions = extract_questions(combined_text)
        update_step("extract", "done")

        # ── Step 5: RAG ─────────────────────────────────────────────────
        advance_progress(5, DOC_STEPS[4][1])
        update_step("rag", "active")
        rag_chain = build_rag_chain_from_docs(all_texts, source_labels)
        update_step("rag", "done")

        progress_bar.progress(100, text="✅ Complete!")
        status_text.empty()

        st.session_state.result = {
            "title": title,
            "transcript": combined_text,
            "summary": summary,
            "action_items": action_items,
            "key_decisions": decisions,
            "open_questions": questions,
            "rag_chain": rag_chain,
        }
        st.session_state.pipeline_done = True
        progress_placeholder.success("✅ Document analysis complete!")
        time.sleep(0.8)
        progress_placeholder.empty()
        progress_bar.empty()
        st.rerun()

    except Exception as e:
        for k in ["doc_parse", "title", "summary", "extract", "rag"]:
            if st.session_state.pipeline_steps.get(k) == "active":
                st.session_state.pipeline_steps[k] = "pending"
        progress_bar.empty()
        status_text.empty()
        progress_placeholder.error(f"❌ Error: {e}")

# ── Run Audio Pipeline ──────────────────────────────────────────────────────────
if run_btn:
    if not source.strip():
        st.error("Please enter a YouTube URL or file path.")
    else:
        st.session_state.pipeline_done = False
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = {}
        st.session_state.pipeline_mode = "audio"

        progress_placeholder = st.empty()
        status_text = st.empty()
        progress_bar = st.progress(0)

        # Audio pipeline: 6 steps
        AUDIO_STEPS = [
            ("audio",      "🔊 Processing audio…"),
            ("transcript", "📝 Transcribing with Whisper…"),
            ("title",      "🏷️ Generating title…"),
            ("summary",    "📋 Summarising transcript…"),
            ("extract",    "🔍 Extracting insights…"),
            ("rag",        "🧠 Building RAG index…"),
        ]
        TOTAL_AUDIO_STEPS = len(AUDIO_STEPS)

        def update_step(key, state):
            st.session_state.pipeline_steps[key] = state

        def advance_progress(step_idx, label):
            pct = int((step_idx / TOTAL_AUDIO_STEPS) * 100)
            progress_bar.progress(pct, text=label)
            status_text.markdown(f"**Step {step_idx}/{TOTAL_AUDIO_STEPS}** — {label}")

        from utils.audio_processor import cleanup_audio_files, process_input

        cleanup_paths: list[str] = []
        try:
            # Whisper / embeddings load only when analysis runs
            from core.transcriber import transcribe_all
            from core.summarizer import summarize, generate_title
            from core.extractor import (
                extract_action_items,
                extract_key_decisions,
                extract_questions,
            )
            from core.rag_engine import build_rag_chain

            with progress_placeholder.container():
                st.info("✨ Pipeline running — watch the sidebar light up…")

            # Step 1
            advance_progress(1, AUDIO_STEPS[0][1])
            update_step("audio", "active")
            chunks, cleanup_paths = process_input(source)
            update_step("audio", "done")

            # Step 2
            advance_progress(2, AUDIO_STEPS[1][1])
            update_step("transcript", "active")
            transcript = transcribe_all(chunks, language)
            update_step("transcript", "done")

            # Step 3
            advance_progress(3, AUDIO_STEPS[2][1])
            update_step("title", "active")
            title = generate_title(transcript)
            update_step("title", "done")

            # Step 4
            advance_progress(4, AUDIO_STEPS[3][1])
            update_step("summary", "active")
            summary = summarize(transcript)
            update_step("summary", "done")

            # Step 5
            advance_progress(5, AUDIO_STEPS[4][1])
            update_step("extract", "active")
            action_items = extract_action_items(transcript)
            decisions = extract_key_decisions(transcript)
            questions = extract_questions(transcript)
            update_step("extract", "done")

            # Step 6
            advance_progress(6, AUDIO_STEPS[5][1])
            update_step("rag", "active")
            rag_chain = build_rag_chain(transcript)
            update_step("rag", "done")

            progress_bar.progress(100, text="✅ Complete!")
            status_text.empty()

            st.session_state.result = {
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
                "rag_chain": rag_chain,
            }
            st.session_state.pipeline_done = True
            progress_placeholder.success("✅ Analysis complete!")
            time.sleep(0.8)
            progress_placeholder.empty()
            progress_bar.empty()
            st.rerun()

        except Exception as e:
            for k in ["audio","transcript","title","summary","extract","rag"]:
                if st.session_state.pipeline_steps.get(k) == "active":
                    st.session_state.pipeline_steps[k] = "pending"
            progress_bar.empty()
            status_text.empty()
            progress_placeholder.error(f"❌ Error: {e}")
        finally:
            cleanup_audio_files(cleanup_paths)

# ── Results ──────────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # Title banner
    st.markdown(f"""
    <div class="card card-delay-1">
        <div class="card-title">✦ Session Title</div>
        <div class="card-title-lg">{esc(r['title'])}</div>
    </div>""", unsafe_allow_html=True)

    @st.cache_data(show_spinner=False)
    def _report_txt(title, summary, transcript, action_items, key_decisions, open_questions):
        from utils.export import export_txt

        return export_txt({
            "title": title,
            "summary": summary,
            "transcript": transcript,
            "action_items": action_items,
            "key_decisions": key_decisions,
            "open_questions": open_questions,
        })

    @st.cache_data(show_spinner=False)
    def _report_pdf(title, summary, action_items, key_decisions, open_questions):
        from utils.export import export_pdf

        return export_pdf({
            "title": title,
            "summary": summary,
            "action_items": action_items,
            "key_decisions": key_decisions,
            "open_questions": open_questions,
        })

    export_col1, export_col2, _ = st.columns([1, 1, 3])
    with export_col1:
        st.download_button(
            "⬇️ Download TXT",
            data=_report_txt(
                r["title"], r["summary"], r["transcript"],
                r["action_items"], r["key_decisions"], r["open_questions"],
            ),
            file_name="meeting_report.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with export_col2:
        st.download_button(
            "⬇️ Download PDF",
            data=_report_pdf(
                r["title"], r["summary"],
                r["action_items"], r["key_decisions"], r["open_questions"],
            ),
            file_name="meeting_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    # Top row: summary + transcript/document text
    col1, col2 = st.columns([3, 2], gap="medium")

    with col1:
        st.markdown(f"""
        <div class="card card-delay-2">
            <div class="card-title">📋 Executive Summary</div>
            <div class="card-content">{esc(r['summary'])}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        expander_label = "📝 Full Transcript" if st.session_state.pipeline_mode == "audio" else "📄 Full Document Text"
        with st.expander(expander_label, expanded=False):
            st.markdown(f'<div class="transcript-box">{esc(r["transcript"])}</div>', unsafe_allow_html=True)

    # Second row: action items | decisions | questions
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(f"""
        <div class="card card-delay-3">
            <div class="card-title">✅ Action Items</div>
            <div class="card-content">{esc(r['action_items'])}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card card-delay-4">
            <div class="card-title">🔑 Key Decisions</div>
            <div class="card-content">{esc(r['key_decisions'])}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card card-delay-5">
            <div class="card-title">❓ Open Questions</div>
            <div class="card-content">{esc(r['open_questions'])}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── RAG Chat ──────────────────────────────────────────────────────────────
    chat_label = "💬 Chat with your Content"
    st.markdown(f'<div class="section-title">{chat_label}</div>', unsafe_allow_html=True)

    # Chat history display
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-end">
                    <span class="chat-label user-label">You</span>
                    <div class="chat-bubble user-bubble">{esc(msg['content'])}</div>
                </div>"""
            else:
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-start">
                    <span class="chat-label bot-label">🤖 Assistant</span>
                    <div class="chat-bubble bot-bubble">{esc(msg['content'])}</div>
                </div>"""
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem">
            <div class="empty-icon" style="font-size:2.5rem">💬</div>
            <div class="empty-desc" style="margin-top:0.75rem">Ask anything about your content</div>
        </div>""", unsafe_allow_html=True)

    # Chat input
    chat_col1, chat_col2 = st.columns([5, 1], gap="small")
    with chat_col1:
        user_input = st.text_input("Your question", placeholder="What were the main decisions made?", label_visibility="collapsed")
    with chat_col2:
        send_btn = st.button("Send →", use_container_width=True)

    if send_btn and user_input.strip():
        from core.rag_engine import ask_question

        with st.spinner("Thinking…"):
            answer = ask_question(r["rag_chain"], user_input.strip())
        st.session_state.chat_history.append({"role": "user",      "content": user_input.strip()})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

else:
    # Empty state
    st.markdown("""
    <div class="empty-hero">
        <div class="empty-icon">🧠</div>
        <div class="empty-title">Ready to Analyse</div>
        <div class="empty-desc">
            Paste a YouTube URL or local file path in the sidebar, or
            <strong style="color:#5eead4">upload a document</strong> above,
            then hit <strong style="color:#5eead4">Launch Analysis</strong> to transform your content into insights.
        </div>
        <div class="hero-pills" style="margin-top:2rem">
            <span class="badge badge-teal">Transcription</span>
            <span class="badge badge-amber">Summarisation</span>
            <span class="badge badge-green">RAG Chat</span>
            <span class="badge badge-indigo">Doc Upload</span>
        </div>
        <div class="feature-ring">
            <div class="feature-item">
                <div class="feature-icon">🎙️</div>
                <div class="feature-label">Listen</div>
            </div>
            <div class="feature-item" style="animation-delay:0.15s">
                <div class="feature-icon">📄</div>
                <div class="feature-label">Read</div>
            </div>
            <div class="feature-item" style="animation-delay:0.3s">
                <div class="feature-icon">🧠</div>
                <div class="feature-label">Understand</div>
            </div>
            <div class="feature-item" style="animation-delay:0.45s">
                <div class="feature-icon">💡</div>
                <div class="feature-label">Act</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)