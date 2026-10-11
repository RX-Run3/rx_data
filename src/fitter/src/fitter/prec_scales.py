'''
Module containing class PrecScales 
'''

import math
import numpy
import jacobi   as jac

from pathlib         import Path
from dmu             import LogStore
from dmu.stats       import Constraint1D, ConstraintType
from dmu.generic     import utilities  as gut
from rx_common       import Qsq, Brem
from rx_common       import Component
from rx_common       import Trigger 
from rx_selection    import selection  as sel
from rx_efficiencies import EfficiencyCalculator

from .configs        import RXFitConfig

log=LogStore.add_logger('fitter:prec_scales')
#------------------------------------------
class PrecScales:
    '''
    Class used to calculate scale factor between yields of background component and signal
    '''
    #------------------------------------------
    def __init__(
        self, 
        output_directory : Path,
        trigger          : Trigger,
        brem             : Brem,
        q2bin            : Qsq):
        '''
        Parameters
        --------------------
        output_directory : This is the full path to the directory where outputs will be saved
        trigger          : Hlt2 trigger, needed to pick selection to get efficiencies
        brem             : Bremsstrahlung category to get this scale for
        q2bin            : Needed to apply correct selection to get correct efficiencies and scales
        '''
        self._out_dir     = output_directory
        self._trigger     = trigger 
        self._brem        = brem
        self._q2bin       = q2bin
        self._d_frbf : dict[str,dict[str,tuple[float,float]]] = gut.load_data(
            package='rx_efficiencies_data', 
            fpath  ='scales/fr_bf.yaml')
    #------------------------------------------
    def _check_arg(self, l_val, val, name):
        if val not in l_val:
            raise ValueError(f'{name} {val} not allowed')

        log.debug(f'{name:<20}{"->":20}{val:<20}')
    #------------------------------------------
    def _get_fr(self, proc : str) -> tuple[float,float]:
        '''
        Returns hadronization fraction for given process
        '''
        if   proc.startswith('bp'):
            name = 'fu'
        elif proc.startswith('bd'):
            name = 'fd'
        elif proc.startswith('bs'):
            name = 'fs'
        elif proc.startswith('lb'):
            name = 'flb'
        else:
            raise ValueError(f'Cannot find hadronization fraction for: {proc}')

        fx = self._d_frbf['fr'][name]

        return fx
    #------------------------------------------
    def _mult_brs(self, bfractions : list[tuple[float,float]]) -> tuple[float,float]:
        '''
        Parameters
        -----------------------
        bfractions: List of branching fraction, branching fraction error tuples

        Returns
        -----------------------
        A tuple with the product of those branching fractions and the error in the product
        '''
        log.debug('Multiplying branching fractions')

        l_br_val = [ float(br[0]) for br in bfractions ] # These numbers come from YAML files
        l_br_err = [ float(br[1]) for br in bfractions ] # when using "e" in scientific notation, these numbers are made into strings

        br_cov   = numpy.diag(l_br_err) ** 2
        val, var = jac.propagate( # type: ignore
            math.prod,
            l_br_val,             # type: ignore
            br_cov)               # type: ignore

        err = math.sqrt(var)
        val = float(val)

        return val, err
    #------------------------------------------
    def _get_br(self, proc : str) -> tuple[float,float]:
        log.debug(f'Calculating BR for {proc}')

        l_dec = Component[proc].subdecays
        l_bf  = [ self._d_frbf['bf'][dec] for dec in l_dec ]

        return self._mult_brs(l_bf)
    #------------------------------------------
    def _get_ef(self, component : Component) -> tuple[float,float]:
        '''
        Parameters
        --------------
        component: Represents sample whose efficiency is needed

        Returns
        --------------
        Tuple with efficiency value and error
        '''
        log.debug(f'Calculating efficiencies for {component}')

        with sel.update_selection(d_sel = self._brem.region.selection):
            obj = EfficiencyCalculator(
                out_dir= self._out_dir,
                q2bin  = self._q2bin, 
                sample = component, 
                trigger= self._trigger)
            val = obj.get_efficiency()

        log.debug(f'Efficiency: {val}')

        return val
    #------------------------------------------
    def _print_vars(self, l_tup : list[tuple[float,float]], proc : str) -> None:
        log.debug('')
        log.debug(f'Decay: {proc}')
        log.debug('-' * 20)
        log.debug(f'{"Var":<20}{"Value":<20}{"Error":<20}')
        log.debug('-' * 20)
        for (val, err), name in zip(l_tup, ['fr', 'br', 'eff'], strict=True):
            log.debug(f'{name:<20}{val:<20.3e}{err:<20.3e}')
        log.debug('-' * 20)
    #------------------------------------------
    def get_scale(
        self, 
        background : Component,
        signal     : Component) -> tuple[float,float]:
        '''
        Parameters
        -----------------------
        background: Component associated to background to scale
        signal    : Component associated to signal WRT which to scale, e.g. bpkpee

        Returns
        ---------------
        Scale factor k and error, meant to be used in:

        Nbackground = k * Nsignal

        reparametrization, during fit.
        '''
        fr_bkg = self._get_fr(background)
        br_bkg = self._get_br(background)
        ef_bkg = self._get_ef(background)

        fr_sig = self._get_fr(signal)
        br_sig = self._get_br(signal)
        ef_sig = self._get_ef(signal)

        l_tup = [fr_sig, br_sig, ef_sig, fr_bkg, br_bkg, ef_bkg]
        l_val = [ tup[0] for tup in l_tup]
        l_err = [ tup[1] for tup in l_tup]
        cov   = numpy.diag(l_err) ** 2

        self._print_vars(l_tup[:3], proc=    signal)
        self._print_vars(l_tup[3:], proc=background)

        val, var = jac.propagate(lambda x : (x[3] * x[4] * x[5]) / (x[0] * x[1] * x[2]), l_val, cov) # type: ignore
        val = float(val)
        err = math.sqrt(var)

        return val, err
    #------------------------------------------
    def get_constraint(
        self, 
        background : Component,
        signal     : Component, 
        par        : str) -> Constraint1D:
        '''
        Parameters
        ---------------
        background : Background component
        signal     : Signal component
        par        : Name of parameter to constrain

        Returns
        ---------------
        Constrain
        '''
        val, err = self.get_scale(
            background = background,
            signal     = signal)

        cns = Constraint1D(
            name = par,
            kind = ConstraintType.gauss,
            mu   = val,
            sg   = err)
        
        return cns
