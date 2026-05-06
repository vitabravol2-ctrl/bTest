from __future__ import annotations

import sys
from pathlib import Path

from app.session_analyzer import SessionAnalyzer


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/analyze_session.py data/sessions/session_xxx.jsonl")
        return 1

    session_path = Path(sys.argv[1])
    analyzer = SessionAnalyzer()
    analyzer.load(session_path)
    analyzer.analyze()

    report_path = session_path.with_name(f"{session_path.stem}_report.txt")
    analyzer.export_report(report_path)

    print(analyzer.report_text)
    print(f"Report saved: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
