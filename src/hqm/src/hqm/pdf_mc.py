'''
Module holding PdfBuilder
'''
import os
import numpy
import numpy.typing      as npt
import matplotlib.pyplot as plt

from contextlib     import AbstractContextManager
from contextlib     import ExitStack
from typing         import Final, Literal, overload
from functools      import cached_property
from pathlib        import Path
from dmu.generic    import utilities as gut
from pydantic       import BaseModel, RootModel
from rx_common      import Component, Mass, Trigger, Qsq
from dmu            import LogStore
from dmu.stats      import Fitter, Model, ModelFactory, ParameterLibrary
from dmu.stats      import FittedModel, NonParametricModel
from dmu.stats      import ZFitPlotter, ZFitPlotterConf, zfit
from hqm.data_store import DataStore
from dmu.generic    import Mode

log=LogStore.add_logger('hqm:pdf_mc')

_PDF_NAME : Final[str] = 'pdf_mc'
_MAX_SIZE : Final[int] = 50_000 # If array is larger than this, limit it to this number

# Ranges used to override parameters from ModelFactory
_RANGES : Final[list[tuple[str,str,float,float,float]]] = [
('suj', 'dl', 2.0, 0.0, 4.0),
('suj', 'gm', 0.0,-3.0, 3.0),
]

type NpFltArr = npt.NDArray[numpy.float64]
type zpdf     = zfit.pdf.BasePDF
type zdat     = zfit.data.Data
type zobs     = zfit.Space
# ----------------------------
class StatsConf(BaseModel, frozen = True):
    stats : tuple[int,int]
    models: list[Model]
    # ----------------------------
    @property
    def min_entries(self) -> int:
        '''
        Minimum number of entries for current config
        '''
        minv, _ = self.stats

        return minv
# ----------------------------
class ModelsConf(RootModel[dict[str,StatsConf]], frozen = True):
    '''
    Class meant to configue model choice
    '''
    # ----------------------------
    @property
    def min_entries(self) -> int:
        '''
        Smallest number of entries usable for model building
        '''
        entries = [ cfg.min_entries for cfg in self.root.values() ]

        return min(entries)
    # ----------------------------
    def get_model(self, nentries : int) -> list[Model] | None:
        '''
        Parameters
        ----------------
        nentries: Size of dataset

        Returns
        ----------------
        List of models whose sum is used to fit data
        or None if dataset is too small
        '''
        for stats in self.root.values():
            min_size = stats.stats[0]
            max_size = stats.stats[1]

            if min_size < nentries <= max_size:
                return stats.models

        return
# ----------------------------
class RangesConf(BaseModel, frozen = True):
    '''
    Object meant to configure how parameter and plotting ranges are set
    '''
    mu : tuple[float,float,float]
    sg : tuple[float,float,float]
    rn : tuple[float,float]
# ----------------------------
class PdfBuilderConf(BaseModel, frozen = True):
    '''
    Class meant to configure PDF building
    '''
    electron : dict[Qsq,dict[Qsq,RangesConf]]
    muon     : dict[Qsq,dict[Qsq,RangesConf]]
    out_dir  : Path
    mod_cfg  : ModelsConf
    # ----------------------------
    def __qsq_from_component(self, comp : Component) -> Qsq:
        '''
        Parameters
        -----------------
        comp: Component to be fitted

        Returns
        -----------------
        q2-bin associated to component, i.e. where this component exists
        '''
        jpsi_comp = [
            Component.bpkpjpsiee, Component.bdkstkpijpsiee,
            Component.bpkpjpsimm, Component.bdkstkpijpsimm]

        psi2_comp = [
            Component.bpkppsi2ee, Component.bdkstkpipsi2ee,
            Component.bpkppsi2mm, Component.bdkstkpipsi2mm]

        high_comp = [Component.bpkpee, Component.bdkstkpiee]

        if comp in jpsi_comp:
            return Qsq.jpsi

        if comp in psi2_comp:
            return Qsq.psi2

        if comp in high_comp:
            return Qsq.high

        raise ValueError(f'Invalid component: {comp}')
    # ----------------------------
    def read_conf(
        self,
        comp : Component,
        trig : Trigger,
        qsq  : Qsq) -> RangesConf:
        '''
        Parameters
        -------------
        comp : Component been fitted
        trig : Trigger associated to data
        qsq  : q2-bin in which component data will be fitted

        Returns
        -------------
        Configuration object storing range information
        '''
        inner_qsq = self.__qsq_from_component(comp = comp)
        data      = self.electron if trig.is_electron else self.muon

        return data[qsq][inner_qsq]
    # ----------------------------
    @property
    def out_path(self) -> Path:
        '''
        Path to directory where outputs will go
        '''
        ana_dir  = Path(os.environ['ANADIR'])
        out_path = ana_dir / self.out_dir / 'latest'

        return out_path
    # ----------------------------
    @classmethod
    def load(cls) -> 'PdfBuilderConf':
        '''
        Returns config object from YAML file
        '''
        data = gut.load_data(package = 'hqm_data', fpath = 'config/models.yaml')

        return cls(**data)