#------------------------------------------
def get_constraints(
    brem   : Brem,
    pars   : list[str],
    signal : Component,
    cfg    : RXFitConfig) -> list[Constraint1D]:
    '''
    Parameters
    ------------------
    brem   : Category needed to name constraints
    pars   : Parameters known, e.g. in NLL
    signal : Signal component w.r.t which constraint
    cfg    : Full fit configuration

    Returns
    ------------------
    List of constraints
    '''
    if not cfg.mod_cfg.constraints.signal_fraction:
        log.warning('Dropping part-reco constraints')
        return []

    components = cfg.mod_cfg.constraints.signal_fraction
    scales     = {f's_{comp}_{brem.region}' : comp for comp in components}
    log.debug('Looking for scales:')
    for scale in scales:
        log.debug(scale)

    obj = PrecScales(
        output_directory = cfg.output_directory,
        trigger          = cfg.mod_cfg.trigger,
        brem             = brem,
        q2bin            = cfg.q2bin)

    constraints : list[Constraint1D] = []
    for par in pars:
        if par not in scales:
            log.debug(f'Skipping: {par}')
            continue

        log.info(f'Adding part reco constraint for: {par}')

        background = scales[par]
        cns = obj.get_constraint(
            par        = par, 
            background = background,
            signal     = signal)
        constraints.append(cns)

    return constraints 
#------------------------------------------
