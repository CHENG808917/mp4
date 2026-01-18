from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from faster_whisper import WhisperModel

from models import Job, JobOutputs


ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / "01_raw"
SUBBED_DIR = ROOT_DIR / "02_subbed"
JOBS_DIR = ROOT_DIR / "03_jobs"
LOGS_DIR = ROOT_DIR / "98_logs"
DEADLETTER_DIR = ROOT_DIR / "99_deadletter"

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "5"))
SUB_FONT = os.getenv("SUB_FONT", "Microsoft JhengHei")
SUB_FONTSIZE = os.getenv("SUB_FONTSIZE", "36")


def ensure_directories() -> None:
    for path in [RAW_DIR, SUBBED_DIR, JOBS_DIR, LOGS_DIR, DEADLETTER_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iter_job_files() -> Iterable[Path]:
    return JOBS_DIR.glob("*/*.json")


def read_job(job_path: Path) -> Job:
    data = json.loads(job_path.read_text(encoding="utf-8"))
    return Job.model_validate(data)


def write_job(job_path: Path, job: Job) -> None:
    job_path.write_text(
        json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def log_message(message: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"worker_{datetime.now(timezone.utc).date().isoformat()}.log"
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def acquire_lock(job_path: Path) -> Optional[Path]:
    lock_path = job_path.with_suffix(job_path.suffix + ".lock")
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    else:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(now_iso())
        return lock_path


def release_lock(lock_path: Optional[Path]) -> None:
    if lock_path and lock_path.exists():
        lock_path.unlink()


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def extract_audio(video_path: Path, wav_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        str(wav_path),
    ]
    run_command(cmd)


def transcribe_audio(model: WhisperModel, wav_path: Path, srt_path: Path) -> None:
    segments, _info = model.transcribe(
        str(wav_path),
        beam_size=5,
        vad_filter=True,
    )
    lines = []
    for idx, segment in enumerate(segments, start=1):
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        text = segment.text.strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    srt_path.write_text("\n".join(lines), encoding="utf-8")


def format_timestamp(seconds: float) -> str:
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def escape_subtitle_path(path: Path) -> str:
    value = str(path)
    value = value.replace("\\", "/")
    value = value.replace(":", "\\:")
    value = value.replace("'", "\\'")
    return value


def burn_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> None:
    escaped_path = escape_subtitle_path(srt_path)
    style = f"FontName={SUB_FONT},FontSize={SUB_FONTSIZE},Outline=1,Shadow=0"
    vf_filter = f"subtitles='{escaped_path}':force_style='{style}'"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf_filter,
        "-c:a",
        "copy",
        str(output_path),
    ]
    run_command(cmd)


def move_to_deadletter(job_path: Path, job: Job, reason: str) -> None:
    job.status = "failed"
    job.error_reason = reason
    job.updated_at = datetime.now(timezone.utc)
    deadletter_dir = DEADLETTER_DIR / job.account_id
    deadletter_dir.mkdir(parents=True, exist_ok=True)
    destination = deadletter_dir / job_path.name
    write_job(job_path, job)
    shutil.move(str(job_path), str(destination))
    log_message(f"Job {job.job_id} failed: {reason}")


def process_job(job_path: Path, model: WhisperModel) -> None:
    job = read_job(job_path)
    if job.status != "queued":
        return

    job.status = "subtitling"
    job.updated_at = datetime.now(timezone.utc)
    write_job(job_path, job)

    raw_video = RAW_DIR / job.account_id / job.video_filename
    if not raw_video.exists():
        raise FileNotFoundError(f"Missing input video: {raw_video}")

    output_dir = SUBBED_DIR / job.account_id
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / f"{job.video_filename}.srt"
    output_video = output_dir / job.video_filename
    temp_wav = output_dir / f"{Path(job.video_filename).stem}_tmp.wav"

    try:
        extract_audio(raw_video, temp_wav)
        transcribe_audio(model, temp_wav, srt_path)
        burn_subtitles(raw_video, srt_path, output_video)
    finally:
        if temp_wav.exists():
            temp_wav.unlink()

    job.status = "ready_to_upload"
    job.outputs = JobOutputs(
        mp4=str(output_video.relative_to(ROOT_DIR)).replace("\\", "/"),
        srt=str(srt_path.relative_to(ROOT_DIR)).replace("\\", "/"),
    )
    job.error_reason = None
    job.updated_at = datetime.now(timezone.utc)
    write_job(job_path, job)


def main() -> None:
    ensure_directories()
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    log_message(f"subtitle_worker started with model={WHISPER_MODEL}")
    while True:
        processed = False
        for job_path in iter_job_files():
            lock_path = acquire_lock(job_path)
            if not lock_path:
                continue
            try:
                job = read_job(job_path)
                if job.status != "queued":
                    continue
                process_job(job_path, model)
                processed = True
                break
            except Exception as exc:  # noqa: BLE001 - log and move to deadletter
                try:
                    job = read_job(job_path)
                except Exception:
                    job = Job(
                        job_id=job_path.stem,
                        account_id="unknown",
                        product_id="",
                        video_filename="",
                        exact_search_text="",
                        shop_name="",
                        affiliate_link="",
                        status="failed",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        error_reason=str(exc),
                        outputs=None,
                    )
                move_to_deadletter(job_path, job, str(exc))
            finally:
                release_lock(lock_path)
        if not processed:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
