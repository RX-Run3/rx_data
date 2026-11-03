'''
Module storing ZModel class
'''

from collections.abc import Set
from functools       import cached_property
from typing          import Self
from contextlib      import contextmanager
from contextvars     import ContextVar
from pydantic        import BaseModel, ConfigDict, Field
from typing          import Callable
from zfit.interface  import ZfitSpace     as zobs
from zfit.pdf        import BasePDF       as zpdf
from zfit.param      import Parameter, ComposedParameter

from dmu             import LogStore
from dmu.stats       import ParameterLibrary as PL

from .imports        import zfit
from .types          import CorrectionImplementation, Model
from .ipatia         import Ipatia
from .zfit_models    import HypExp
from .zfit_models    import ModExp
from .zfit_models    import FermiDirac

log=LogStore.add_logger('dmu:stats:model_factory')

_FIX_CORRECTION : ContextVar[bool] = ContextVar('_FIX_CORRECTION', default = True)

type zpar = Parameter | ComposedParameter
# ------------------------------
class ModelFactoryConf(BaseModel, frozen = True):
    '''
    Class meant to configure the builder of PDFs

    Attributes
    ----------------
    values: Dictionary mapping parameter name (e.g. mu) to tuple with default, low and high bound
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True) # Due to reuse field that uses zpar

    pdfs          : list[Model]
    shared        : list[str]
    reparametrize : dict[str,CorrectionImplementation]
    fix           : dict[str,float]
    floating      : list[str]
    values        : dict[str,tuple[float,float,float]] = Field(default_factory=dict)
    reuse         : list[zpar]                         = Field(default_factory=list)
    # ------------------------------
    @classmethod
    def default(cls, pdfs : list[Model]) -> 'ModelFactoryConf':
        '''
        Parameters
        ------------
        pdfs: List of nicknames to PDFs

        Returns
        ------------
        Default configuration for ModelFactory
        '''
        return cls(
            pdfs          = pdfs,
            shared        = [],
            floating      = [],
            reparametrize = dict(),
            fix           = dict(),
            reuse         = [])
#-----------------------------------------
class MethodRegistry:
    '''
    Class intended to store protected methods belonging to ModelFactory class
    which is defined in this same module
    '''
    # Registry dictionary to hold methods
    _d_method : dict[Model,Callable] = {}

    @classmethod
    def register(cls, nickname : Model):
        '''
        Decorator in charge of registering method for given nickname
        '''
        def decorator(method : Callable):
            cls._d_method[nickname] = method
            return method

        return decorator

    @classmethod
    def get_method(cls, nickname : Model) -> Callable | None:
        '''
        Will return method in charge of building PDF, for an input nickname
        '''
        method = cls._d_method.get(nickname, None)

        if method is not None:
            return method

        log.warning('Available PDFs:')
        for value in cls._d_method:
            log.info(f'    {value}')

        return method

    @classmethod
    def get_pdf_names(cls) -> list[Model]:
        '''
        Returns list of PDFs that are registered/supported
        '''
        return list(cls._d_method)
#-----------------------------------------
class ModelFactory:
    '''
    Class used to create Zfit PDFs by passing only the nicknames, e.g.:

    ```python
    from dmu.stats.model_factory import ModelFactory

    l_pdf = ['dscb', 'gauss']
    l_shr = ['mu']
    l_flt = ['mu', 'sg']
    d_rep = {'mu' : 'scale', 'sg' : 'reso'}
    mod   = ModelFactory(
        preffix = 'signal',
        obs     = obs,
        l_pdf   = l_pdf,
        l_shared= l_shr,
        d_rep   = d_rep)
    pdf   = mod.get_pdf()
    ```

    where one can specify which parameters

    - Can be shared among the PDFs
    - Are meant to float if this fit is done to MC, in order to fix parameters in data.
    - Are scales or resolutions that need reparametrizations
    '''
    #-----------------------------------------
    def __init__(self, # noqa: PLR0913, PLR0917
        preffix  : str,
        obs      : zobs,
        l_pdf    : list[Model],
        l_shared : list[str],
        l_float  : list[str],
        values   : None | dict[str,tuple[float,float,float]] = None,
        l_reuse  : None | list[zpar]                         = None,
        d_fix    : None | dict[str,float]                    = None,
        d_rep    : None | dict[str,CorrectionImplementation] = None):
        '''
        preffix:  used to identify PDF, will be used to name every parameter
        obs:      zfit obserbable
        l_pdf:    List of PDF nicknames which are registered below
        l_shared: List of parameter names that are shared
        l_float:  List of parameter names to allow to float
        l_reuse:  Optional. List of parameters that if given will be used instead of built by factory
        d_fix:    Dictionary with keys as the beginning of the name of a parameter and value as the number
                  to which it has to be fixed. If not one and only one parameter is found, ValueError is raised
        d_rep:    Dictionary with keys as variables that will be reparametrized
        '''
        l_reuse = []     if l_reuse is None else l_reuse
        values  = dict() if values  is None else values

        if len(preffix) == 0:
            raise ValueError('Preffix cannot be an empty string, it will be used as name')

        self._values  = values
        self._preffix = preffix
        self._l_pdf   = l_pdf
        self._l_shr   = l_shared
        self._l_flt   = l_float
        self._d_fix   = d_fix
        self._d_rep   = d_rep
        self._d_reuse = { par.name : par for par in l_reuse }
        self._obs     = obs

        self._d_par : dict[str,zpar] = {}

        self._check_reparametrization()
    #-----------------------------------------
    def _check_reparametrization(self) -> None:
        '''
        This method:

        - Returns if no reparametrization has been requested
        - Raises if reparametrization is on any fixed parameter
        - Raises if trying to reparametrize anything that is not scales and resolutions
        '''
        if self._d_rep is None:
            return

        s_par_1 = set(self._d_rep)
        s_par_2 = set(self._l_flt)

        if not s_par_1.isdisjoint(s_par_2):
            log.info(f'Found  : {s_par_1}')
            log.info(f'Allowed: {s_par_2}')
            raise ValueError('Non empty intersection between floating and reparametrization parameters')

        s_kind  = set(self._d_rep.values())
        if not s_kind.issubset({'scale', 'reso'}):
            raise ValueError(f'Only scales and resolution reparametrizations allowed, found: {s_kind}')
    #-----------------------------------------
    def _split_name(self, name : str) -> tuple[str,str]:
        l_part = name.split('_')
        pname  = l_part[0]
        xname  = '_'.join(l_part[1:])

        return pname, xname
    #-----------------------------------------
    def _get_parameter_name(self, name : str, suffix : str) -> str:
        '''
        Parameters
        ---------------
        name  : Name of pdf and physical name, e.g mu_gauss
        suffix: Identifies this PDF, e.g. index of 3rd gaussian

        Returns
        ---------------
        Name of parameter which:

        - mu_preffix,     if parameter is shared
        - mu_preffix3     if not shared but not floating
        - mu_preffix3_flt if not shared and floating
        '''
        # pname = physical name, is something like mu or sg
        pname, xname = self._split_name(name)
        log.debug(f'Using physical name: {pname}')

        if pname in self._l_flt:
            # If reused parameter is floating
            # find it with flt
            reuse_name = f'{pname}_{suffix}_flt'
        else:
            reuse_name = f'{pname}_{suffix}'

        if reuse_name in self._d_reuse:
            log.debug(f'Picking name {reuse_name} for reused parameter')
            return self._add_float(pname=pname, name=pname)

        if pname in self._l_shr:
            name = f'{pname}_{self._preffix}'
            log.debug(f'Using model specific parameter name {name}')
        else:
            name = f'{pname}_{xname}_{self._preffix}{suffix}'
            log.debug(f'Using component specific parameter name {name}')

        return self._add_float(pname=pname, name=name)
    #-----------------------------------------
    def _add_float(self, pname : str, name : str) -> str:
        '''
        Parameters
        -------------
        pname : Physical name, e.g. mu
        name  : Actual parameter name, e.g. mu_cbl_3

        Returns
        -------------
        Actual parameter name with _flt appended if the physical version is meant to float
        '''
        if pname not in self._l_flt:
            return name

        return f'{name}_flt'
    #-----------------------------------------
    def _get_parameter(
        self,
        name   : str,
        kind   : Model,
        suffix : str) -> zpar:
        '''
        Parameters
        ----------------
        name  : Physical name of parameter, e.g. mu
        kind  : Identifies PDF, e.g. gaus
        suffix: If multiple PDFs of this kind, it will be some sort of index, e.g. _1, _2

        Returns
        ----------------
        Parameter, if it was :

        - Provided as part of l_reuse (e.g. mu), it will pick it up instead of building it
        - Specified as shared, it will build it once and then reuse that one.
        - Otherwise, it will make a new one, with a suffix to diferentiate it from whatever was already created
        '''

        par_name = self._get_parameter_name(f'{name}_{kind}', suffix)
        log.debug(f'Assigning name: {par_name}')

        if par_name in self._d_reuse:
            log.info(f'Reusing {par_name}')
            return self._d_reuse[par_name]

        if par_name in self._d_par:
            log.info(f'Picking already made parameter {par_name}')
            return self._d_par[par_name]

        rep_kind = self._get_reparametrization_type(name = name)

        val, low, high = self._get_parameter_values(model = kind, name = name)

        if rep_kind is not None:
            log.debug(f'Reparametrizing {par_name}')
            par  = self.get_reparametrization(
                name     = par_name,
                kind     = rep_kind,
                value    = val,
                low      = low,
                high     = high)
        elif val == low == high:
            log.info(f'Upper and lower edges agree, fixing parameter to: {low}')
            par  = zfit.param.Parameter(par_name, val, low - 1 , high + 1)
            par.floating = False
        else:
            log.debug(f'Creating new parameter {par_name}')
            par  = zfit.param.Parameter(par_name, val, low, high)

        self._d_par[par_name] = par

        return par
    # ----------------------
    def _get_parameter_values(
        self,
        model : Model,
        name  : str) -> tuple[float,float,float]:
        '''
        Parameters
        -------------
        name : Parameter name, e.g. mu
        model: PDF, e.g. gauss

        Returns
        -------------
        Tuple with initial, low and high value for parameter
        '''
        if name not in self._values:
            log.debug(f'Using default parameters for model/parameter: {model}/{name}')
            return PL.get_values(kind=model, parameter=name)

        log.info(f'Using custom parameters for model/name: {model}/{name}')

        return self._values[name]
    #-----------------------------------------
    def _get_reparametrization_type(self, name : str) -> CorrectionImplementation | None:
        '''
        Parameters
        -------------------
        name: Physical name of parameter, e.g. mu

        Returns
        -------------------
        Type of reparametrization (e.g. scale, resolution...)
        or None, if no reparametrization is needed
        '''
        if self._d_rep is None:
            return None

        return self._d_rep.get(name)
    #-----------------------------------------
    @staticmethod
    def get_reparametrization(
        name  : str,
        kind  : CorrectionImplementation,
        value : float,
        low   : float,
        high  : float) -> zpar:
        '''
        Parameters
        ---------------
        name    : Name of returned parameter
        kind    : Type of reparametrization
        value   : Initial value
        low/high: Bounds of original parameter as defined below

        Returns
        ---------------
        Parameter meant to be fitted and parametrized either as:

        composed = original * resolution
        composed = original + scale
        '''
        log.debug(f'Reparametrizing {name}')
        par_orig = zfit.Parameter(name, value, low, high)

        match kind:
            case CorrectionImplementation.reso:
                par_corr  = zfit.Parameter(f'{name}_reso_flt' , 1.0, 0.20, 5.0)
                func      = lambda d_par : d_par['orig'] * d_par['corr']
            case CorrectionImplementation.scale:
                par_corr  = zfit.Parameter(f'{name}_scale_flt', 0.0, -100, 100)
                func      = lambda d_par : d_par['orig'] + d_par['corr']
            case _:
                raise ValueError(f'Invalid correction: {kind}')

        par_comp  = zfit.ComposedParameter(
            name  = f'{name}_cmp',
            func  = func,
            params={'orig' : par_orig, 'corr' : par_corr} )

        if _FIX_CORRECTION.get():
            par_corr.floating = False
            par_orig.floating = True
        else:
            par_corr.floating = True
            par_orig.floating = False

        return par_comp
    #-----------------------------------------
    @MethodRegistry.register(Model.exp)
    def _get_exponential(self, suffix : str = '') -> zpdf:
        c   = self._get_parameter(kind = Model.exp, name = 'c', suffix = suffix)
        pdf = zfit.pdf.Exponential(c, self._obs, name=f'exp_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.ipatia)
    def _get_ipatia(self, suffix : str = '') -> zpdf:
        mu   = self._get_parameter(kind = Model.ipatia, name = 'mu'  , suffix = suffix)
        sg   = self._get_parameter(kind = Model.ipatia, name = 'sg'  , suffix = suffix)
        nl   = self._get_parameter(kind = Model.ipatia, name = 'nl'  , suffix = suffix)
        al   = self._get_parameter(kind = Model.ipatia, name = 'al'  , suffix = suffix)
        nr   = self._get_parameter(kind = Model.ipatia, name = 'nr'  , suffix = suffix)
        ar   = self._get_parameter(kind = Model.ipatia, name = 'ar'  , suffix = suffix)
        lam  = self._get_parameter(kind = Model.ipatia, name = 'lam' , suffix = suffix)
        beta = self._get_parameter(kind = Model.ipatia, name = 'beta', suffix = suffix)
        zeta = self._get_parameter(kind = Model.ipatia, name = 'zeta', suffix = suffix)

        pdf = Ipatia(
            mu   = mu,
            sigma= sg,
            lam  = lam,
            zeta = zeta,
            beta = beta,
            al   = al,
            nl   = nl,
            ar   = ar,
            nr   = nr,
            obs  = self._obs,
            name = f'ipatia_{self._preffix}{suffix}')

        return pdf
    # ---------------------------------------------
    @MethodRegistry.register(Model.hypexp)
    def _get_hypexp(self, suffix : str = '') -> zpdf:
        mu = self._get_parameter(kind = Model.hypexp, name = 'mu', suffix = suffix)
        ap = self._get_parameter(kind = Model.hypexp, name = 'ap', suffix = suffix)
        bt = self._get_parameter(kind = Model.hypexp, name = 'bt', suffix = suffix)

        pdf= HypExp(
            obs   = self._obs,
            mu    = mu,
            alpha = ap,
            beta  = bt,
            name  = f'hypexp_{self._preffix}{suffix}')

        return pdf
    # ---------------------------------------------
    @MethodRegistry.register(Model.fermi_dirac)
    def _get_fermi_dirac(self, suffix : str = '') -> zpdf:
        mu = self._get_parameter(kind = Model.fermi_dirac, name = 'mu', suffix = suffix)
        ap = self._get_parameter(kind = Model.fermi_dirac, name = 'ap', suffix = suffix)

        pdf= FermiDirac(
            obs   = self._obs,
            mu    = mu,
            ap    = ap,
            name  = f'fermi_dirac_{self._preffix}{suffix}')

        return pdf
    # ---------------------------------------------
    @MethodRegistry.register(Model.modexp)
    def _get_modexp(self, suffix : str = '') -> zpdf:
        mu = self._get_parameter(kind = Model.modexp, name = 'mu', suffix = suffix)
        ap = self._get_parameter(kind = Model.modexp, name = 'ap', suffix = suffix)
        bt = self._get_parameter(kind = Model.modexp, name = 'bt', suffix = suffix)

        pdf= ModExp(obs=self._obs, mu=mu, alpha=ap, beta=bt, name=f'modexp_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.pol1)
    def _get_pol1(self, suffix : str = '') -> zpdf:
        a   = self._get_parameter(kind = Model.pol1, name = 'a', suffix = suffix)
        pdf = zfit.pdf.Chebyshev(obs=self._obs, coeffs=[a], name=f'pol1_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.pol2)
    def _get_pol2(self, suffix : str = '') -> zpdf:
        a   = self._get_parameter(kind = Model.pol2, name = 'a', suffix = suffix)
        b   = self._get_parameter(kind = Model.pol2, name = 'b', suffix = suffix)
        pdf = zfit.pdf.Chebyshev(obs=self._obs, coeffs=[a, b   ], name=f'pol2_{self._preffix}{suffix}')

        return pdf
    # ---------------------------------------------
    @MethodRegistry.register(Model.pol3)
    def _get_pol3(self, suffix : str = '') -> zpdf:
        a   = self._get_parameter(kind = Model.pol3, name = 'a', suffix = suffix)
        b   = self._get_parameter(kind = Model.pol3, name = 'b', suffix = suffix)
        c   = self._get_parameter(kind = Model.pol3, name = 'c', suffix = suffix)

        pdf = zfit.pdf.Chebyshev(obs=self._obs, coeffs=[a, b, c], name=f'pol3_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.cbr)
    def _get_cbr(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.cbr, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.cbr, name = 'sg', suffix = suffix)
        ar  = self._get_parameter(kind = Model.cbr, name = 'ar', suffix = suffix)
        nr  = self._get_parameter(kind = Model.cbr, name = 'nr', suffix = suffix)

        pdf = zfit.pdf.CrystalBall(mu, sg, ar, nr, self._obs, name=f'cbr_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.suj)
    def _get_suj(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.suj, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.suj, name = 'sg', suffix = suffix)
        gm  = self._get_parameter(kind = Model.suj, name = 'gm', suffix = suffix)
        dl  = self._get_parameter(kind = Model.suj, name = 'dl', suffix = suffix)

        pdf = zfit.pdf.JohnsonSU(mu, sg, gm, dl, self._obs, name=f'suj_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.cbl)
    def _get_cbl(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.cbl, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.cbl, name = 'sg', suffix = suffix)
        al  = self._get_parameter(kind = Model.cbl, name = 'al', suffix = suffix)
        nl  = self._get_parameter(kind = Model.cbl, name = 'nl', suffix = suffix)

        pdf = zfit.pdf.CrystalBall(mu, sg, al, nl, self._obs, name=f'cbl_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.gauss)
    def _get_gauss(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.gauss, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.gauss, name = 'sg', suffix = suffix)

        pdf = zfit.pdf.Gauss(mu, sg, self._obs, name=f'gauss_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.dscb)
    def _get_dscb(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.dscb, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.dscb, name = 'sg', suffix = suffix)
        ar  = self._get_parameter(kind = Model.dscb, name = 'ar', suffix = suffix)
        al  = self._get_parameter(kind = Model.dscb, name = 'al', suffix = suffix)
        nr  = self._get_parameter(kind = Model.dscb, name = 'nr', suffix = suffix)
        nl  = self._get_parameter(kind = Model.dscb, name = 'nl', suffix = suffix)

        pdf = zfit.pdf.DoubleCB(mu, sg, al, nl, ar, nr, self._obs, name=f'dscb_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.voigt)
    def _get_voigt(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.voigt, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.voigt, name = 'sg', suffix = suffix)
        gm  = self._get_parameter(kind = Model.voigt, name = 'gm', suffix = suffix)

        pdf = zfit.pdf.Voigt(m=mu, sigma=sg, gamma=gm, obs=self._obs, name=f'voigt_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.qgauss)
    def _get_qgauss(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.qgauss, name = 'mu', suffix = suffix)
        sg  = self._get_parameter(kind = Model.qgauss, name = 'sg', suffix = suffix)
        q   = self._get_parameter(kind = Model.qgauss, name =  'q', suffix = suffix)

        pdf = zfit.pdf.QGauss(q=q, mu=mu, sigma=sg, obs=self._obs, name =f'qgauss_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    @MethodRegistry.register(Model.cauchy)
    def _get_cauchy(self, suffix : str = '') -> zpdf:
        mu  = self._get_parameter(kind = Model.cauchy, name = 'mu', suffix = suffix)
        gm  = self._get_parameter(kind = Model.cauchy, name = 'gm', suffix = suffix)

        pdf = zfit.pdf.Cauchy(obs=self._obs, m=mu, gamma=gm, name=f'cauchy_{self._preffix}{suffix}')

        return pdf
    #-----------------------------------------
    def _get_pdf_types(self) -> list[tuple[Model,str]]:
        '''
        Returns
        -----------------------
        list of tuples, one for each model, each tuple has:

        - Model name
        - Model suffix representing index of PDF, e.g. _1
        '''
        d_name_freq = {}

        l_type = []
        for name in self._l_pdf:
            if name not in d_name_freq:
                d_name_freq[name] = 1
            else:
                d_name_freq[name]+= 1

            frq = d_name_freq[name]
            frq = f'_{frq}'

            l_type.append((name, frq))

        return l_type
    #-----------------------------------------
    def _get_pdf(self, kind : Model, preffix : str) -> zpdf:
        fun = MethodRegistry.get_method(kind)
        if fun is None:
            raise NotImplementedError(f'PDF of type \"{kind}\" with preffix \"{preffix}\" is not implemented')

        return fun(self, suffix = preffix)
    #-----------------------------------------
    def _add_pdf(self, l_pdf : list[zpdf]) -> zpdf:
        nfrc = len(l_pdf)
        if nfrc == 1:
            log.debug('Requested only one PDF, skipping sum')
            pdf = l_pdf[0]

            return pdf.copy(name = self._preffix)

        l_frc= [ zfit.param.Parameter(f'mod_frc_{self._preffix}_{ifrc + 1}', 0.5, 0, 1) for ifrc in range(nfrc - 1) ]

        pdf = zfit.pdf.SumPDF(
            pdfs = l_pdf,
            name = self._preffix,
            fracs= l_frc)

        return pdf
    #-----------------------------------------
    def _find_par(self, s_par : Set[zpar], name_start : str) -> zpar:
        l_par_match = [ par for par in s_par if par.name.startswith(name_start) ]
        npar        = len(l_par_match)

        if npar!= 1:
            for par in s_par:
                log.info(par.name)

            raise ValueError(f'Found {npar} parameters starting with: {name_start}')

        return l_par_match[0]
    #-----------------------------------------
    def _fix_parameters(self, pdf : zpdf) -> zpdf:
        if self._d_fix is None:
            log.debug('Not fixing any parameter')
            return pdf

        s_par = pdf.get_params()

        log.info('-' * 30)
        log.info('Fixing parameters')
        log.info('-' * 30)
        for name_start, value in self._d_fix.items():
            par = self._find_par(s_par, name_start)
            par.set_value(value)

            log.info(f'{name_start:<20}{value:<20.3f}')
            par.floating = False

        return pdf
    #-----------------------------------------
    def get_pdf(self) -> zpdf:
        '''
        Given a list of strings representing PDFs returns the a zfit PDF which is
        the sum of them
        '''
        l_type=   self._get_pdf_types()
        l_pdf = [ self._get_pdf(kind, preffix) for kind, preffix in l_type ]
        pdf   =   self._add_pdf(l_pdf)
        pdf   =   self._fix_parameters(pdf)

        return pdf
    #-----------------------------------------
    @classmethod
    def from_conf(
        cls,
        obs    : zobs,
        prefix : str,
        cfg    : ModelFactoryConf) -> Self:
        '''
        Parameters
        ----------------
        prefix: Prefix for parameters
        obs   : Observable
        cfg   : Configuration needed to build factory

        Returns
        ----------------
        Model factory, build from configuration
        '''
        return cls(
            obs     = obs,
            preffix = prefix,
            l_pdf   = cfg.pdfs,
            d_fix   = cfg.fix,
            d_rep   = cfg.reparametrize,
            values  = cfg.values,
            l_shared= cfg.shared,
            l_float = cfg.floating,
            l_reuse = cfg.reuse)
    #-----------------------------------------
    @cached_property
    def cfg(self) -> ModelFactoryConf:
        '''
        Configuration that can be used to make this model factory
        '''
        reused_pars   = [ par for par in self._d_reuse.values() ]
        reparametrize = dict() if self._d_rep is None else self._d_rep
        fixed         = dict() if self._d_fix is None else self._d_fix

        return ModelFactoryConf(
            pdfs         = self._l_pdf,
            shared       = self._l_shr,
            floating     = self._l_flt,
            values       = self._values,
            fix          = fixed,
            reparametrize= reparametrize,
            reuse        = reused_pars)
    #-----------------------------------------
    @classmethod
    def correction(cls, fixed : bool):
        '''
        Parameters
        --------------
        fixed : If True, wil fix correction and float original parameter
                for reparametrized parameters
        '''

        @contextmanager
        def _context():
            token = _FIX_CORRECTION.set(fixed)

            try:
                yield
            finally:
                _FIX_CORRECTION.reset(token)

        return _context()
#-----------------------------------------
