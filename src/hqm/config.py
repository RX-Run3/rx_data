import os

from dmu                 import LogStore
from dmu.stats           import Model, ZFitPlotterConf
from dmu.generic         import utilities as gut
from typing              import Final
from pathlib             import Path
from dmu.stats           import FitConf
from pydantic            import BaseModel
from rx_common           import Block, Trigger, Qsq

log = LogStore.add_logger('rx_hqm:config')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
#-------------------------------------------------------------------
class BinningConf(BaseModel, frozen = True):
    variable : str
    '''
    Name of variable to bin with
    '''
    bin      : int
    '''
    Index of bin
    '''
    cut      : str
    '''
    Expression defining cut
    '''
    # ------------------------
    @property
    def prefix(self) -> str:
        return f'{self.variable}_{self.bin}'
#-------------------------------------------------------------------
class Conf(BaseModel, frozen = True):
    '''
    Configuration controlling how transfer function is built
    '''
    bandwidth : int
    fft_npt   : int
    fits      : FitConf
    plots     : ZFitPlotterConf
    binning   : BinningConf | None
    source    : Qsq
    target    : Qsq
    models    : list[Model]
    # -----------------------------------------------
    def __str__(self):
        return f'''
        ----------
        Data
        ----------
        Source: {self.source}
        Target: {self.target}
        Models: {self.models}

        ----------
        Fits
        ----------
        {self.fits}

        ----------
        Plots
        ----------
        {self.plots}

        ----------
        Binning
        ----------
        {self.binning}
        '''
    # -----------------------------------------------
    @property
    def prefix(self) -> str:
        '''
        String meant to be used to identify PDFs, etc
        '''
        if self.binning is None:
            binning = 'unbinned'
        else:
            binning = self.binning.prefix

        return f'{self.source}_{self.target}_{binning}'
    # -----------------------------------------------
    @classmethod
    def load(
        cls, 
        name   : str,
        source : Qsq,
        target : Qsq) -> 'Conf':
        '''
        Parameters
        ---------------
        name: Name of config file used to create config
        source: Origin (muon) q2 bin 
        target: Needed (electron) q2 bin

        Returns
        ---------------
        Config object
        '''
        data     = gut.load_data(package = 'hqm_data', fpath = f'config/{name}.yaml')
        qsq_data = data['qsq']
        cfg      = dict() 

        for q2_cfg in qsq_data:
            if q2_cfg['source'] != source:
                continue

            if q2_cfg['target'] != target:
                continue

            cfg.update(q2_cfg)

        cfg['fits'     ] = data['fits'     ]
        cfg['binning'  ] = data['binning'  ]
        cfg['fft_npt'  ] = data['fft_npt'  ]
        cfg['bandwidth'] = data['bandwidth']
        cfg['plots'  ].update(data['plots'])
        if cfg is None:
            raise ValueError(f'Missing configuration for {source}/{target}')

        return cls(**cfg)
    # -----------------------------------------------
    @staticmethod
    def print_config(name) -> None:
        if not hasattr(Conf, name):
            log.error(f'Cannot find {name} in configuration')
            raise

        d_data = getattr(Conf, name)
        log.info(80 * '-')
        log.info(f'{"Setting":<30}{"Value":<50}')
        log.info(80 * '-')
        for key, val in d_data.items():
            log.info(f'{key:<30}{val:<50}')
    # -----------------------------------------------
    def make_path(
        self,
        kind    : str, 
        fname   : str,
        block   : Block, 
        trigger : Trigger) -> Path:
        '''
        Function will make a path and return it. 

        Parameters 
        -----------------
        kind   : Name of directory meant to sybolize what data will be stored there, e.g. fits, trfc
        fname  : Optional, file name, e.g. data.json
        Block  : E.g. block 1,...8 
        trigger: E.g. rk_ee_os 

        Returns
        -----------------
        Path to either file or directory
        '''
        if self.binning is None:
            binning = 'int'
        else:
            binning = f'{self.binning.variable}_{self.binning.bin}'

        dir_path = _ANADIR / f'{kind}/{binning}/{block}'
        dir_path.mkdir(parents = True, exist_ok = True)

        if fname is None:
            return dir_path

        return dir_path / fname 
#-------------------------------------------------------------------
