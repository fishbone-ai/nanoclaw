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
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
import supabase_store
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


def meeting_id_for(drive_file: dict) -> str:
    """Meeting id = transcript filename stem: YYYY-MM-DD-<slug>."""
    created = drive_file.get("createdTime", "")
    if created:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{date_str}-{recording_slug(drive_file)}"


def infer_source(filename: str) -> str:
    name = filename.lower()
    if name.startswith("phone_"):
        return "phone"
    if name.startswith("whatsapp_"):
        return "whatsapp"
    if name.startswith("voice-"):
        return "voice"
    return "meet"


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


# Recordings longer than this threshold are split into chunks before transcription.
# Gemini hits its output token limit on single calls for long audio, causing truncation.
CHUNK_THRESHOLD_SECONDS = 600   # 10 minutes (lowered from 15 — recordings under 15min were hitting MAX_TOKENS)
CHUNK_DURATION_SECONDS  = 480   # 8 minutes per chunk (lowered from 14 for headroom)


def split_audio_into_chunks(audio_path: Path, chunk_duration: int = CHUNK_DURATION_SECONDS) -> list[Path]:
    """Split an MP3 into fixed-duration chunks. Returns list of chunk paths."""
    duration = get_duration_seconds(audio_path)
    if duration is None:
        raise RuntimeError(f"Could not determine duration of {audio_path}")
    n_chunks = max(1, int(duration / chunk_duration) + (1 if duration % chunk_duration else 0))
    chunks = []
    for i in range(n_chunks):
        start = i * chunk_duration
        chunk_path = audio_path.parent / f"{audio_path.stem}-chunk{i+1}.mp3"
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ss", str(start), "-t", str(chunk_duration),
                "-acodec", "libmp3lame", "-q:a", "4", str(chunk_path),
                "-loglevel", "error",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg chunk split failed: {result.stderr[-500:]}")
        if chunk_path.exists() and chunk_path.stat().st_size > 0:
            chunks.append(chunk_path)
    return chunks


