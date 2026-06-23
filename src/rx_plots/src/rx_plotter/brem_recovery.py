'''
Module with BremRecovery class
'''
import re
import pandas            as pnd
import matplotlib.pyplot as plt

from dmu.generic import utilities as gut
from pathlib     import Path
from typing      import Final
from dmu         import LogStore

log=LogStore.add_logger('rx_plotter:brem_recovery')

_BLOCK_BREM_RGX : Final[str] = r'(\d)_(\d)'
_RESO_WC        : Final[str] = '**/fwhm_bmass_Corrected.json'
# ----------------------
class BremRecovery:
    '''
    Class holding functions needed to make diagnostic plots
    associated to brem recovery
    '''
    # ----------------------
    def _get_brem_block(self, path : Path) -> tuple[int,int]:
        '''
        Parameters
        -------------
        path: Path to JSON file

        Returns
        -------------
        Tuple with brem and block associated
        '''
        match = re.search(_BLOCK_BREM_RGX, str(path))
        if not match:
            raise ValueError(f'Could not find {_BLOCK_BREM_RGX} in {path}')

        brem  = match.group(1)
        block = match.group(2)

        return int(brem), int(block)
    # ----------------------
    def _add_row(
        self, 
        kind : str,
        df   : pnd.DataFrame, 
        path : Path) -> None:
        '''
        Parameters
        --------------
        df  : DataFrame to which to add row
        path: Path to JSON file with values
        kind: Either corrected or not, neededin dataframe
        '''
        brem, block = self._get_brem_block(path = path)
        data        = gut.load_json(path = path)
        row         = {
            'kind' : kind, 
            'brem' : brem, 
            'block': block,
            'fwhm' : data['fwhm'],
        }

        df.loc[len(df)] = row
    # ----------------------
    def resolution(self, path : Path) -> None:
        '''
        Parameters
        ---------------
        path: Path to root directory containing all JSON FILES
              with resolution information
        '''
        paths = list(path.rglob(_RESO_WC))
        if not paths:
            raise ValueError(f'No paths found in {path} with wildcard {_RESO_WC}')

        npath = len(paths)
        log.info(f'Found {npath} paths')

        df = pnd.DataFrame(columns=['kind', 'brem', 'block', 'fwhm'])
        for corr_path in paths:
            self._add_row(df = df, path = corr_path, kind = 'Corrected')

            str_path = str(corr_path)
            org_path = str_path.replace('Corrected', 'Original')
            path     = Path(org_path)

            self._add_row(df = df, path = path, kind = 'Original')

        for brem, df_brem in df.groupby('brem'):
            ax = None
            for kind, df_kind in df_brem.groupby('kind'):
                df_sort = df_kind.sort_values(by = 'block')
                ax = df_sort.plot(
                    x         ='block', 
                    y         ='fwhm', 
                    label     = kind, 
                    marker    = 'o',
                    linestyle = 'none',
                    ax        = ax)

            plt.title(rf'${brem}\gamma$')
            plt.ylim(bottom = 0, top = 800)
            plt.ylabel('FWHM [MeV]')
            plt.grid()
            plt.show()
# ----------------------
