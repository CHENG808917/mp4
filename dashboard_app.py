from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from models import Job


ROOT_DIR = Path(__file__).resolve().parent
JOBS_DIR = ROOT_DIR / "03_jobs"
DEADLETTER_DIR = ROOT_DIR / "99_deadletter"


def load_jobs() -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for path in list(JOBS_DIR.glob("*/*.json")) + list(DEADLETTER_DIR.glob("*/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            job = Job.model_validate(data)
            jobs.append({"path": path, "job": job})
        except Exception:
            continue
    return jobs


def status_counts(jobs: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "queued": 0,
        "subtitling": 0,
        "ready_to_upload": 0,
        "uploaded": 0,
        "failed": 0,
    }
    for item in jobs:
        counts[item["job"].status] += 1
    return counts


def retry_job(item: Dict[str, Any]) -> None:
    job: Job = item["job"]
    job.status = "queued"
    job.error_reason = None
    job.updated_at = datetime.now(timezone.utc)
    target_dir = JOBS_DIR / job.account_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / item["path"].name
    target_path.write_text(
        json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if item["path"].resolve() != target_path.resolve():
        item["path"].unlink(missing_ok=True)


def main() -> None:
    st.set_page_config(page_title="字幕機看板", layout="wide")
    st.title("字幕機 / 工單看板")

    jobs = load_jobs()
    account_ids = sorted({item["job"].account_id for item in jobs})
    account_filter = st.sidebar.selectbox(
        "Account ID",
        ["全部"] + account_ids,
        index=0,
    )

    if account_filter != "全部":
        jobs = [item for item in jobs if item["job"].account_id == account_filter]

    counts = status_counts(jobs)
    cols = st.columns(5)
    cols[0].metric("queued", counts["queued"])
    cols[1].metric("subtitling", counts["subtitling"])
    cols[2].metric("ready", counts["ready_to_upload"])
    cols[3].metric("uploaded", counts["uploaded"])
    cols[4].metric("failed", counts["failed"])

    st.subheader("工單列表")
    table_rows = []
    for item in jobs:
        job = item["job"]
        table_rows.append(
            {
                "job_id": job.job_id,
                "product_id": job.product_id,
                "video_filename": job.video_filename,
                "status": job.status,
                "updated_at": job.updated_at.isoformat(),
                "error_reason": job.error_reason or "",
            }
        )
    st.dataframe(table_rows, use_container_width=True)

    st.subheader("失敗工單重試")
    failed_jobs = [item for item in jobs if item["job"].status == "failed"]
    for item in failed_jobs:
        job = item["job"]
        cols = st.columns([3, 2, 2, 1])
        cols[0].write(f"{job.job_id} / {job.video_filename}")
        cols[1].write(job.error_reason or "")
        cols[2].write(item["path"].as_posix())
        if cols[3].button("重試", key=f"retry_{job.job_id}"):
            retry_job(item)
            st.experimental_rerun()

    st.subheader("資料夾路徑")
    st.code(str((ROOT_DIR / "01_raw").resolve()), language="text")
    st.code(str((ROOT_DIR / "02_subbed").resolve()), language="text")
    st.code(str((ROOT_DIR / "03_jobs").resolve()), language="text")
    st.code(str((ROOT_DIR / "99_deadletter").resolve()), language="text")


if __name__ == "__main__":
    main()
