import os
import pytest

from typing    import Final
from pathlib   import Path
from fitter    import ParameterReader
from rx_common import MVAWp
from rx_common import Brem, Component
from rx_common import Trigger
from rx_common import Qsq
from rx_common import Block
from dmu       import LogStore

log=LogStore.add_logger('fitter:test_parameter_reader')

_BREMS  : Final[list[Brem]] = [Brem.zero, Brem.one, Brem.two]
_Q2BINS : Final[list[Qsq ]] = [Qsq.jpsi, Qsq.psi2]
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize() -> None:
    LogStore.set_level('fitter:parameter_reader', 10)
# -----------------------
def test_data():
    '''
    Test reader with data
    '''
    comp = Component.data_24
    name = 'reso_dtf-latest' # 'reso_no_dtf'
    rdr  = ParameterReader(name = name)
    meas = rdr(
        comp     = comp,
        brem     = Brem.brx12,
        block    = Block(value = 1),
        cmb      = MVAWp.from_str('0.99'),
        prc      = MVAWp.from_str('0.60'),
        q2bin    = Qsq.jpsi,
        trigger  = Trigger.rk_ee_os,
    )

    print(meas)
# -----------------------
@pytest.mark.parametrize('q2bin',        _Q2BINS)
@pytest.mark.parametrize('brem' ,         _BREMS)
@pytest.mark.parametrize('block', Block.blocks())
def test_all(
    q2bin : Qsq,
    block : Block,
    brem  : Brem):
    '''
    Test reader with initializer
    '''
    if brem == Brem.zero:
        trig = Trigger.rk_mm_os
        comp = Component.bpkpjpsimm if q2bin == Qsq.jpsi else Component.bpkppsi2mm
    else:
        trig = Trigger.rk_ee_os
        comp = Component.bpkpjpsiee if q2bin == Qsq.jpsi else Component.bpkppsi2ee

    name = 'reso_dtf-latest' # 'reso_no_dtf'
    rdr  = ParameterReader(name = name)
    res  = rdr(
        comp     = comp,
        brem     = brem,
        block    = block,
        cmb      = MVAWp.from_str('0.99'),
        prc      = MVAWp.from_str('0.60'),
        q2bin    = q2bin,
        trigger  = trig,
    )

    print(res)
# -----------------------
@pytest.mark.parametrize('q2bin',        _Q2BINS)
@pytest.mark.parametrize('brem' ,         _BREMS)
@pytest.mark.parametrize('block', Block.blocks())
def test_pars_path(
    q2bin : Qsq,
    block : Block,
    brem  : Brem):
    '''
    Test context manager user to set path to parameters
    '''
    if brem == Brem.zero:
        trig = Trigger.rk_mm_os
        comp = Component.bpkpjpsimm if q2bin == Qsq.jpsi else Component.bpkppsi2mm
    else:
        trig = Trigger.rk_ee_os
        comp = Component.bpkpjpsiee if q2bin == Qsq.jpsi else Component.bpkppsi2ee

    name      = 'reso_dtf-latest' # 'reso_no_dtf'
    ana_dir   = Path(os.environ['ANADIR'])
    pars_path = ana_dir / f'fits/data/{name}/fit_summary.json'

    with ParameterReader.inputs_from(pars_path = pars_path):
        rdr = ParameterReader()
        res = rdr(
            comp    = comp,
            brem    = brem,
            block   = block,
            cmb     = MVAWp.from_str('0.99'),
            prc     = MVAWp.from_str('0.60'),
            q2bin   = q2bin,
            trigger = trig,
        )

    print(res)
# -----------------------
