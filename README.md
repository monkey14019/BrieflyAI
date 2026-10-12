# ClipMind

Transcribe meetings from YouTube or local audio/video, summarize them with Mistral AI, extract action items and decisions, and chat with the transcript via RAG.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) or pip

Audio is **downloaded with yt-dlp**, then **converted to WAV** with bundled FFmpeg (`imageio-ffmpeg`). No system FFmpeg/ffprobe install required.

## Setup

```bash
# Install dependencies
uv sync

# Copy env template and add your keys
copy .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | Yes | Mistral API key for summary, extraction, and chat |
| `SARVAM_API_KEY` | For Hinglish | Sarvam API key when using **hinglish** transcription |
| `WHISPER_MODEL` | No | Whisper size (default: `small`) |

## Run

**Streamlit UI (recommended):**

```bash
uv run streamlit run app.py
```

**CLI:**

```bash
uv run python main.py
```

## Usage

1. Paste a YouTube URL or local file path (`.mp4`, `.mp3`, `.wav`, etc.).
2. Choose **english** (local Whisper) or **hinglish** (Sarvam, translates to English).
3. Click **Analyse** and wait for the pipeline to finish.
4. Review summary, action items, decisions, and open questions.
5. Chat with the meeting transcript or download TXT/PDF reports.

## Project layout

```
app.py              # Streamlit UI
main.py             # CLI entry point
core/
  transcriber.py    # Whisper / Sarvam STT
  summarizer.py     # Map-reduce summarization
  extractor.py      # Action items, decisions, questions
  vector_store.py   # Chroma embeddings
  rag_engine.py     # RAG Q&A chain
  llm.py            # Shared Mistral client
utils/
  audio_processor.py
  export.py
```

## Notes

- First run downloads the Whisper model and embedding model; this can take several minutes.
- Temporary audio chunks are deleted after each run.
- The vector store is rebuilt on each analysis in `vector_db/`.