# ---------------------------------------------------------------------------
# Gemini transcription
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTIONS = """\
את/ה מומחה/ית בתמלול מדויק. **המשימה הקריטית ביותר שלך היא לעבד קובץ שמע של פגישת עסקים, ולהפיק על בסיסה תעתיק ורבטים (Verbatim) נקי ומדויק של השיחה.**
המסמך אינו סיכום, אלא תיעוד קרוב ככל האפשר למלל המקורי, לאחר עריכה מינימלית.
המסמך יתבסס **באופן בלעדי ומוחלט** על המידע הנשמע בהקלטה, תוך הקפדה חמורה על הכללים להלן.

---

## כללי יסוד קריטיים ובלתי מתפשרים

* **דיוק אבסולוטי בזיהוי דוברים:** זוהי הדרישה החשובה ביותר.
  * שם ייוחס לדובר **רק** אם מתקיים אחד מאלה: (א) השם נשמע בהקלטה בצורה ברורה, או (ב) השם מופיע בשם קובץ ההקלטה שסופק.
  * **אסור בהחלט לנחש שמות על סמך הקשר, ידע קודם, או הנחות לגבי מי עשוי להשתתף בשיחה.** טעות בזיהוי גרועה מאי-זיהוי.
  * אם שם הדובר אינו ידוע לפי הכללים לעיל — תייג כ-`[דובר 1]`, `[דובר 2]` וכן הלאה, באופן עקבי לאורך כל התמליל.

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
[דובר 2]: נכון, אבל קודם בוא נסיים את ה-onboarding.

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



def _wait_for_active(client, uploaded_file, timeout_polls: int = 30) -> None:
    """Poll until a Gemini uploaded file reaches ACTIVE state."""
    import time
    for _ in range(timeout_polls):
        info = client.files.get(name=uploaded_file.name)
        if info.state.name == "ACTIVE":
            return
        elif info.state.name == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {uploaded_file.name}")
        time.sleep(10)
    raise RuntimeError(f"Timed out waiting for Gemini file: {uploaded_file.name}")


class _MaxTokensError(RuntimeError):
    """Raised when Gemini hits its output token limit (causes silent mid-sentence truncation in JSON mode)."""
    pass


def _transcribe_single_file(
    client,
    uploaded_file,
    model_chain: list[str],
    owner_hint: str,
    chunk_label: str,
    slack_token: str | None,
    thread_ts: str | None,
) -> str:
    """Run generate_content on a single already-uploaded Gemini file, with retries."""
    import time
    from google.genai import types
    from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted

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
                    f"⏳ Gemini overloaded — retrying {chunk_label} in {wait}s (model: `{attempt_model}`)...",
                    slack_token, thread_ts=thread_ts,
                )
                time.sleep(wait)
            try:
                response = client.models.generate_content(
                    model=attempt_model,
                    contents=[uploaded_file, SYSTEM_INSTRUCTIONS + owner_hint],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        max_output_tokens=65536,
                    ),
                )
                # Check for None response (safety filters / empty output)
                if response.text is None:
                    raise RuntimeError(
                        f"Gemini returned None response for {chunk_label} "
                        f"(candidates: {response.candidates!r})"
                    )
                # Check for MAX_TOKENS — JSON mode silently truncates string fields,
                # so json.loads() succeeds but the transcript is cut off mid-sentence.
                if response.candidates:
                    finish_reason = getattr(response.candidates[0], "finish_reason", None)
                    if finish_reason is not None:
                        reason_name = getattr(finish_reason, "name", str(finish_reason))
                        if reason_name == "MAX_TOKENS":
                            token_count = getattr(
                                getattr(response, "usage_metadata", None),
                                "candidates_token_count", "?"
                            )
                            raise _MaxTokensError(
                                f"Gemini hit MAX_TOKENS for {chunk_label} "
                                f"({token_count} output tokens) — transcript would be truncated"
                            )
                result = json.loads(response.text)
                return result["תמליל"]
            except Exception as e:
                if _is_retryable(e):
                    last_error = e
                    continue
                raise
        slack_notify(
            f"⚠️ Model `{attempt_model}` exhausted retries for {chunk_label} — trying next fallback...",
            slack_token, thread_ts=thread_ts,
        )
    raise RuntimeError(f"All Gemini models failed for {chunk_label}. Last error: {last_error}")


def _upload_wait_transcribe_chunk(
    client,
    chunk_path: Path,
    model_chain: list[str],
    owner_hint: str,
    label: str,
    slack_token: str | None,
    thread_ts: str | None,
) -> str:
    """Upload a chunk, wait for Gemini to process it, transcribe, and clean up."""
    uploaded = client.files.upload(file=chunk_path, config={"mime_type": "audio/mpeg"})
    _wait_for_active(client, uploaded)
    slack_notify(f"📝 Transcribing {label}...", slack_token, thread_ts=thread_ts)
    text = _transcribe_single_file(client, uploaded, model_chain, owner_hint, label, slack_token, thread_ts)
    chunk_path.unlink(missing_ok=True)
    return text


def _transcribe_chunks_sequential(
    client,
    chunks: list[Path],
    model_chain: list[str],
    owner_hint: str,
    label_suffix: str,
    slack_token: str | None,
    thread_ts: str | None,
    state_path: "Path | None" = None,
    file_id: str | None = None,
) -> list[str]:
    """Transcribe chunks one at a time, passing the tail of each chunk as context
    to the next so Gemini maintains consistent speaker labels across boundaries.

    If state_path and file_id are provided, each completed chunk is saved immediately.
    On restart, already-completed chunks are skipped and prior_context is rebuilt
    from the last saved chunk.
    """
    n = len(chunks)

    # Load any chunks already saved from a previous (killed) run
    saved: dict[str, str] = {}
    if state_path and file_id:
        s = load_state(state_path)
        saved = s.get("chunk_cache", {}).get(file_id, {})
        if saved:
            slack_notify(
                f"♻️ Resuming: {len(saved)}/{n} chunks already done — skipping those.",
                slack_token, thread_ts=thread_ts,
            )

    results: dict[str, str] = dict(saved)

    def _save_chunk(index: int, text: str) -> None:
        if not (state_path and file_id):
            return
        s = load_state(state_path)
        s.setdefault("chunk_cache", {}).setdefault(file_id, {})[str(index)] = text
        save_state(state_path, s)

    def _tail_lines(text: str, n_lines: int = 15) -> str:
        lines = [ln for ln in text.strip().split("\n") if ln.strip()]
        return "\n".join(lines[-n_lines:])

    # Rebuild prior_context from the last already-saved chunk (resumability)
    prior_context = ""
    for i in range(n):
        if str(i) in saved:
            prior_context = _tail_lines(saved[str(i)])

    for i, chunk_path in enumerate(chunks):
        if str(i) in saved:
            continue

        label = f"chunk {i+1}/{n}{label_suffix}"

        if prior_context:
            chunk_hint = (
                owner_hint
                + "\n\n**הקשר מהחלק הקודם של ההקלטה:** "
                "להלן השורות האחרונות שתומללו לפני החלק הנוכחי. "
                "ההקלטה נמשכת ישירות מכאן — שמור על **אותם תיוגי דוברים** בדיוק:\n"
                f"```\n{prior_context}\n```"
            )
        else:
            chunk_hint = owner_hint

        text = _upload_wait_transcribe_chunk(
            client, chunk_path, model_chain, chunk_hint, label, slack_token, thread_ts,
        )
        results[str(i)] = text
        _save_chunk(i, text)
        prior_context = _tail_lines(text)

    # All chunks done — clean up chunk cache
    if state_path and file_id:
        s = load_state(state_path)
        s.get("chunk_cache", {}).pop(file_id, None)
        save_state(state_path, s)

    return [results[str(i)] for i in range(n)]


def transcribe_audio(
    file_path: Path,
    api_key: str,
    model: str,
    slack_token: str | None = None,
    thread_ts: str | None = None,
    owner: str | None = None,
    state_path: "Path | None" = None,
    file_id: str | None = None,
) -> str:
    """Transcribe an audio/video file.

    For recordings longer than CHUNK_THRESHOLD_SECONDS, the audio is split into
    ~8-minute chunks, transcribed in parallel, then a reconciliation pass unifies
    speaker labels across chunk boundaries to avoid label drift.
    """
    FALLBACK_MODELS = [model, "gemini-2.5-pro", "gemini-2.5-flash", "gemini-flash-latest"]
    seen: set = set()
    model_chain = [m for m in FALLBACK_MODELS if not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]

    client = genai.Client(api_key=api_key)

    audio_path = extract_audio(file_path)
    duration = get_duration_seconds(audio_path)

    owner_hint = ""
    if owner:
        owner_display = {"avishay": "אבישי", "ohav": "אוהב"}.get(owner.lower(), owner)
        owner_hint = (
            f"\n\n**פרטי ההקלטה:**\n"
            f"- שם קובץ המקור: `{file_path.name}` — השתמש בו כרמז לזיהוי שמות משתתפים נוספים.\n"
            f"- **{owner_display} הוא/היא בוודאות אחד/ת המשתתפים בשיחה זו** — תייג אותו/ה בשמו/ה.\n"
            f"- שאר המשתתפים: זהה לפי שם שנאמר בהקלטה או לפי שם הקובץ בלבד. "
            f"אל תנחש ואל תניח זהויות על סמך ידע קודם."
        )

    use_chunks = duration is not None and duration > CHUNK_THRESHOLD_SECONDS
    if use_chunks:
        chunks = split_audio_into_chunks(audio_path, CHUNK_DURATION_SECONDS)
        n = len(chunks)
        slack_notify(
            f"⚙️ Long recording ({format_duration(duration)}) — splitting into {n} chunks for transcription.",
            slack_token, thread_ts=thread_ts,
        )
        parts = _transcribe_chunks_sequential(
            client, chunks, model_chain, owner_hint, "", slack_token, thread_ts,
            state_path=state_path, file_id=file_id,
        )
        return "\n\n".join(parts)
    else:
        uploaded = client.files.upload(file=audio_path, config={"mime_type": "audio/mpeg"})
        _wait_for_active(client, uploaded)
        try:
            return _transcribe_single_file(
                client, uploaded, model_chain, owner_hint, "full recording", slack_token, thread_ts
            )
        except _MaxTokensError:
            # Gemini hit its output limit even on a "short" recording — fall back to chunking.
            slack_notify(
                f"⚠️ MAX_TOKENS on full recording ({format_duration(duration or 0)}) — "
                f"switching to chunked transcription automatically...",
                slack_token, thread_ts=thread_ts,
            )
            chunks = split_audio_into_chunks(audio_path, CHUNK_DURATION_SECONDS)
            n = len(chunks)
            slack_notify(
                f"⚙️ Re-splitting into {n} chunks for transcription.",
                slack_token, thread_ts=thread_ts,
            )
            parts = _transcribe_chunks_sequential(
                client, chunks, model_chain, owner_hint, " (rechunked)", slack_token, thread_ts,
                state_path=state_path, file_id=file_id,
            )
            return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not acquire_lock():
        print("Another transcriber instance is running. Exiting.")
        return

    config = load_config()
    folder_ids: dict = config["drive_folder_ids"]
    model: str = config.get("model", "gemini-2.5-pro")

    api_key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY env var not set")
    slack_token = os.environ.get("SLACK_BOT_TOKEN")

    state_path = SCRIPT_DIR / ".transcriber-state.json"
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

            transcript = transcribe_audio(
                local_path, api_key, model, slack_token, thread_ts=thread_ts,
                owner=rec.get("owner"), state_path=state_path, file_id=rec["id"],
            )
            local_path.unlink(missing_ok=True)

            meeting_id = meeting_id_for(rec)
            supabase_store.upsert_meeting({
                "id": meeting_id,
                "date": meeting_id[:10],
                "owner": rec.get("owner"),
                "language": "he",
                "source": infer_source(rec["name"]),
                "duration_seconds": raw_secs,
                "transcript_md": transcript,
            })
            print(f"  Stored meeting {meeting_id} in Supabase")

            state["processed"].append(rec["id"])
            save_state(state_path, state)

            if thread_ts:
                slack_react("white_check_mark", thread_ts, slack_token)
            slack_notify(
                f"✅ Done: `{meeting_id}` _{duration_str}_",
                slack_token, thread_ts=thread_ts,
            )
            new_transcripts.append((meeting_id, rec.get("owner")))
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

    # Print new meeting ids for the agent to pick up and process
    if new_transcripts:
        print("\nNEW_TRANSCRIPTS:")
        for meeting_id, owner in new_transcripts:
            owner_hint = f" (recorded from {owner}'s Drive)" if owner else ""
            print(f"  {meeting_id}{owner_hint}")
    print("\nDone.")


if __name__ == "__main__":
    main()
