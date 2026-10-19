'''
Module with tests for DataFitterSim class
'''
from pathlib     import Path
from dmu.stats   import ZFitPlotterConf
from rx_common   import Channel
from rx_common   import Component
from rx_common   import Trigger
from rx_common   import Brem
from rx_common   import Region
from rx_common   import Qsq
from rx_common   import MVAWp

from fitter      import CCbarConf
from fitter      import RXFitConfig
from fitter      import FitModelConf
from fitter      import NLLConf
from fitter      import DataFitterSim
from fitter      import PlotConf
from dmu.testing import get_nll 

# -------------------------------
def _get_nll(region : Region) -> NLLConf:
    if region.trigger.is_electron:
        nentries = 10_000
    else:
        nentries = 30_000

    nll  = get_nll(
        nentries= nentries,
        kind    = 's+b',
        prefix  = region.name)

    return NLLConf(
        nll         = nll,
        selection   = {},
        constraints = [])
# -------------------------------
def _get_cfg(region : Region) -> RXFitConfig:
    q2bin      = Qsq.central
    mva        = MVAWp.from_str(val = '0900')
    components = {q2bin : {Component.comb : CCbarConf.default(Channel.ee)}}
    plt_cfg    = PlotConf.default()
    plt_cfg    = plt_cfg.model_copy(update = {'regions' : {region : ZFitPlotterConf.default()}})

    new_fields = {
        'components' : components,
        'plots'      : {q2bin : plt_cfg} 
    }

    mod_cfg = FitModelConf.default()
    mod_cfg = mod_cfg.model_copy(update = {'trigger' : region.trigger})

    mod_cfg = mod_cfg.model_copy(update = new_fields)

    return RXFitConfig(
        name    = str(region),
        group   = 'test',
        q2bin   = q2bin,
        mva_cmb = mva,
        mva_prc = mva,
        mod_cfg = mod_cfg)
# -------------------------------
def test_rk(
    monkeypatch,
    tmp_path : Path):
    '''
    Simplest test
    '''
    monkeypatch.setenv('ANADIR', tmp_path)

    rk_ee   = Region(brem = Brem.brx12, trigger = Trigger.rk_ee_os)
    rk_mm   = Region(brem = Brem.zero , trigger = Trigger.rk_mm_os)
    regions = [rk_ee, rk_mm]

    d_nll : dict[Region, NLLConf] = {}
    for region in regions:
        d_nll[region] = _get_nll(region = region)

    d_cfg : dict[Region, RXFitConfig] = {}
    for region in regions:
        d_cfg[region] = _get_cfg(region = region)

    ftr = DataFitterSim(
        d_cfg = d_cfg,
        d_nll = d_nll, 
        q2bin = Qsq.central)

    res = ftr.run(skip_fit = False)

    print(res)
# -------------------------------
