'''
Module containing Conf class
'''
import os
from typing         import Self
from pathlib        import Path
from pydantic       import BaseModel, computed_field, model_validator, ConfigDict
from dmu            import LogStore
from dmu.stats      import zfit, Model, FitConf
from zfit           import Space    as zobs

log=LogStore.add_logger('rx_q2:config')
#-------------------
class Samples(BaseModel):
    '''
    Class meant to represent sample information
    '''
    rk_ee  : dict[str,str]
    rkst_ee: dict[str,str]
    rk_mm  : dict[str,str]
    rkst_mm: dict[str,str]
    #-------------------
    def __getitem__(self, name : str) -> dict[str,str]:
        if not hasattr(self, name):
            raise AttributeError(f'Samples class has no {name} attribute')

        return getattr(self, name)
#-------------------
class Input(BaseModel):
    '''
    Class meant to represent input section of config
    '''
    year      : str
    brem      : int
    block     : str
    kind      : str     # dat or sim, used to pick from Samples below
    samples   : Samples
    trigger   : dict[str,str]
    selection : dict[str,str]
    friends   : dict[str,list[str]]
#-------------------
class Plots(BaseModel):
    yrange : dict[str, list[float|None]]
    nbins  : int
    stacked: bool
    d_leg  : dict[str,str]
#-------------------
class Fitting(BaseModel):
    '''
    Class used to store fitting configuration
    '''
    ranges    : dict[str,dict[int,list[float]]]
    mass      : str
    weights   : str
    model     : list[Model]
    sim       : FitConf
    dat       : FitConf
    skip      : bool
    # ----------------------
    def __getitem__(self, kind : str) -> FitConf:
        '''
        Parameters
        -------------
        kind: I.e. sim or dat

        Returns
        -------------
        Fitting configuration
        '''
        if kind not in ['sim', 'dat']:
            raise ValueError(f'Invalid kind: {kind}')

        val = getattr(self, kind)
        if not isinstance(val, FitConf):
            raise ValueError(f'Cannot extrac fit configuration for: {kind}')

        return val
#-------------------
class Config(BaseModel):
    '''
    Class meant to hold configuration
    '''
    model_config = ConfigDict(
        arbitrary_types_allowed = True,
        frozen                  = True)

    project  : str
    logl     : int
    ana_dir  : Path
    vers     : str
    syst     : str
    input    : Input
    fitting  : Fitting
    plots    : Plots
    #-------------------
    @model_validator(mode='after')
    def _update_selection(self) -> Self:
        '''
        Updates input.selection dictionary
        '''
        log.debug('Updating selection')
        self.input.selection['block'] = self._get_block_cut()
        self.input.selection['brem' ] = self._get_brem_cut()

        return self
    #-------------------
    @computed_field
    @property
    def obs_range(self) -> tuple[float,float]:
        project     = self.project
        brem        = self.input.brem
        rng         = self.fitting.ranges[project][brem]
        [low, high] = rng

        return low, high
    # ----------------------
    def _get_brem_cut(self) -> str:
        '''
        Returns
        -------------
        E.g. nbrem == 2
        '''
        brem = self.input.brem
        if brem == -1:
            return 'nbrem == (1)'

        if brem in [0, 1, 2]:
            return f'nbrem == {brem}'

        raise ValueError(f'Invalid brem value: {brem}')
    #-------------------
    def _get_block_cut(self) -> str:
        block = self.input.block

        if block == 'all':
            return '(1)'

        if block == '12':
            return '(block == 1) || (block == 2)'

        if block == '78':
            return '(block == 7) || (block == 8)'

        return f'block == {block}'
    #-------------------
    @computed_field
    @property
    def out_dir(self) -> Path:
        ana_dir = Path(os.environ['ANADIR'])
        path_1  = f'q2/fits/{self.vers}/{self.input.kind}'
        path_2  = f'{self.project}_{self.input.year}'
        path_3  = f'{self.input.brem}_{self.input.block}_{self.syst}'

        out_dir = ana_dir / path_1 / path_2 / path_3
        out_dir.mkdir(parents=True, exist_ok=True)

        return out_dir
    #-------------------
    @computed_field
    @property
    def obs(self) -> zobs:
        '''
        Observable used in fit
        '''
        name = self.fitting.mass

        return zfit.Space(name, limits=self.obs_range)
#-------------------
