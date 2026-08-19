import os
import copy

from dmu         import LogStore
from dmu.stats   import Model, ZFitPlotterConf, zfit
from dmu.generic import utilities as gut
from typing      import Final, Self
from pathlib     import Path
from dmu.stats   import FitConf
from pydantic    import BaseModel, model_validator
from rx_common   import Project, Qsq

log = LogStore.add_logger('rx_hqm:config')

#-------------------------------------------------------------------
class ObsConf(BaseModel, frozen = True):
    '''
    Class meant to configure observables needed in
    transfer function calculation
    '''
    name       : str
    mass_range : tuple[float,float]
    tran_range : tuple[float,float]
    #---------------------------------
    @property
    def fit_obs(self) -> zfit.Space:
        '''
        Observable that will be fitted for source and target datasets
        '''
        return zfit.Space(self.name, limits = self.mass_range)
    #---------------------------------
    @property
    def trn_obs(self) -> zfit.Space:
        '''
        Observable for transfer function 
        '''
        return zfit.Space(self.name, limits = self.tran_range)
#-------------------------------------------------------------------
class BinningConf(BaseModel, frozen = True):
    '''
    Config describing 
    '''
    name : str
    '''
    Label for cut used to get current bin, e.g occupacy
    '''

    bin   : int
    '''
    Index of bin, needed to pick up cut
    '''

    cuts  : list[str]
    '''
    Expression defining cut
    '''
    # ------------------------
    @property
    def cut(self) -> str:
        '''
        Cut associated to current bin
        '''
        return self.cuts[self.bin]
    # ------------------------
    @property
    def is_unbinned(self) -> bool:
        '''
        True if unbinned
        '''
        return len(self.cuts) == 1 and self.cuts[0] == 'true'
    # ------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> Self:
        ncut = len(self.cuts)
        if self.bin < 0:
            raise ValueError(f'Non-positive bin found: {self.bin}')

        if ncut == 0:
            raise ValueError('Found no cuts')

        if self.name == 'none':
            if ncut != 1:
                raise ValueError('Unbinned case requires one bin')

            [cut] = self.cuts
            if cut != 'true':
                raise ValueError(f'Unbinned case using invalid cut: {cut}')

        if ncut <= self.bin:
            raise ValueError(f'Bin index {self.bin} incompatible with number of bins {ncut}')

        return self
    # ------------------------
    @property
    def prefix(self) -> str:
        '''
        String used to identify transfer function, e.g. brem_001
        '''
        if self.is_unbinned:
            return 'unbinned'

        return f'{self.name}_{self.bin:03d}'
#-------------------------------------------------------------------
class Conf(BaseModel, frozen = True):
    '''
    Configuration controlling how transfer function is built
    '''
    observable: ObsConf
    bandwidth : int
    fft_npt   : int
    fits      : FitConf
    plots     : ZFitPlotterConf
    binning   : BinningConf
    source    : Qsq
    target    : Qsq
    models    : list[Model]
    # -----------------------------------------------
    def __str__(self):
        return f'''
        Name: {self.name}

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
    def name(self) -> str:
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
        binning: str,
        source : Qsq,
        target : Qsq) -> list['Conf']:
        '''
        Parameters
        ---------------
        binning: Name of binning, e.g. none
        source : Origin (muon) q2 bin 
        target : Needed (electron) q2 bin

        Returns
        ---------------
        Config object
        '''
        trf_data = gut.load_data(package = 'hqm_data', fpath = 'config/transfer.yaml')
        bin_data = gut.load_data(package = 'hqm_data', fpath = 'config/binning.yaml')
        qsq_data = trf_data['qsq']
        cfg      = dict() 

        for q2_cfg in qsq_data:
            if q2_cfg['source'] != source:
                continue

            if q2_cfg['target'] != target:
                continue

            cfg.update(q2_cfg)

        cfg['fits'      ] = trf_data['fits'       ]
        cfg['observable'] = trf_data['observable' ]
        cfg['binning'   ] = bin_data[binning      ]
        cfg['fft_npt'   ] = trf_data['fft_npt'    ]
        cfg['bandwidth' ] = trf_data['bandwidth'  ]

        cfg['plots'].update(trf_data['plots'])
        if cfg is None:
            raise ValueError(f'Missing configuration for {source}/{target}')

        nbin = len(bin_data[binning]['cuts'])

        confs : list[cls] = []
        for ibin in range(nbin):
            this_cfg = copy.deepcopy(cfg)
            this_cfg['binning']['bin'] = ibin

            confs.append(cls(**this_cfg))

        return confs
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
        fname   : str,
        kind    : str, 
        project : Project) -> Path:
        '''
        Function will make a path and return it. 

        Parameters 
        -----------------
        kind   : Name of directory meant to sybolize what data will be stored there, e.g. fits, trfc
        fname  : Optional, file name, e.g. data.json
        project: E.g. rk, rkst

        Returns
        -----------------
        Path to either file or directory
        '''
        if self.binning is None:
            binning = 'int'
        else:
            binning = f'{self.binning.name}_{self.binning.bin}'

        anadir = Path(os.environ['ANADIR'])
        log.error(f'Using ANADIR: {anadir}')

        dir_path = anadir / f'{kind}/{binning}/{project}'
        dir_path.mkdir(parents = True, exist_ok = True)

        if fname is None:
            return dir_path

        return dir_path / fname 
#-------------------------------------------------------------------
