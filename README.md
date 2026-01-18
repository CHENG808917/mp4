# mp4 字幕機（自動模式）＋ Streamlit 看板

此專案提供兩個主要元件：
- **subtitle_worker.py**：長時間執行的字幕機（自動模式主力）。
- **dashboard_app.py**：Streamlit 看板（員工只需監看）。

## 1) 安裝與環境（Windows 友善）

### 建立 venv
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 安裝 requirements
```bash
pip install -r requirements.txt
```

### 檢查 ffmpeg 是否可用
```bash
ffmpeg -version
```

## 2) 資料夾結構

執行 worker 前請確認下列資料夾（缺少會自動建立）：
```
01_raw/{account_id}/
02_subbed/{account_id}/
03_jobs/{account_id}/
98_logs/
99_deadletter/
```

## 3) 工單格式與範例

- Schema：`docs/job_schema.json`
- 範例：`examples/jobs/sample_job_A.json`

> `video_filename` 必須是安全檔名（無路徑），對應 `01_raw/{account_id}/` 內的 mp4。

## 4) 如何放影片與工單

1. 將 mp4 放入 `01_raw/A/`（或 B/C）。
2. 將工單 JSON 放入 `03_jobs/A/`。

## 5) 啟動字幕機
```bash
python subtitle_worker.py
```

環境變數：
- `WHISPER_MODEL`：預設 `small`
- `SUB_FONT`：預設 `Microsoft JhengHei`
- `SUB_FONTSIZE`：預設 `36`
- `POLL_INTERVAL`：掃描間隔秒數，預設 `5`

## 6) 啟動看板
```bash
streamlit run dashboard_app.py
```

