"""Manual integration test — set SOURCE and run: python test.py"""

from dotenv import load_dotenv

load_dotenv()

from utils.audio_processor import process_input, cleanup_audio_files
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions

SOURCE = ""  # e.g. https://www.youtube.com/watch?v=... or path/to/file.mp4
LANGUAGE = "english"


def main():
    if not SOURCE.strip():
        raise SystemExit("Set SOURCE in test.py to a YouTube URL or local file path.")

    cleanup_paths: list[str] = []
    try:
        chunks, cleanup_paths = process_input(SOURCE)
        transcript = transcribe_all(chunks, language=LANGUAGE)

        print("\n" + "=" * 60)
        print("TRANSCRIPT (preview)")
        print("=" * 60)
        preview = transcript[:500] + "..." if len(transcript) > 500 else transcript
        print(preview)

        title = generate_title(transcript)
        summary = summarize(transcript)
        action_items = extract_action_items(transcript)
        decisions = extract_key_decisions(transcript)
        questions = extract_questions(transcript)

        print("\n" + "=" * 60)
        print(f"TITLE: {title}")
        print("=" * 60)
        print("\nSUMMARY")
        print("-" * 60)
        print(summary)
        print("\nACTION ITEMS\n", action_items)
        print("\nKEY DECISIONS\n", decisions)
        print("\nOPEN QUESTIONS\n", questions)
    finally:
        cleanup_audio_files(cleanup_paths)


if __name__ == "__main__":
    main()
