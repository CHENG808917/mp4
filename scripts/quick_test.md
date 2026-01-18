# Quick Test Plan

1. 建立資料夾並放入檔案：
   - `01_raw/A/` 放入 `sample_video.mp4`
   - `03_jobs/A/` 放入 `examples/jobs/sample_job_A.json`
2. 執行字幕機：
   ```bash
   python subtitle_worker.py
   ```
3. 驗證結果：
   - `02_subbed/A/` 出現 `sample_video.mp4` 與 `sample_video.mp4.srt`
   - 工單狀態變成 `ready_to_upload`，`outputs` 填入相對路徑

