'''
Module used to test CmbConstraints class
'''
import pytest 

from contextlib   import ExitStack
from pathlib      import Path
from dmu          import LogStore
from dmu.workflow import Cache
from dmu.generic  import UnpackerModel, utilities           as gut
from dmu.stats    import ConstraintND
from dmu.stats    import ParameterLibrary as PL

from rx_common    import Cuts, Qsq, Region
from rx_selection import selection           as sel

from fitter       import CmbConstraints
from fitter       import CombinatorialConf

log=LogStore.add_logger('test_cmb_constraints')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:cmb_constraints', 10)
    LogStore.set_level('dmu:stats:fitter'      , 10)
    LogStore.set_level('dmu:stats:minimizers'  , 10)
# ----------------------
def _get_nll(
    reg   : Region,
    cfg   : CombinatorialConf,
    q2bin : Qsq) -> zlos:
    '''
    Returns
    -------------
    Likelihood with a combinatorial PDF
    '''
    pdfs= cfg.models[q2bin].pdfs
    obs = zfit.Space('B_Mass_smr', limits=(4600, 6900))
    mod = ModelFactory(
        preffix = f'{Component.comb}_{reg}',
        obs     = obs,
        l_pdf   = pdfs,
        l_shared= [],
        l_float = [])

    pdf   = mod.get_pdf()
    data  = pdf.create_sampler(1000)

    return zlos(model = pdf, data = data)
# ----------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_simple(q2bin : Qsq, tmp_path : Path):
    '''
    Simplest test of CmbConstraints
    '''
    region = Region.brem_x12
    data   = gut.load_data(
        package= 'fitter_data', 
        fpath  = 'rare/rk/ee/comb.yaml')

    cfg  = CombinatorialConf(**data)
    nll  = _get_nll(cfg = cfg, q2bin = q2bin, reg = region)

    d_sel = {
        Cuts.cmb   : 'mva_cmb > 0.6 && mva_cmb < 0.9',
        Cuts.prc   : 'mva_prc > 0.5',
        Cuts.brem  : 'nbrem != 0',
        Cuts.block : '(1)',
    }

    with Cache.cache_root(path = tmp_path),\
        sel.custom_selection(d_sel = d_sel):
        calc      = CmbConstraints(
            reg   = region,
            nll   = nll,
            cfg   = cfg,
            q2bin = q2bin)

    constraint = calc.get_constraint()

    assert isinstance(constraint, ConstraintND)

    print(constraint)
# ----------------------
