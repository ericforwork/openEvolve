# 終端／日誌備份 — 2026-06-12 約 15:40（run：`20260612_154029`）

本資料夾為同一次操作之**三份來源**，方便對照；**內容不重複合併**，請分開開啟。

| 檔案 | 說明 |
|------|------|
| **`cursor_terminal_14_snapshot.txt`** | Cursor IDE 寫入的 **`terminals/14.txt`** 原樣複製（緩衝區內容，**可能**不含更早捲動）。 |
| **`powershell_tee_console.log`** | 你執行 `make evolve ... \| Tee-Object` 時寫入的 **`docs/evolve_console_20260612_154029.log`** 之副本（**較接近完整終端 stdout/stderr**）。 |
| **`openevolve_file_logger.log`** | OpenEvolve 寫入檔案的 logger：`config/openevolve_output/20260612_154029/logs/openevolve_20260612_154034.log` 之副本。 |

**輸出目錄**：`config/openevolve_output/20260612_154029/`

---

## 之後若要自己備份

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$dir = "docs\terminal_archive_$ts"
New-Item -ItemType Directory -Path $dir -Force
$env:PYTHONUTF8 = 1
make evolve ITERS=1 TASKS=1 2>&1 | Tee-Object -FilePath "$dir\console.log"
# 跑完後再手動複製：
# - .cursor\...\terminals\<id>.txt → $dir\cursor_snapshot.txt
# - config\openevolve_output\<run>\logs\openevolve_*.log → $dir\
```
