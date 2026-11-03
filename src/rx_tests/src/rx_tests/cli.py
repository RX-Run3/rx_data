'''
Entry point for testing CLI utilities
'''

import typer
import tempfile
import subprocess

from pathlib        import Path
from ihep_utilities import JobSubmitter
from rx_tests       import TestConfig
from rx_tests       import TestJobs
from rx_tests       import ReportBuilder
from dmu            import LogStore

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_tests:cli')
# ----------------------
@app.command()
def show_report(
    browser: str= typer.Option('firefox', '--browser', '-b'),
    path : Path = typer.Option(..., '--path', '-p')) -> None:
    '''
    Picks path to XML files, merges them, converts them to HTML
    and shows report in browser
    '''
    xml_files = list(path.glob('*.xml'))
    if not xml_files:
        typer.echo(f"No XML files found in {path}")
        raise typer.Exit(1)

    merged = Path('/tmp/merged.xml')
    report = Path('/tmp/report.html')

    subprocess.run(['junitparser', 'merge', *xml_files, str(merged)], check=True)
    subprocess.run(['junit2html', str(merged), str(report)], check=True)
    subprocess.run([browser, str(report)], check=True)
# ----------------------
@app.command()
def test_all(
    project : str | None = typer.Option(None, '--project', '-p'),
    dry_run : bool       = typer.Option(False, '--dry_run', '-d')) -> None:
    '''
    Runs all tests as configured in rx_tests_data/config.yaml
    '''
    cfg = TestConfig.from_package(
        file_path = 'config.yaml',
        package   = 'rx_tests_data')

    if project:
        cfg = cfg.filter(project = project)

    tjb = TestJobs(cfg = cfg)
    jobs= tjb.get_jobs()

    sbt = JobSubmitter(
        jobs        = jobs,
        environment = 'rx_run3')
    sbt.run(skip_submit=dry_run)
# ----------------------
@app.command()
def build_report(
    path    : Path = typer.Option(..., '--path'   , '-p'),
    browser : str  = typer.Option(..., '--browser', '-b')) -> None:
    '''
    Runs all tests as configured in rx_tests_data/config.yaml
    '''
    if not path.exists():
        raise ValueError(f'Path not found: {path}')

    with tempfile.NamedTemporaryFile(mode = 'w+t', delete=False) as temp_file:
        json_path = Path(temp_file.name)
        code_path = str(path)

        log.info('Running type analysis')
        result = subprocess.run(
            ['pyright', '--project', code_path, '--outputjson'],
            capture_output = True,
            text           = True,
            check          = False)

        log.info(f'Saving to: {json_path}')
        json_path.write_text(result.stdout)

    log.info('Building HTML report')
    bdr = ReportBuilder(json_path = json_path)
    html_path = bdr.run()

    log.info(f'Opening {html_path} with {browser}')
    subprocess.run([browser, html_path], check = True)
# ----------------------
if __name__ == '__main__':
    app()
