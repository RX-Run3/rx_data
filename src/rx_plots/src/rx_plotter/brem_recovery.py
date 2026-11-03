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

_BLOCK_BREM_RGX : Final[str] = r'(\d|all)_(\d)'
_RESO_WC        : Final[str] = '**/fwhm_bmass_Corrected.json'
# ----------------------
class BremRecovery:
    '''
    Class holding functions needed to make diagnostic plots
    associated to brem recovery
    '''
    # ----------------------
    def _get_brem_block_mva(self, path : Path) -> tuple[str,int, str]:
        '''
        Parameters
        -------------
        path: Path to JSON file

        Returns
        -------------
        Tuple with brem, block and mva flag associated
        '''
        match = re.search(_BLOCK_BREM_RGX, str(path))
        if not match:
            raise ValueError(f'Could not find {_BLOCK_BREM_RGX} in {path}')

        brem  = match.group(1)
        block = match.group(2)

        path_str = str(path)
        if   'with_mva' in path_str:
            mva = 'with_mva'
        elif 'drop_mva' in path_str:
            mva = 'drop_mva'
        else:
            raise ValueError(f'Cannot find mva string in: {path}')

        return brem, int(block), mva
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
        brem, block, mva = self._get_brem_block_mva(path = path)
        data             = gut.load_json(path = path)
        row              = {
            'kind' : kind,
            'brem' : brem,
            'block': block,
            'mva'  : mva,
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

        df = pnd.DataFrame(columns=['kind', 'brem', 'block', 'fwhm', 'mva'])
        for corr_path in paths:
            self._add_row(df = df, path = corr_path, kind = 'Corrected')

            str_path = str(corr_path)
            org_path = str_path.replace('Corrected', 'Original')
            path_org = Path(org_path)

            self._add_row(df = df, path = path_org, kind = 'Original')

        for brem, df_brem in df.groupby('brem'):
            brem_str = f'{int(brem):03d}' if brem.isnumeric() else brem # type: ignore

            for mva, df_mva in df_brem.groupby('mva'):
                ax = None
                for kind, df_kind in df_mva.groupby('kind'):
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

                img_path = path / f'{mva}_brem_{brem_str}.png'
                log.info(f'Saving to: {img_path}')
                plt.savefig(img_path)
                plt.close()
# ----------------------