# ----------------------------
class PdfBuilder:
    '''
    Class meant to:

    - Load simulated data
    - Fit it
    - Scale PDF
    '''
    # ----------------------------
    def __init__(
        self,
        name   : str,
        comp   : Component,
        trigger: Trigger,
        qsq    : Qsq,
        label  : str = 'Unlabeled'):
        '''
        Parameters
        ------------------
        name   : Identifier for current PDF
        label  : Used in title of plots
        qsq    : q2-bin
        comp   : Describes sample used for fit
        trigger: E.g. rk_ee_os
        '''
        self.__label= label
        self.__comp = comp
        self.__trig = trigger
        self.__qsq  = qsq
        self.__cfg  = PdfBuilderConf.load()

        self.__out_path = self.__cfg.out_path / name / f'{comp}_{trigger}_{qsq}'
        self.__out_path.mkdir(parents = True, exist_ok = True)
    # ----------------------------
    def _get_val_ctx(self) -> list[AbstractContextManager[None]]:
        '''
        Returns list of context managers, each representing a parameter whose values
        should be overriden for ModelFactory
        '''
        contexts : list[AbstractContextManager[None]] = []
        for kind, name, val, low, high in _RANGES:
            ctx = ParameterLibrary.values(
                kind      = kind, 
                parameter = name, 
                val       = val,
                low       = low,
                high      = high)

            contexts.append(ctx)

        return contexts 
    # ----------------------------
    @cached_property
    def name(self) -> str:
        '''
        Identifier for current instance
        '''
        return f'{self.__comp}_{self.__trig}_{self.__qsq}'
    # ----------------------------
    @overload
    def _get_model(
        self,
        data    : zdat,
        models  : None,
        cfg_par : RangesConf) -> NonParametricModel: ...
    @overload
    def _get_model(
        self,
        data    : zdat,
        models  : list[Model],
        cfg_par : RangesConf) -> FittedModel: ...
    def _get_model(
        self,
        data    : zdat,
        models  : list[Model] | None,
        cfg_par : RangesConf) -> FittedModel | NonParametricModel:

        if models:
            mod = self.__run_parametric_fit(
                models = models,
                cfg    = cfg_par,
                data   = data)
        else:
            mod = NonParametricModel.from_data(
                name = 'Model',
                data = data)

        self._plot_fit(cfg_par = cfg_par, data = data, pdf = mod.pdf)

        return mod
    # ----------------------------
    def __run_parametric_fit(
        self,
        models : list[Model],
        cfg    : RangesConf,
        data   : zdat) -> FittedModel:
        '''
        Parameters
        --------------
        models: List of models needed for fit
        cfg   : Configuration describing ranges
        data  : Zfit data

        Returns
        --------------
        Object holding information on fit
        '''
        values = {
            'mu': cfg.mu,
            'sg': cfg.sg}

        with ExitStack() as stack: 
            for val_ctx in self._get_val_ctx():
                stack.enter_context(val_ctx)

            fac = ModelFactory(
                preffix  = _PDF_NAME,
                obs      = data.space,
                l_shared = ['mu', 'sg'],
                l_float  = [],
                values   = values,
                l_pdf    = models)
            pdf = fac.get_pdf()

        ftr = Fitter(pdf = pdf, data = data)
        res = ftr.fit()
        print(res)

        fmod = FittedModel.from_fit(
            name= _PDF_NAME,
            cfg = fac.cfg,
            pdf = pdf,
            res = res)

        return fmod
    # ----------------------------
    def _get_data(
        self,
        obs : zobs,
        mass: Mass) -> zdat:
        '''
        Parameters
        ------------------
        mass: Used to build observable for data and get array of masses
        obs : Observable used to build zfit data object

        Returns
        ------------------
        zfit data object
        '''
        masses, weights = self.__get_arrays(mass = mass)
        data            = zfit.Data.from_numpy(
            obs     = obs,
            array   = masses,
            weights = weights)

        if not isinstance(data, zfit.Data):
            raise ValueError('Invalid data')

        return data
    # ----------------------------
    def __get_arrays(self, mass : Mass) -> tuple[NpFltArr, NpFltArr]:
        '''
        Parameters
        ------------------
        mass: Mass type, used to read database column

        Returns
        ------------------
        Tuple with numpy arrays with masses and weights
        '''
        obj = DataStore(
            comp        = self.__comp,
            trig        = self.__trig,
            min_entries = self.__cfg.mod_cfg.min_entries,
            max_entries = _MAX_SIZE)

        masses, weights = obj.get_array(mass = mass)
        obj.save_selection(path = self.__out_path / 'selection.json')

        return masses, weights
    # ----------------------------
    def _plot_fit(
        self,
        cfg_par : RangesConf,
        data    : zdat,
        pdf     : zpdf) -> None:
        cfg_plt    = ZFitPlotterConf.default()

        settings   = {
            'ext_text'   : f'{self.__comp.latex}\n {self.__qsq.latex} bin',
            'title'      : f'Entries: {data.n_events}; {self.__trig.value} trigger; {self.__label}',
            'plot_range' : cfg_par.rn}
        cfg_plt = cfg_plt.model_copy(update = settings)

        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = cfg_plt)

        plt.savefig(self.__out_path / 'fit.png')
        plt.close()
    # ----------------------------
    @property
    def model_path(self) -> Path:
        '''
        Path to JSON file with model
        '''
        return self.__out_path / 'model.json'
    # ----------------------------
    @overload
    def __load_model(self, use_kde : Literal[False], obs : zfit.Space) -> FittedModel           : ...
    @overload
    def __load_model(self, use_kde : Literal[True ], obs : zfit.Space) -> NonParametricModel    : ...
    def __load_model(self, use_kde : bool          , obs : zfit.Space) -> FittedModel | NonParametricModel:
        if use_kde:
            return NonParametricModel.from_json(path = self.model_path)

        model = FittedModel.from_json(path = self.model_path)
        return model.with_obs(obs = obs)
    # ----------------------------
    @overload
    def get_model(
        self,
        mode   : Mode,
        obs_ext: zobs,
        use_kde: Literal[False] = ...) -> FittedModel:...
    @overload
    def get_model(
        self,
        mode   : Mode,
        obs_ext: zobs,
        use_kde: Literal[True]) -> NonParametricModel:...
    def get_model(
        self,
        mode   : Mode,
        obs_ext: zobs,
        use_kde: bool = False) -> FittedModel | NonParametricModel:
        '''
        Parameters
        ---------------
        obs_ext: Observable that this model's PDF will use
        use_kde: If true won't try to fit to parametric model, default False
        mode   : Controls how output will be made, read, write or update

        Returns
        ---------------
        PDF associated to MC
        '''
        mode.validate(path = self.model_path)

        if self.model_path.exists() and not mode.skip_reading:
            log.info(f'Loading model at: {self.model_path}')
            try:
                return self.__load_model(use_kde, obs_ext)
            except Exception:
                log.warning(f'Removing and remaking broken model at {self.model_path}')
                self.model_path.unlink()

        log.info(f'Model not found at: {self.model_path}')
        cfg_par  = self.__cfg.read_conf(
            comp = self.__comp,
            trig = self.__trig,
            qsq  = self.__qsq )

        mass   = Mass.raw_from_project(project = self.__trig.project)
        obs    = zfit.Space(mass, limits = cfg_par.rn)
        data   = self._get_data(obs = obs, mass = mass)
        models = None if use_kde else self.__cfg.mod_cfg.get_model(nentries = data.num_entries)

        if models is None and not use_kde:
            raise ValueError(f'No model found for {data.num_entries} entries')

        fmod = self._get_model(
            data    = data,
            cfg_par = cfg_par,
            models  = models)

        fmod.to_json(path = self.model_path)

        return self.__load_model(use_kde, obs_ext)
# ----------------------------
