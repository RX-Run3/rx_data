'''
Convert pyright --outputjson report to a self-contained HTML file.
'''

import tempfile
import json

from collections         import defaultdict
from string              import Template
from datetime            import datetime
from pathlib             import Path
from importlib.resources import files, as_file

# ------------------
class ReportBuilder:
    '''
    Class meant to build HTML report from
    JSON file produced by pyright
    '''
    # ------------------
    def __init__(self, json_path : Path):
        '''
        Parameters
        -------------
        json_path: Path to report made by pyright
        '''
        self._json_path = json_path
    # ------------------
    def _severity_badge(self, severity: str) -> str:
        colors = {"error": "#e05252", "warning": "#e09a52", "information": "#5284e0"}
        color  = colors.get(severity, "#888")
        badge  = f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:bold">{severity.upper()}</span>'

        return badge
    # ----------------------------------
    def _get_template(self) -> str:
        with as_file(files('rx_tests_data')) as path:
            path = path / 'pyright_template.html'
            text = path.read_text()

        return text
    # ------------------
    def _build_html(self, data: dict) -> str:
        '''
        Parameters
        ---------------
        data: Data stored in JSON file
        '''
        cnt : dict[str,str | int] = dict()

        diagnostics           = data.get("generalDiagnostics", [])
        summary               = data.get("summary", {})
        cnt['version']        = data.get("version", "unknown")
        ts                    = int(data.get("time", 0)) / 1000
        cnt['run_time']       = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "unknown"
        cnt['error_count']    = sum(1 for d in diagnostics if d.get("severity") == "error")
        cnt['warning_count']  = sum(1 for d in diagnostics if d.get("severity") == "warning")
        cnt['info_count']     = sum(1 for d in diagnostics if d.get("severity") == "information")
        cnt['files_analyzed'] = summary.get("filesAnalyzed", "N/A")

        by_file = defaultdict(list)
        for d in diagnostics:
            by_file[d.get("file", "unknown")].append(d)

        rows = ""
        files_with_issues = 0
        for file_path, issues in sorted(by_file.items()):
            if issues:
                files_with_issues += 1

            short_path    = file_path
            file_errors   = sum(1 for i in issues if i.get("severity") == "error")
            file_warnings = sum(1 for i in issues if i.get("severity") == "warning")
            badge_summary = ""

            if file_errors:
                badge_summary += f'<span style="color:#e05252;font-weight:bold">{file_errors}     error{"s" if file_errors   != 1 else ""}</span> '

            if file_warnings:
                badge_summary += f'<span style="color:#e09a52;font-weight:bold">{file_warnings} warning{"s" if file_warnings != 1 else ""}</span>'

            rows += f"""
            <tr class="file-row" onclick="toggleFile(this)">
                <td colspan="4">
                    <span style="font-family:monospace;font-size:0.9em">{short_path}</span>
                    &nbsp;&nbsp;{badge_summary}
                    <span class="arrow">▶</span>
                </td>
            </tr>"""

            for issue in issues:
                sev   = issue.get("severity", "")
                msg   = issue.get("message", "").replace("\n", "<br>")
                rule  = issue.get("rule", "")
                start = issue.get("range", {}).get("start", {})
                line  = start.get("line", 0) + 1
                char  = start.get("character", 0) + 1
                rows += f"""
            <tr class="issue-row hidden">
                <td style="padding-left:2em;font-family:monospace;color:#888;white-space:nowrap">L{line}:{char}</td>
                <td>{self._severity_badge(sev)}</td>
                <td>{msg}</td>
                <td style="font-family:monospace;font-size:0.8em;color:#888">{rule}</td>
            </tr>"""

        cnt['rows']              = rows
        cnt['files_with_issues'] = files_with_issues
        cnt['status_color']      = "#e05252" if cnt['error_count'] else "#52a852"
        cnt['status_text' ]      = "FAILED"  if cnt['error_count'] else "PASSED"
        template                 = self._get_template()

        return Template(template).substitute(cnt)
    # ------------------
    def run(self) -> Path:
        string = self._json_path.read_text()
        data   = json.loads(string)

        text   = self._build_html(data = data)
        with tempfile.NamedTemporaryFile(mode = 'w+t', delete=False) as temp_file:
            temp_file.write(text)

        return Path(temp_file.name)
# ----------------------------------
