'''
Module containing the MisIDConstraints class
'''
from pathlib             import Path
from typing              import Final
from rx_common           import Component, Correction, Cuts, Qsq, Region
from rx_selection        import selection as sel

from dmu.stats           import Constraints
from dmu.stats           import ConstraintType, FitResult, GofCalculator
from dmu.stats           import ParameterLibrary as PL
from dmu.stats           import Constraint1D

from dmu                 import LogStore
from dmu.generic         import utilities        as gut
from dmu.workflow        import Cache

from .configs            import FitModelConf, MisIDConf
from .data_fitter        import DataFitter
from .likelihood_factory import LikelihoodFactory, NLLConf
from .data_preprocessor  import DataPreprocessor

log=LogStore.add_logger('fitter:misid_constraints')
# -------------------------        
class MisIDConstraints(Cache):
    '''
    Class meant to provide constraints for the yields of different
    misID components, e.g.:

    - hdpipi:
        - 3
        - 1
    - hdkk:
        - 4
        - 2
    '''
    # ----------------------
    def __init__(
        self, 
        cfg   : FitModelConf, 
        q2bin : Qsq):
        '''
        Parameters
        -------------
        cfg      : configuration needed to build PDF
        q2bin    : E.g. central
        '''
        self._data_sample : Final[Component] = Component.data_24 

        self._cfg   = cfg
        self._q2bin = q2bin

        d_sel = sel.selection(
            q2bin   = self._q2bin, 
            trigger = self._cfg.trigger, 
            process = self._data_sample)

        Cache.__init__(
            self,
            out_path = Path('constraints'),
            d_sel    = { cut.name : val for cut, val in d_sel.items() }, 
            config   = cfg.model_dump(),
        )
    # ----------------------
    def __get_constraints(self, pars : FitResult) -> dict[str,tuple[float,float]]:
        '''
        Parameters
        -------------
        pars: Dictionary with parameters from fit to control region

        Returns
        -------------
        Dictionary with yields in signal region
        '''
        d_yield : dict[str, tuple[float,float]] = {}
        for region in Region.hadronic_misid():
            # Use constraint for signal region
            d_yield[f'yld_{region.signal}'] = self.__get_signal_region_yield(
                region   = region, # Pick it from control region
                pars     = pars) 

        return d_yield 
    # ----------------------
    def __get_signal_region_yield(
        self, 
        region   : Region, 
        pars     : FitResult) -> tuple[float,float]:
        '''
        Parameters
        -------------
        region   : Identifies the control region, e.g. kk or pipi
        pars     : Dictionary with fitting parameters for fit to control region

        Returns
        -------------
        Tuple with expected signal region yield and error
        '''
        control_yield, control_error = pars[f'yld_{region.signal}_{region}']
        scale = self.__get_transfer_factor(region=region)

        # Use it to scale yield from control region in data
        value = control_yield * scale
        error = control_error * scale

        log.info(f'Control yield: {control_yield:.3f}')
        log.info(f'Signal yield: {value:.3f}')
        log.info(20 * '-')

        return value, error
    # ----------------------
    def __get_transfer_factor(self, region : Region) -> float:
        '''
        Parameters
        -------------
        nickname: Sample nickname, e.g. hdkk, hdpipi        

        Returns
        -------------
        Ratio of PID efficiencies between signal and control region
        Needed to translate MisID yields in control region to expectation
        in signal region
        '''
        cfg = self._cfg.components[self._q2bin][region.signal]
        if not isinstance(cfg, MisIDConf):
            cfg_type = type(cfg)
            raise ValueError(f'Config for hadronic misID components of type: {cfg_type}')

        sig_yld, ctr_yld = 0, 0 
        # Extract yields from weighted (PID) no PID misID MC
        log.info(20 * '-')
        for pid_region in ['signal', 'control']:
            prp = DataPreprocessor(
                name      = f'transfer_factor/{region}_{pid_region}',
                obs       = region.obs,
                sample    = cfg.component,
                trigger   = self._cfg.trigger,
                is_sig    = pid_region == 'signal',
                wgt_cfg   = {Correction.pid : cfg.weights},
                selection = {Cuts.pid_l : '(1)'},
                q2bin     = self._q2bin)
            dat = prp.get_data()
            yld = dat.weights.numpy().sum()
            yld = float(yld)

            log.info(f'Region {pid_region} MC yield: {yld:.3f}')

            if pid_region == 'signal':
                sig_yld = yld
            else:
                ctr_yld = yld

        return sig_yld / ctr_yld
    # ----------------------
    def __get_pid_cut(self, region : Region) -> str:
        '''
        Parameters
        -------------
        region: Type of control region, e.g. kkk or kpipi

        Returns
        -------------
        PID cut needed to build control region
        '''
        cut    = self._cfg.selection[self._q2bin][Cuts.pid_l]
        cut_l1 = cut.replace('LEP_', 'L1_')
        cut_l2 = cut.replace('LEP_', 'L2_')

        # This is the FailFail region in data
        cut = f'({cut_l1}) && ({cut_l2})'

        log.info('')
        log.info(f'Building {region} PID control region with:')
        log.info(cut)
        log.info('')

        return cut
    # ----------------------
    def __get_control_nll(self, region : Region) -> NLLConf:
        '''
        Parameters
        -------------
        region: Control region type, e.g. kkk, kpipi

        Returns
        -------------
        Object storing NLL and selection
        '''
        pid_cut = self.__get_pid_cut(region=region)

        with PL.parameter_schema(cfg=self._cfg.yields),\
             sel.update_selection(d_sel={Cuts.pid_l : pid_cut}):

            ftr = LikelihoodFactory(
                obs    = region.obs,
                name   = region,
                sample = self._data_sample, 
                q2bin  = self._q2bin,
                cfg    = self._cfg)
            nll = ftr.run()

        return nll
    # ----------------------
    def get_constraints(self) -> Constraints[Constraint1D]:
        '''
        Returns
        -------------
        Constraints on normalization of misID components, i.e.:

        kkk   : (yield, error)
        kpipi : (yield, error)
        '''
        cons_path = self._out_path / 'misid.yaml'
        if self._copy_from_cache():
            log.info(f'Found cached: {cons_path}')

            d_cns = gut.load_json(cons_path)
            cons  = Constraint1D.from_dict(
                data = d_cns, 
                kind = ConstraintType.gauss)

            return cons

        log.info(f'Running full calculation, nothing cached for hash {self._hsh} in: {cons_path}')

        l_res : list[FitResult] = []
        for region in Region.hadronic_misid():
            nll = self.__get_control_nll(region=region)

            with GofCalculator.disabled(value=True):
                ftr      = DataFitter(
                    q2bin= self._q2bin, 
                    d_nll= { region : nll }, 
                    cfg  = self._cfg)

                cfg = self._cfg.components[self._q2bin][region.signal]

                if not isinstance(cfg, MisIDConf):
                    tconf = type(cfg)
                    raise ValueError(f'Config for {region} is of the wrong type: {tconf}')

                res = ftr.run(skip_fit = False)
                l_res.append(res)

        pars  = FitResult.merge(results = l_res)
        d_cns = self.__get_constraints(pars=pars)
        gut.dump_json(data=d_cns, path=cons_path)

        self._cache()

        const    = Constraint1D.from_dict(
            data = d_cns, 
            kind = ConstraintType.gauss)

        return const
# -------------------------
