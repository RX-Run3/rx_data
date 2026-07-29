import os
import pytest

from typing    import Final
from pathlib   import Path
from fitter    import ParameterReader
from fitter    import MVAWp
from rx_common import Brem
from rx_common import Trigger 
from rx_common import Qsq 
from rx_common import Block
from dmu       import LogStore

log=LogStore.add_logger('fitter:test_parameter_reader')

_TRIGGERS : Final[list[Trigger  ]] = [Trigger.rk_ee_os, Trigger.rkst_ee_os, Trigger.rk_mm_os, Trigger.rkst_mm_os]
_BREMS    : Final[list[Brem     ]] = [Brem.zero, Brem.one, Brem.two]
_Q2BINS   : Final[list[Qsq      ]] = [Qsq.jpsi, Qsq.psi2]
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize() -> None:
    LogStore.set_level('fitter:parameter_reader', 10)
# -----------------------
@pytest.mark.parametrize('q2bin',        _Q2BINS)
@pytest.mark.parametrize('trig' ,      _TRIGGERS)
@pytest.mark.parametrize('brem' ,         _BREMS)
@pytest.mark.parametrize('block', Block.blocks())
@pytest.mark.parametrize('is_mc',  [True, False])
def test_initializer(
    is_mc : bool,
    q2bin : Qsq,
    trig  : Trigger,
    block : Block, 
    brem  : Brem):
    '''
    Test reader with initializer 
    '''
    if trig.is_electron and brem == Brem.zero:
        return

    if trig.is_muon     and brem != Brem.zero:
        return

    name = 'reso_dtf-latest' # 'reso_no_dtf'
    rdr  = ParameterReader(name = name)
    meas = rdr(
        brem     = brem, 
        block    = block, 
        is_mc    = is_mc,
        cmb      = MVAWp.from_str('0.99'),
        prc      = MVAWp.from_str('0.60'),
        q2bin    = q2bin,
        trigger  = trig, 
    )

    print(meas)
# -----------------------
@pytest.mark.parametrize('q2bin',        _Q2BINS)
@pytest.mark.parametrize('trig' ,      _TRIGGERS)
@pytest.mark.parametrize('brem' ,         _BREMS)
@pytest.mark.parametrize('block', Block.blocks())
@pytest.mark.parametrize('is_mc',  [True, False])
def test_pars_path(
    is_mc : bool,
    q2bin : Qsq,
    trig  : Trigger,
    block : Block, 
    brem  : Brem):
    '''
    Test context manager user to set path to parameters 
    '''
    if trig.is_electron and brem == Brem.zero:
        return

    if trig.is_muon     and brem != Brem.zero:
        return

    name      = 'reso_dtf-latest' # 'reso_no_dtf'
    ana_dir   = Path(os.environ['ANADIR'])
    pars_path = ana_dir / f'fits/data/{name}/parameters.parquet'

    with ParameterReader.inputs_from(pars_path = pars_path):
        rdr  = ParameterReader()
        meas = rdr(
            brem     = brem, 
            block    = block, 
            is_mc    = is_mc,
            cmb      = MVAWp.from_str('0.99'),
            prc      = MVAWp.from_str('0.60'),
            q2bin    = q2bin,
            trigger  = trig, 
        )

        print(meas)
# -----------------------
