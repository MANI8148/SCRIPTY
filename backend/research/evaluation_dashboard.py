from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


class EvaluationDashboard:
    def build(self, reports: list[Any], output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for index, report in enumerate(reports, 1):
            metrics = getattr(report, "metrics", report)
            rows.extend(
                f"<tr><td>{index}</td><td>{html.escape(str(key))}</td><td>{float(value):.4f}</td></tr>"
                for key, value in sorted(metrics.items())
                if isinstance(value, (int, float))
            )
        payload = [getattr(report, "metrics", report) for report in reports]
        content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SCRIPTY Evaluation Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #172026; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d0d7de; padding: 8px; text-align: left; }}
    th {{ background: #f6f8fa; }}
    pre {{ background: #f6f8fa; padding: 12px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>SCRIPTY Evaluation Dashboard</h1>
  <table>
    <thead><tr><th>Run</th><th>Metric</th><th>Value</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>Raw Metrics</h2>
  <pre>{html.escape(json.dumps(payload, indent=2, sort_keys=True))}</pre>
</body>
</html>
"""
        target.write_text(content, encoding="utf-8")
        return target
