'''
Entry point for CLI utilities of DMU project
'''
import xml.etree.ElementTree as ET
import typer
from pathlib import Path
from dmu     import LogStore

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('dmu:cli')
# ----------------------
@app.command()
def check_jobs_status(
        xml_dir : Path = typer.Option(..., '--xml_dir', '-d')):
    '''
    This function will check the status of the tests produced by pytest
    when used with --junitxml

    Parameters
    ----------------
    xml_dir: Path to directory with XML files with report from pytest
    '''
    if not xml_dir.exists():
        log.error(f'Cannot find: {xml_dir}')
        raise typer.Exit(code=2)

    freport        = 'report.txt'
    total_tests    = 0
    total_errors   = 0
    total_failures = 0
    paths          = list(xml_dir.glob(pattern='group_*.xml'))
    if not paths:
        log.warning(f'No XML files with status found in: {xml_dir}')
        raise typer.Exit(code=2)

    for file_path in sorted(paths):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception:
            log.warning(f'Cannot parse {file_path}')
            continue

        for suite in root.iter('testsuite'):
            total_tests    += int(suite.get('tests'   , 0))
            total_errors   += int(suite.get('errors'  , 0))
            total_failures += int(suite.get('failures', 0))

    log.info(f'{"Failures:":<20}{total_failures:<20}')
    log.info(f'{"Errors:  ":<20}{total_errors:<20}')
    log.info(f'{"Total:   ":<20}{total_tests:<20}')

    report = f'Tests: {total_tests}, Failures: {total_failures}, Errors: {total_errors}'

    log.info(f'Saving tests report to: {freport}')
    with open(freport, 'w') as file_path:
        file_path.write(report + '\n')

    if total_failures > 0 or total_errors > 0:
        log.warning('At least one test failed')
        raise typer.Exit(code=1)
    else:
        log.info('All tests passed')
# ----------------------
@app.command()
def _dummy():
    pass
# ----------------------
if __name__ == '__main__':
    app()
