'''
Module containing ScalesConf class
'''
import os

from typing     import Literal
from fitter     import MVAWp
from pydantic   import BaseModel, ConfigDict
from pathlib    import Path
from dmu        import LogStore

log=LogStore.add_logger('fitter:scales_conf')
#-------------------------------------
class ScalesConf(BaseModel):
    '''
    Class used to store configuration
    needed to extract mass scales and resolutions
    '''
    model_config = ConfigDict(frozen=True)
    jpsi_mass : float

    mm      : dict[str,list[float]]
    ee      : dict[str,list[float]]

    kind    : Literal['q2', 'B']
    comb    : MVAWp
    prec    : MVAWp
    year    : str
    proj    : str
    # ------------------------------
    @property
    def out_dir(self) -> Path:
        '''
        Directory where results of fits are located
        '''
        ana_dir = Path(os.environ['ANADIR'])
        name    = f'{self.comb.name}_{self.prec.name}'

        match self.kind:
            case 'q2':
                out_dir = ana_dir / f'q2/fits/{name}/plots/{self.proj}'
            case 'B':
                out_dir = ana_dir / f'fits/data/reso_no_dtf/{name}/{self.proj}/plots'

        out_dir.mkdir(parents=True, exist_ok=True)

        return out_dir
    # ------------------------------
    @property
    def inp_dir(self) -> Path:
        '''
        Directory where results of fits are located
        '''
        ana_dir = Path(os.environ['ANADIR'])
        name    = f'{self.comb.name}_{self.prec.name}'

        match self.kind:
            case 'q2':
                return ana_dir / f'q2/fits/{name}'
            case 'B':
                return ana_dir / f'fits/data/reso_no_dtf/{name}/{self.proj}'
    # ------------------------------
    @property
    def regex(self) -> str:
        '''
        Regular expression used to extract block and MVA WP
        '''
        match self.kind:
            case 'q2':
                return r'(\d)_(\d)_nom'
            case 'B':
                return r'(\d{3})_(\d{3})_b(\d)'
    # ------------------------------
    def get_range(self, var : str) -> tuple[float,float]:
        '''
        Parameters
        -----------------
        var: Variable name, e.g. mu, sg, dm, ss

        Returns
        -----------------
        Y axis range for plot
        '''
        if   self.proj.endswith('_mm'):
            data = self.mm
        elif self.proj.endswith('_ee'):
            data = self.ee
        else:
            raise ValueError(f'Invalid project: {self.proj}')

        if var not in data:
            for value in data:
                log.error(value)
            raise ValueError(f'Invalid variable: {var}')

        [low, high] = data[var]

        return low, high
#-------------------------------------
