'''
Script holding ConstraintReader class
'''
from typing              import Final
from dmu                 import LogStore
from dmu.stats           import ConstraintAdder
from dmu.stats           import ConstraintType
from dmu.stats           import Constraint, ParsHolder, Constraints
from dmu.stats           import ConstraintND
from dmu.stats           import Constraint1D
from rx_common           import Brem, Component, Trigger
from zfit.loss           import ExtendedUnbinnedNLL

from .eff_scales         import EffScales
from .configs            import CombinatorialConf, RXFitConfig
from .prec_scales        import get_constraints as get_prec_constraints
from .misid_constraints  import MisIDConstraints
from .cmb_constraints    import CmbConstraints
from .signal_constraints import SignalConstraints

_RARE_RK_MISID_COMPONENTS : Final[set[Component]] = {Component.bpkkk, Component.bpkpipi}

log=LogStore.add_logger('fitter:constraint_reader')
# -------------------------------------------------------------
class ConstraintReader:
    '''
    Class meant to provide constraints for fitting model
    '''
    # ----------------------
    def __init__(
        self,
        brem  : Brem,
        nll   : ParsHolder,
        cfg   : RXFitConfig,
        signal: Component):
        '''
        Parameters
        -------------------
        Brem  : brem category
        nll   : Likelihoood
        cfg   : Object storing fit configuration
        signal: Process considered as the signal when calculating denominator of rare Partially
                reconstructed scale constraints
        '''
        s_par         = nll.get_params(floating=True)
        if not s_par:
            raise ValueError('No floating parameters found in parameters holder')

        self._brem    = brem
        self._nll     = nll
        self._l_par   = [ par.name for par in s_par ]
        self._cfg     = cfg
        self._signal  = signal

        self._constraints : list[Constraint] = []
    # ----------------------
    def _add_bkg_fraction_constraints(self, skip : bool) -> None:
        '''
        Appends constraints to _constraints list for parameters in parameter holder
        whose names start with `s_{COMPONENT}_brem_...`
        '''
        if skip:
            log.warning('Dropping part-reco constraints')
            return

        log.info('Getting background fraction constraints')
        self._constraints += get_prec_constraints(
            cfg    = self._cfg,
            pars   = self._l_par,
            signal = self._signal,
            brem   = self._brem)
    # ----------------------
    def _get_eff_constraint_inputs(self) -> tuple[str,Trigger,Trigger] | None:
        '''
        Returns tuple with:

        - Efficiency ratio parameter to be constrained
        - Trigger associated to signal region where original yield is measured
        - Trigger associated to signal region where yield is needed
        '''
        pars     = self._nll.get_params(floating = True)
        eff_pars = [ par for par in pars if par.name.startswith('eff_') ]

        if not eff_pars:
            log.debug('No efficiency ratio parameters to constraint')
            return

        if len(eff_pars) != 1:
            raise ValueError(f'Multiple efficiency parameters to constraint: {eff_pars}')

        eff_par = eff_pars[0]
        name    = eff_par.name
        parts   = name.split('-')

        try:
            source = Trigger(parts[1])
            target = Trigger(parts[2])
        except Exception as exc:
            raise ValueError(f'Cannot extract source and target triggers from: {name}') from exc

        return name, source, target
    # ----------------------
    def _add_eff_constraints(self, skip : bool) -> None:
        '''
        Appends constraints to _constraints list for parameters in parameter holder
        whose names start with `eff_{source_trig}_{target_trig}...`
        '''
        if skip:
            log.warning('Dropping efficiency ratio constraints')
            return

        data = self._get_eff_constraint_inputs()
        if data is None:
            log.info('No parameters found for efficiency constraints')
            return

        var_name, source, target = data

        obj = EffScales(
            out_dir = self._cfg.output_directory,
            sample  = self._signal,
            channel = source.channel,
            source  = source.project,
            target  = target.project,
            brem    = self._brem,
            q2bin   = self._cfg.q2bin)

        val, err = obj.get_value()

        cons = Constraint1D(
            name = var_name,
            kind = ConstraintType.gauss,
            mu   = val,
            sg   = err)

        self._constraints.append(cons)
    # ----------------------
    def _add_misid_constraints(self, skip : bool) -> None:
        '''
        Adds constraints for fully hadronic MisID components
        '''
        if skip:
            return

        components= self._cfg.mod_cfg.components
        all_found = all(component in components for component in _RARE_RK_MISID_COMPONENTS)
        any_found = any(component in components for component in _RARE_RK_MISID_COMPONENTS)
        if not all_found and     any_found:
            raise ValueError('At least one misID component was found, but not all')

        if not all_found and not any_found:
            log.info('Skipping rare RK misID constraints')
            return

        log.info('Adding MisID constraints')

        cfg = self._cfg.mod_cfg.constraints.misid
        if cfg is None:
            log.debug('No MisID constraints config found, not adding constraints')
            return

        mrd       = MisIDConstraints(
            cfg   = cfg,
            q2bin = self._cfg.q2bin)

        cns = mrd.get_constraints()
        self._constraints += list(cns.root.values())
    # ----------------------
    def _add_combinatorial_constraints(self, skip : bool) -> None:
        '''
        Adds combinatorial constraints
        '''
        if skip or not self._cfg.mod_cfg.constraints.combinatorial:
            log.warning('Dropping combinatorial constraints')
            return

        components = self._cfg.mod_cfg.components[self._cfg.q2bin]

        if Component.comb not in components:
            log.warning(f'Combinatorial {Component.comb} component not found, not calculating constraints')
            return

        cmb_cfg = components[Component.comb]
        if not isinstance(cmb_cfg, CombinatorialConf):
            raise ValueError(f'Expected combinatorial config, got: {cmb_cfg}')

        if self._cfg.q2bin not in cmb_cfg.constraints.parameters:
            log.info(f'Not constraining the combinatorial shape for: {self._cfg.q2bin}/{self._cfg.mod_cfg.trigger}')
            return

        calc        = CmbConstraints(
            brem    = self._brem,
            signal  = self._signal,
            cfg_fit = self._cfg)

        self._constraints.append( calc.get_constraint() )
    # ----------------------
    def _add_signal_constraints(self, skip : bool) -> None:
        '''
        Update _constraints with constraints to the mass scale, resolution
        '''
        if skip or not self._cfg.mod_cfg.constraints.signal_shape:
            log.warning('Dropping signal shape constraints')
            return

        calc = SignalConstraints(
            channel = self._cfg.mod_cfg.trigger.channel,
            comp    = self._signal,
            nll     = self._nll)

        cons = calc.get_constraints()

        if self._cfg.mod_cfg.trigger.is_electron and not cons:
            for par in self._nll.get_params():
                log.error(par.name)

            raise ValueError(f'No constraints found for {self._signal}')

        log.info(f'Found {len(cons)} signal constraints')

        self._constraints += cons
    # ----------------------
    def get_constraints(
        self,
        skip_misid : bool = False,
        skip_prec  : bool = False,
        skip_comb  : bool = False,
        skip_signal: bool = False,
        skip_eff   : bool = False) -> Constraints[Constraint1D | ConstraintND]:
        '''
        Parameters
        ---------------
        skip_xx: By default false, if true, will skip constraints, meant for tests

        Returns
        ---------------
        Container holding constraints object
        '''
        self._add_misid_constraints(skip = skip_misid)
        self._add_bkg_fraction_constraints(skip = skip_prec)
        self._add_combinatorial_constraints(skip = skip_comb)
        self._add_signal_constraints(skip = skip_signal)
        self._add_eff_constraints(skip = skip_eff)

        data : dict[str,Constraint] = { constraint.name : constraint for constraint in self._constraints }
        constraints = Constraints[Constraint1D | ConstraintND](root = data)

        return constraints
# -------------------------------------------------------------
def add_constraints(
    brem: Brem,
    nll : ExtendedUnbinnedNLL,
    cfg : RXFitConfig) -> tuple[ExtendedUnbinnedNLL, Constraints]:
    '''
    Parameters
    -------------
    brem: Brem region
    nll : Likelihood
    cfg : Object holding configuration for fit

    Returns
    -------------
    Tuple with:

    - Constrained likelihood
    - Object holding constraints
    '''
    signal = cfg.mod_cfg.trigger.get_signal_component(qsq = cfg.q2bin)
    crd  = ConstraintReader(
        brem   = brem,
        signal = signal,
        nll    = nll,
        cfg    = cfg)
    cons = crd.get_constraints()

    cons.to_json(path = cfg.output_directory / f'constraints/{brem}.json')

    if not cons:
        log.warning('Not using any constraints')

    cad  = ConstraintAdder(nll=nll, constraints=cons)
    nll  = cad.get_nll()

    return nll, cons
# -------------------------------------------------------------
