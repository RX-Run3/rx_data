'''
Module containing ScalesConf class
'''
import os

from typing      import Literal
from rx_common   import MVAWp
from pydantic    import BaseModel, RootModel
from pathlib     import Path
from dmu         import LogStore
from rx_common   import Trigger

log=LogStore.add_logger('fitter:scales_conf')
#-------------------------------------
class Ranges(RootModel[dict[str,tuple[float,float]]]):
    '''
    Class representing set of ranges to plot variables
    '''
#-------------------------------------
class ScalesConf(BaseModel, frozen = True):
    '''
    Class used to store configuration
    needed to extract mass scales and resolutions
    '''
    pdg_mass: float
    ee      : Ranges
    mm      : Ranges

    name    : str
    '''
    Name of fit group, e.g. reso_no_dtf
    '''
    kind    : Literal['q2', 'B']
    comb    : MVAWp
    prec    : MVAWp
    trig    : Trigger
    year    : str
    # ------------------------------
    @property
    def out_dir(self) -> Path:
        '''
        Directory where results of fits are located
        '''
        ana_dir = Path(os.environ['ANADIR'])
        name    = f'{self.comb.name}_{self.prec.name}'
        proj    = self.trig.project
        chan    = self.trig.channel

        match self.kind:
            case 'q2':
                out_dir = ana_dir / f'q2/fits/{name}/plots/{proj}_{chan}'
            case 'B':
                out_dir = ana_dir / f'fits/data/{self.name}/{name}/{proj}_{chan}/plots'

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
        proj    = self.trig.project
        chan    = self.trig.channel

        match self.kind:
            case 'q2':
                return ana_dir / f'q2/fits/{name}'
            case 'B':
                return ana_dir / f'fits/data/reso_no_dtf/{name}/{proj}_{chan}'
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
        if   self.trig.is_muon:
            data = self.mm
        elif self.trig.is_electron:
            data = self.ee
        else:
            raise ValueError(f'Trigger {self.trig} is neither electron or muon')

        if var not in data.root:
            for value in data:
                log.error(value)
            raise ValueError(f'Invalid variable: {var}')

        low, high = data.root[var]

        return low, high
#-------------------------------------
