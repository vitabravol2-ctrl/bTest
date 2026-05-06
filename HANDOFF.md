# bTest HANDOFF

## Version
v0.4.3

## Что добавлено
- Добавлен offline-анализатор сессий `SessionAnalyzer` в `app/session_analyzer.py`:
  - `load(path)` для загрузки JSONL-сессии
  - `analyze()` для подсчёта:
    - total_events / detected_count / max_score / avg_score
    - profile_counts
    - phase_counts
    - reason_code_counts
    - fail_counts по debug-флагам (`drop_ok`, `bounce_ok`, `speed_ok`, `reclaim_ok`, `hold_ok`, `slow_trend_ok`)
    - near signals (`score>=50`, `detected=false`) с распределением blocker
    - top-20 near-signal событий
    - threshold hints (max/p95 для drop/bounce/speed и этапные проходы)
  - `export_report(path)` для сохранения текстового отчёта
- Добавлен CLI-инструмент `tools/analyze_session.py`:
  - `python tools/analyze_session.py data/sessions/session_xxx.jsonl`
  - печатает отчёт в консоль
  - сохраняет `session_xxx_report.txt` рядом с JSONL
- GUI обновлён (`app/gui/main_window.py`):
  - добавлена кнопка **ANALYZE SESSION**
  - выбор JSONL-файла через диалог
  - запуск `SessionAnalyzer`
  - сохранение отчёта `*_report.txt`
  - логирование summary: `total_events`, `max_score`, `detected_count`, `top_blocker`, `report path`
- Добавлены тесты `tests/test_session_analyzer.py`:
  - empty file
  - simple no-signal session
  - profile counts
  - fail counts
  - report export creates file

## Known limitations
- Анализ выполняется только по структуре записанных JSONL событий; если в событии отсутствуют некоторые поля debug/reason_codes, статистика строится по доступным данным.
- p95 рассчитывается дискретно по отсортированному списку без интерполяции.
- Отчёт текстовый (`.txt`) без интерактивных графиков.

## Next
v0.4.4 Replay Timeline GUI / Calibration presets
