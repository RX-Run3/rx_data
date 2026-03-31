'''
Script used to interact with DataFitter tool
and run fits to the resonant mode
'''

import os
import argparse
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from contextlib    import ExitStack
from omegaconf     import DictConfig
from dmu           import LogStore
from dmu.stats     import GofCalculator
from dmu.stats     import ParameterLibrary as PL
from dmu.generic   import utilities as gut
from dmu.stats     import utilities as sut
from dmu.workflow  import Cache
from zfit.loss     import ExtendedUnbinnedNLL

from fitter        import FitModelConf
from fitter        import ToyConf
from fitter        import RXFitConfig
from fitter        import DataFitter
from fitter        import LikelihoodFactory
from rx_selection  import selection as sel
from rx_common     import Qsq, Component, Region

log=LogStore.add_logger('fitter:fit_rx_reso')
# ----------------------
def _set_logs() -> None:
    '''
    Hides log messages from certain tools
    '''
    LogStore.set_level('rx_fitter:inclusive_sample_weights', 30)
    LogStore.set_level('rx_fitter:inclusive_decays_weights', 30)

    LogStore.set_level('rx_data:path_splitter'    , 30)
    LogStore.set_level('rx_data:spec_maker'       , 30)
    LogStore.set_level('rx_data:sample_patcher'   , 30)
    LogStore.set_level('rx_data:sample_emulator'  , 30)
    LogStore.set_level('rx_data:rdf_getter'       , 30)

    LogStore.set_level('fitter:base_fitter'       , 30)
    LogStore.set_level('fitter:sim_fitter'        , 30)
    LogStore.set_level('fitter:likelihood_factory', 30)
# ----------------------
def _parse_args() -> RXFitConfig:
    '''
    Returns
    --------------
    Instance of configuration class, built from arguments
    '''
    if args is None:
        parser = argparse.ArgumentParser(description='Script used to fit RX data')
        parser.add_argument('-b', '--block'  , type=int  , help='Block number, if not passed will do all data'    , choices =[1,2,3,4,5,6,7,8], default=-1)
        parser.add_argument('-c', '--fit_cfg', type=str  , help='Name of configuration, e.g. reso/rkst/ee'        , required=True)
        parser.add_argument('-t', '--toy_cfg', type=str  , help='Name of toy config, e.g. toys/maker.yaml'        , default =  '')
        parser.add_argument('-N', '--ntoys'  , type=int  , help='If specified, this will override ntoys in config', default =0)
        parser.add_argument('-n', '--nthread', type=int  , help='Number of threads'                               , default =1)
        parser.add_argument('-l', '--log_lvl', type=int  , help='Logging level', choices=[5, 10, 20, 30]          , default =20)
        parser.add_argument('-q', '--q2bin'  , type=str  , help='q2 bin'      , choices=['jpsi', 'psi2']          , required=True)
        parser.add_argument('-C', '--mva_cmb', type=float, help='Cut on combinatorial MVA working point'          , required=True)
        parser.add_argument('-P', '--mva_prc', type=float, help='Cut on part reco MVA working point'              , required=True)
        args = parser.parse_args()

    fit_cfg = gut.load_conf(package='fitter_data', fpath=f'{args.fit_cfg}/data.yaml')
    toy_cfg = gut.load_conf(package='fitter_data', fpath=args.toy_cfg) if args.toy_cfg else None

    cfg         = RXFitConfig(
        mod_cfg = fit_cfg, 
        toy_cfg = toy_cfg,
        block   = args.block,
        q2bin   = args.q2bin,
        nthread = args.nthread,
        mva_cmb = args.mva_cmb,
        mva_prc = args.mva_prc,
        log_lvl = args.log_lvl,
        ntoys   = args.ntoys)

    return cfg
# ----------------------
def _get_nll(cfg : RXFitConfig) -> tuple[ExtendedUnbinnedNLL, dict[str,dict[str,str]]]:
    '''
    Parameters
    -------------
    cfg : Fit configuration

    Returns
    -------------
    Tuple with:
        - Negative log likelihood
        - Config related to model 
    '''
    ftr = LikelihoodFactory(
        name   = cfg.name,
        obs    = cfg.observable,
        q2bin  = cfg.q2bin,
        sample = Component.data_24,
        cfg    = cfg.mod_cfg)
    nll = ftr.run()
    cfg_mod = ftr.get_config()

    if not isinstance(nll, ExtendedUnbinnedNLL):
        raise TypeError('Likelihood object is not an ExtendedUnbinnedNLL')

    return nll, cfg_mod
# ----------------------
def _fit_electron(cfg : RXFitConfig) -> None:
    '''
    This is where DataFitter is used
    '''
    d_nll = {}
    with sel.update_selection(d_sel = {'brem_cat' : 'nbrem == 1'}):
        cfg.name = 'brem_001'
        cfg.replace(substring='brem_xxx', value=cfg.name)
        d_nll[cfg.name] = _get_nll(cfg=cfg)

    with sel.update_selection(d_sel = {'brem_cat' : 'nbrem == 2'}):
        cfg.name = 'brem_002'
        cfg.replace(substring='brem_001', value=cfg.name)
        d_nll[cfg.name] = _get_nll(cfg=cfg)

    with GofCalculator.disabled(value=True):
        ftr = DataFitter(
            name = cfg.q2bin,
            d_nll= d_nll, 
            cfg  = cfg.mod_cfg)
        ftr.run()
# ----------------------
def _fit_muon(cfg : RXFitConfig) -> None:
    '''
    This is where DataFitter is used
    '''
    d_nll    = {}
    cfg.name = 'brem_000'
    cfg.replace(substring='brem_000', value=cfg.name)
    d_nll[cfg.name] = _get_nll(cfg=cfg)

    with GofCalculator.disabled(value=True):
        ftr = DataFitter(
            name = cfg.q2bin,
            d_nll= d_nll, 
            cfg  = cfg.mod_cfg)
        ftr.run()
# ----------------------
def main(args : DictConfig | None = None):
    '''
    Entry point
    '''
    _set_logs()

    cfg = _parse_args(args=args) 

    overriding_selection = {
        'mass'  : '(1)',
        'block' : cfg.block_cut,
        'nobrm0': cfg.brem_cut,
        'bdt'   : cfg.mva_cut}

    Cache.set_cache_root(root=cfg.output_directory)
    with ExitStack() as stack:
        stack.enter_context(PL.parameter_schema(cfg=cfg.mod_cfg.model.yields))
        stack.enter_context(RDFGetter.multithreading(nthreads=cfg.nthread))
        stack.enter_context(Cache.turn_off_cache(val=[]))
        stack.enter_context(sut.blinded_variables(regex_list=['.*signal.*']))
        stack.enter_context(sel.custom_selection(d_sel=overriding_selection))

        if cfg.is_electron: 
            _fit_electron(cfg=cfg)
        else:
            _fit_muon(cfg=cfg)
# ----------------------
if __name__ == '__main__':
    main()
