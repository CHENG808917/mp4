# Project Guide (字幕機 + 看板)

This repository provides:
- **subtitle_worker.py**: an automated subtitle worker that reads jobs, transcribes via Whisper, and burns subtitles.
- **dashboard_app.py**: a Streamlit dashboard for monitoring jobs.

## How to run the worker
1. Put raw MP4 files in `01_raw/{account_id}/`.
2. Put job JSON files in `03_jobs/{account_id}/`.
3. Run:
   ```bash
   python subtitle_worker.py
   ```

## How to run the dashboard
```bash
streamlit run dashboard_app.py
```

## Job placement
- Jobs live under `03_jobs/{account_id}/`.
- Failed jobs are moved to `99_deadletter/{account_id}/`.

