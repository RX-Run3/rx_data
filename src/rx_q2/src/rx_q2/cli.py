'''
This script is meant to be the entry point for all the functionalities
provided by this project
'''

import typer
from dmu     import LogStore
from rx_q2   import ScaleCombiner

app = typer.Typer(
    help            = __doc__,
    context_settings= {"help_option_names": ["-h", "--help"]})
log = LogStore.add_logger('rx_q2:cli')
# ----------------------
@app.command()
def combine_scales(version : str) -> None:
    '''
    version: Version of fits
    '''
    log.info(f'Combining scales for version: {version}')
    cmb = ScaleCombiner(version=version)
    cmb.combine(name = 'parameters_ee.json', measurements=['rk_ee', 'rkst_ee'])
    cmb.combine(name = 'parameters_mm.json', measurements=['rk_mm', 'rkst_mm'])
# ----------------------
if __name__ == '__main__':
    app()
