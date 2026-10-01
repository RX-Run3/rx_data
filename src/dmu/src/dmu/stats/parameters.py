'''
Module with ParameterLibrary class
'''
import math
import yaml

from pathlib               import Path
from contextvars           import ContextVar
from contextlib            import contextmanager
from importlib.resources   import files
from zfit.param            import Parameter, ComposedParameter
from dmu                   import LogStore

from .types                import Model
from .configs              import YieldsConf
from .configs              import SimpleYieldConf
from .configs              import CompositeYieldConf
from .imports              import zfit

log      = LogStore.add_logger('dmu:parameters')
_YLD_CFG : ContextVar[YieldsConf | None] = ContextVar('_YLD_CFG', default = None)

type zpar = Parameter | ComposedParameter
# --------------------------------
class ParameterLibrary:
    '''
    Class meant to:

    - Connect to database (YAML file) with parameter values and make them available
    - Allow parameter values to be overriden
    '''
    _d_par  : dict[str,zpar      ] = {}   # When building parameters, they will be stored here, such that they can be reused, for simultaneous fits
    _values : dict[str,YieldsConf] = {}   # Values of parameters for all PDFs are in YAML file, they will be loaded here
    # --------------------------------
    @classmethod
    def _load_data(cls) -> None:
        if len(cls._values) > 0:
            return

        data_path = files('dmu_data').joinpath('stats/parameters/data.yaml')
        data_path = Path(str(data_path))
        data      = yaml.safe_load(data_path.read_text())

        cls._values = { pdf_name : YieldsConf(**pdf_data)
            for pdf_name, pdf_data in data.items()}

        npdf = len(cls._values)
        if npdf == 0:
            raise ValueError(f'Could not load any value from: {data_path}')

        log.debug(f'Found {npdf} PDFs')
    # --------------------------------
    @classmethod
    def print_parameters(cls, kind : Model) -> None:
        '''
        Method taking the kind of PDF to which the parameters are associated
        and printing the values.
        '''
        cfg = cls._values
        if kind not in cfg:
            for val in cfg:
                log.error(val)
            raise ValueError(f'Cannot find parameters for PDF of kind: {kind}')

        pdf_pars = cfg[kind]
        data     = pdf_pars.model_dump()

        log.info(yaml.safe_dump(data, indent=2))
    # --------------------------------
    @classmethod
    def get_values(cls, kind : Model, parameter : str) -> tuple[float,float,float]:
        '''
        Parameters
        --------------
        kind     : Kind of PDF, e.g. gaus, cbl, cbr, suj
        parameter: Name of parameter for PDF, e.g. mu, sg

        Returns
        --------------
        Tuple with central value, minimum and maximum
        '''
        if kind not in cls._values:
            raise ValueError(f'Cannot find PDF of kind: {kind}')

        if parameter not in cls._values[kind]:
            raise ValueError(f'For PDF {kind}, cannot find parameter: {parameter}')

        cfg = cls._values[kind][parameter]
        if not isinstance(cfg, SimpleYieldConf):
            raise ValueError(f'Parameter {parameter} is not elementary: {cfg}')

        if cfg.fix:
            return cfg.val, cfg.val, cfg.val

        return cfg.val, cfg.min, cfg.max
    # --------------------------------
    @classmethod
    def values(
        cls,
        kind      : str,
        parameter : str,
        val       : float,
        low       : float,
        high      : float):
        '''
        This function will override the value and range for the given parameter
        It should be typically used before using the ModelFactory class
        '''
        old = cls._values[kind][parameter]
        new = SimpleYieldConf(
            val = val,
            min = low,
            max = high)

        cls._values[kind][parameter] = new

        @contextmanager
        def _context():
            try:
                yield
            finally:
                cls._values[kind][parameter] = old

        return _context()
    # ----------------------
    @classmethod
    def parameter_schema(cls, cfg : YieldsConf):
        '''
        This context manager sets `_YLD_CFG`, which defines

        - How parameters are related. I.e. if they are multiplied
        - What their values are

        Parameters
        -------------
        cfg: DictConfig representing the values and relationships between paramaters
        '''
        token = _YLD_CFG.set(cfg)

        @contextmanager
        def _context():
            try:
                yield
            finally:
                _YLD_CFG.reset(token)

        return _context()
    # ----------------------
    @classmethod
    def get_yield(cls, name : str) -> zpar:
        '''
        Parameters
        -------------
        name: Name of parameter

        Returns
        -------------
        Zfit parameter
        '''
        log.debug(f'Picking up parameter: {name}')
        if name in cls._d_par:
            return cls._d_par[name]

        cfg = _YLD_CFG.get()
        if cfg is None:
            raise ValueError('Parameter schema not set')

        if name not in cfg:
            log.error(cfg)
            raise ValueError(f'Parameter {name} not found in configuration')

        cfg_yld = cfg[name]

        match cfg_yld:
            case CompositeYieldConf() as cfg:
                par = cls._get_composite_yield(name = name, cfg = cfg)
                cls._d_par[name] = par
            case SimpleYieldConf()    as cfg:
                par = cls._get_simple_yield(name = name, cfg = cfg)
                cls._d_par[name] = par

        return par
    # ----------------------
    @classmethod
    def _get_composite_yield(
        cls,
        name: str,
        cfg : CompositeYieldConf) -> zpar:
        '''
        Parameters
        -------------
        name: Parameter name
        cfg : Configuration needed to make composite yield

        Returns
        -------------
        Composite zfit parameter
        '''
        log.debug(f'Building {name} with:')
        log.debug(cfg)

        match cfg.kind:
            case 'mul':
                l_par    = [ cls.get_yield(name=comp_name) for comp_name in cfg.pars ]
                comp_par = cls._multiply_pars(name=name, pars=l_par)
            case 'dif':
                par_1    = cls.get_yield(name=cfg.pars[0])
                par_2    = cls.get_yield(name=cfg.pars[1])
                comp_par = cls._subtract_pars(name = name, par_1=par_1, par_2=par_2)

        return comp_par
    # ----------------------
    @classmethod
    def _subtract_pars(cls, name : str, par_1 : zpar, par_2 : zpar) -> zpar:
        '''
        Parameters
        -------------
        name   : Name of product parameter
        par_1/2: Parameters to be subtracted

        Returns
        -------------
        Product of parameters
        '''
        comp_par = zfit.ComposedParameter(name, lambda pars : pars[0] - pars[1], params=[par_1, par_2])

        return comp_par
    # ----------------------
    @classmethod
    def _multiply_pars(cls, name : str, pars : list[zpar]) -> zpar:
        '''
        Parameters
        -------------
        name: Name of product parameter
        pars: List of parameters

        Returns
        -------------
        Product of parameters
        '''
        if len(pars) == 0:
            raise ValueError(f'No factor parameters found for: {name}')

        def _product(pars : list[zpar]):
            return math.prod(pars)

        comp_par = zfit.ComposedParameter(name, _product, params=pars)

        return comp_par
    # ----------------------
    @classmethod
    def _get_simple_yield(
        cls,
        name : str,
        cfg  : SimpleYieldConf) -> zpar:
        '''
        Parameters
        -------------
        name    : Name of parameter to be returned
        cfg     : Config defining values of parameter bounds and default value of parameter

        Returns
        -------------
        A zfit parameter
        '''
        log.debug(f'Building {name} with:')
        log.debug(cfg)

        par = zfit.Parameter(name, cfg.val, cfg.min, cfg.max,)
        par.floating = not cfg.fix

        return par
# --------------------------------
ParameterLibrary._load_data()
