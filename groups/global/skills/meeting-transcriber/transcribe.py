#!/usr/bin/env python3
"""Poll Google Drive for new Meet recordings, transcribe via Gemini, write to workspace."""

import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from google import genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SLACK_LOG_CHANNEL = "C0ALJGPQSL8"    # #meeting-transcription-logs
SLACK_SUMMARIES_CHANNEL = "C0AQ6D4KPGQ"  # #meeting-summaries

SCRIPT_DIR = Path(__file__).resolve().parent
LOCK_FILE = Path(tempfile.gettempdir()) / "fishbone-transcriber.lock"
WORKSPACE = Path("/workspace/global")

_current_recording: str | None = None


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w.\-]", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


def recording_slug(drive_file: dict) -> str:
    original_name = drive_file["name"]
    name_no_ext = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
    slug = slugify(name_no_ext.lower())
    return slug if slug else f"recording-{drive_file['id']}"


def load_config() -> dict:
    with open(SCRIPT_DIR / "config.json") as f:
        return json.load(f)


def acquire_lock() -> bool:
    try:
        lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquire_lock._fd = lock_fd  # type: ignore[attr-defined]
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def get_slack_token() -> str | None:
    return os.environ.get("SLACK_BOT_TOKEN")


def slack_notify(
    text: str,
    token: str | None = None,
    thread_ts: str | None = None,
    channel: str | None = None,
    broadcast: bool = False,
) -> str | None:
    if not token:
        token = get_slack_token()
    if not token:
        return None
    try:
        payload: dict = {"channel": channel or SLACK_LOG_CHANNEL, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if broadcast and thread_ts:
            payload["reply_broadcast"] = True
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return data.get("message", {}).get("ts")
    except Exception:
        pass
    return None


def slack_react(emoji: str, thread_ts: str, token: str | None = None, channel: str | None = None) -> None:
    if not token:
        token = get_slack_token()
    if not token:
        return
    try:
        requests.post(
            "https://slack.com/api/reactions.add",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"channel": channel or SLACK_LOG_CHANNEL, "name": emoji, "timestamp": thread_ts},
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SIGTERM handler
# ---------------------------------------------------------------------------

def _sigterm_handler(signum, frame):
    msg = "⚠️ Meeting transcriber was killed by SIGTERM"
    if _current_recording:
        msg += f" — was processing: *{_current_recording}* (transcript may be incomplete)"
    slack_notify(msg)
    sys.exit(1)


signal.signal(signal.SIGTERM, _sigterm_handler)


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

def get_drive_service():
    sa_env = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_env:
        sys.exit("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")
    # Support both inline JSON string and a file path
    if sa_env.strip().startswith("{"):
        import tempfile as _tf
        tmp = _tf.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(sa_env)
        tmp.flush()
        sa_path = tmp.name
    else:
        sa_path = sa_env
    creds = service_account.Credentials.from_service_account_file(
        sa_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)


def list_drive_recordings(drive, folder_id: str) -> list:
    results = []
    page_token = None
    while True:
        resp = drive.files().list(
            q=(
                f"'{folder_id}' in parents and trashed = false and "
                "(mimeType contains 'video/' or mimeType contains 'audio/')"
            ),
            fields="nextPageToken, files(id, name, createdTime, mimeType)",
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def download_file(drive, file_id: str, dest_path: Path) -> None:
    request = drive.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state(state_path: Path) -> dict:
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {"processed": []}


def save_state(state_path: Path, state: dict) -> None:
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Audio / video utilities
# ---------------------------------------------------------------------------

def get_duration_seconds(video_path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return None


def format_duration(secs: float) -> str:
    mins, s = divmod(int(secs), 60)
    hrs, m = divmod(mins, 60)
    if hrs:
        return f"{hrs}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def extract_audio(video_path: Path) -> Path:
    audio_path = video_path.with_suffix(".mp3")
    result = subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-vn", "-acodec", "mp3", "-q:a", "4", str(audio_path), "-y"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
    return audio_path


# ---------------------------------------------------------------------------
# Gemini transcription
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTIONS = """\
את/ה מומחה/ית בתמלול מדויק. **המשימה הקריטית ביותר שלך היא לעבד קובץ שמע של פגישת עבודה בין שותפים בסטארטאפ, ולהפיק על בסיסה תעתיק ורבטים (Verbatim) נקי ומדויק של השיחה.**
המסמך אינו סיכום, אלא תיעוד קרוב ככל האפשר למלל המקורי, לאחר עריכה מינימלית.
המסמך יתבסס **באופן בלעדי ומוחלט** על המידע הנשמע בהקלטה, תוך הקפדה חמורה על הכללים להלן.

---

## כללי יסוד קריטיים ובלתי מתפשרים

* **דיוק אבסולוטי בזיהוי דוברים:** זוהי הדרישה החשובה ביותר. יש לזהות את הדוברים לפי שם פרטי אם ניתן לשמוע אותו בהקלטה; אחרת, יש לתייג כ-`[דובר 1]`, `[דובר 2]` וכן הלאה, באופן עקבי לאורך כל התמליל.

* **דיוק מוחלט בתוכן:** **עדיף חוסר מידע על פני מידע שגוי.** אם מילה או משפט אינם ברורים לחלוטין, סמן אותם כ-`[לא ברור]`. אסור לנחש או להשלים מידע.

* **שמירה על מונחים עסקיים:** יש לשמור מונחים מקצועיים כפי שנאמרו, כולל מונחי אנגלית (GTM, pipeline, churn, onboarding וכו').

* **עריכה וניקיון:**
  * **הסרת מילות מילוי (Filler Words):** יש להסיר מילים כמו "אהה", "אממ", "כאילו", "בעצם" וכדומה.
  * **הסרת חזרות מיותרות:** אם דובר חוזר על אותה מילה ברצף באופן לא מהותי, רשום פעם אחת. אם החזרה מדגישה עמדה — השאר.

---

## פורמט ודוגמה

הפורמט חייב להיות: `[שם/תפקיד]: [תוכן הדברים]`

כל אמירה של דובר חייבת להופיע בשורה משלה בלבד.

דוגמה נכונה:
אוהב: אני חושב שצריך לשנות את ה-pricing.
אבישי: נכון, אבל קודם בוא נסיים את ה-onboarding.

---

**הנחיות שפה:**
כתוב בעברית תקנית בלבד. השתמש באותיות אנגליות למונחים עסקיים וטכנולוגיים (SaaS, GTM, API וכו').
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "תמליל": {
            "type": "string",
            "description": "תעתיק ורבטים נקי של הפגישה עם תיוג דוברים",
        }
    },
    "required": ["תמליל"],
}


def transcribe_audio(
    file_path: Path,
    api_key: str,
    model: str,
    slack_token: str | None = None,
    thread_ts: str | None = None,
    owner: str | None = None,
) -> str:
    import time
    from google.genai import types
    from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted

    FALLBACK_MODELS = [model, "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
    seen: set = set()
    model_chain = [m for m in FALLBACK_MODELS if not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]

    client = genai.Client(api_key=api_key)

    audio_path = extract_audio(file_path)

    uploaded = client.files.upload(file=audio_path, config={"mime_type": "audio/mpeg"})

    for _ in range(30):
        file_info = client.files.get(name=uploaded.name)
        if file_info.state.name == "ACTIVE":
            break
        elif file_info.state.name == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {uploaded.name}")
        time.sleep(10)
    else:
        raise RuntimeError(f"Timed out waiting for Gemini file: {uploaded.name}")

    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, (ServiceUnavailable, ResourceExhausted)):
            return True
        msg = str(exc).upper()
        for marker in ("503", "UNAVAILABLE", "OVERLOADED", "RESOURCE_EXHAUSTED", "QUOTA"):
            if marker in msg:
                return True
        for attr in ("status_code", "code"):
            if getattr(exc, attr, None) in (429, 503):
                return True
        return False

    last_error: Exception | None = None
    for attempt_model in model_chain:
        for attempt in range(3):
            if attempt > 0:
                wait = 30 * (2 ** (attempt - 1))
                slack_notify(
                    f"⏳ Gemini overloaded — retrying in {wait}s (model: `{attempt_model}`)...",
                    slack_token, thread_ts=thread_ts,
                )
                time.sleep(wait)
            try:
                owner_hint = ""
                if owner:
                    owner_display = {"avishay": "אבישי", "ohav": "אוהב"}.get(owner.lower(), owner)
                    owner_hint = (
                        f"\n\n**רמז על המשתתפים:** ההקלטה נמצאת בתיקיית Drive של {owner_display}. "
                        f"השתמש בזה כרמז לזיהוי דוברים."
                    )
                response = client.models.generate_content(
                    model=attempt_model,
                    contents=[uploaded, SYSTEM_INSTRUCTIONS + owner_hint],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                    ),
                )
                result = json.loads(response.text)
                if attempt_model != model:
                    slack_notify(
                        f"ℹ️ Used fallback model `{attempt_model}`.",
                        slack_token, thread_ts=thread_ts,
                    )
                return result["תמליל"]
            except Exception as e:
                if _is_retryable(e):
                    last_error = e
                    continue
                raise
        slack_notify(
            f"⚠️ Model `{attempt_model}` exhausted retries — trying next fallback...",
            slack_token, thread_ts=thread_ts,
        )

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def write_transcript(output_dir: Path, drive_file: dict, transcript: str) -> Path:
    created = drive_file.get("createdTime", "")
    if created:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    original_name = drive_file["name"]
    stem = recording_slug(drive_file)
    filename = f"{date_str}-{stem}.md"

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename
    out_path.write_text(
        f"# Meeting Transcription -- {date_str}\n\n"
        f"**Source:** {original_name}\n"
        f"**Date:** {date_str}\n"
        f"**Language:** Hebrew\n\n"
        f"## Transcription\n\n"
        f"{transcript}\n",
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not acquire_lock():
        print("Another transcriber instance is running. Exiting.")
        return

    config = load_config()
    folder_ids: dict = config["drive_folder_ids"]
    output_dir_rel: str = config.get("output_dir", "calls/meetings")
    model: str = config.get("model", "gemini-2.5-pro")

    api_key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY env var not set")
    slack_token = os.environ.get("SLACK_BOT_TOKEN")

    output_dir = WORKSPACE / output_dir_rel
    state_path = output_dir / ".transcriber-state.json"
    state = load_state(state_path)
    processed_ids = set(state["processed"])

    print("Connecting to Google Drive...")
    drive = get_drive_service()

    recordings = []
    for owner, folder_id in folder_ids.items():
        print(f"Listing recordings in {owner}'s folder ({folder_id})...")
        for rec in list_drive_recordings(drive, folder_id):
            rec["owner"] = owner
            recordings.append(rec)

    new_recordings = [r for r in recordings if r["id"] not in processed_ids]
    if not new_recordings:
        print("No new recordings to process.")
        return

    print(f"Found {len(new_recordings)} new recording(s).")

    cache_dir = Path(tempfile.gettempdir()) / "fishbone-transcriber-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    new_transcripts = []

    for rec in new_recordings:
        global _current_recording
        _current_recording = rec["name"]
        print(f"\nProcessing: {rec['name']}")
        thread_ts = slack_notify(f"🟡 Starting: *{rec['name']}*", slack_token)
        duration_str = "unknown"

        try:
            safe_filename = slugify(rec["name"])
            local_path = cache_dir / safe_filename

            if not local_path.exists():
                download_file(drive, rec["id"], local_path)

            raw_secs = get_duration_seconds(local_path)
            if raw_secs is not None:
                duration_str = format_duration(raw_secs)

            MIN_DURATION_SECONDS = 60
            if raw_secs is not None and raw_secs < MIN_DURATION_SECONDS:
                slack_notify(
                    f"⏭️ Skipped: only {raw_secs:.1f}s — too short.",
                    slack_token, thread_ts=thread_ts,
                )
                state["processed"].append(rec["id"])
                save_state(state_path, state)
                local_path.unlink(missing_ok=True)
                _current_recording = None
                continue

            transcript = transcribe_audio(local_path, api_key, model, slack_token, thread_ts=thread_ts, owner=rec.get("owner"))
            local_path.unlink(missing_ok=True)

            out_path = write_transcript(output_dir, rec, transcript)
            rel_transcript = str(out_path.relative_to(WORKSPACE))
            print(f"  Wrote {rel_transcript}")

            state["processed"].append(rec["id"])
            save_state(state_path, state)

            if thread_ts:
                slack_react("white_check_mark", thread_ts, slack_token)
            slack_notify(
                f"✅ Done: `{rel_transcript}` _{duration_str}_",
                slack_token, thread_ts=thread_ts,
            )
            new_transcripts.append((rel_transcript, rec.get("owner")))
            _current_recording = None

        except Exception as e:
            print(f"  ERROR processing {rec['name']}: {e}", file=sys.stderr)
            if thread_ts:
                slack_react("x", thread_ts, slack_token)
            slack_notify(
                f"❌ Error processing *{rec['name']}*: {e}",
                slack_token, thread_ts=thread_ts, broadcast=True,
            )
            continue

    # Print new transcripts for the agent to pick up and process
    if new_transcripts:
        print("\nNEW_TRANSCRIPTS:")
        for rel_path, owner in new_transcripts:
            owner_hint = f" (recorded from {owner}'s Drive)" if owner else ""
            print(f"  {rel_path}{owner_hint}")
    print("\nDone.")


if __name__ == "__main__":
    main()
