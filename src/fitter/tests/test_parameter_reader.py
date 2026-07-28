import os
import pytest

from typing    import Final
from pathlib   import Path
from fitter    import ParameterReader
from fitter    import MVAWp
from rx_common import Brem, Component, Project
from rx_common import Trigger 
from rx_common import Qsq 
from rx_common import Block
from dmu       import LogStore

log=LogStore.add_logger('fitter:test_parameter_reader')

_BREMS : Final[list[Brem     ]] = [Brem.one, Brem.two]
_COMPS : Final[list[Component]] = [Component.bpkpjpsiee, Component.data_24]
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize() -> None:
    LogStore.set_level('fitter:parameter_reader', 10)
# -----------------------
@pytest.mark.parametrize('comp' ,         _COMPS)
@pytest.mark.parametrize('brem' ,         _BREMS)
@pytest.mark.parametrize('block', Block.blocks())
def test_simple(
    comp  : Component,
    block : Block,
    brem  : Brem):
    '''
    Test simplest use of reader
    '''
    rdr  = ParameterReader(name = 'reso_no_dtf')
    meas = rdr(
        signal   = Component.bpkpjpsiee,
        brem     = brem, 
        block    = block, 
        comp     = comp,
        cmb      = MVAWp.from_str('0.99'),
        prc      = MVAWp.from_str('0.40'),
        project  = Project.rk,
        q2bin    = Qsq.jpsi,
        trigger  = Trigger.rk_ee_os, 
    )

    print(meas)
# -----------------------
@pytest.mark.parametrize('comp' ,         _COMPS)
@pytest.mark.parametrize('brem' ,         _BREMS)
@pytest.mark.parametrize('block', Block.blocks())
def test_pars_path(
    comp  : Component,
    block : Block, 
    brem  : Brem):
    '''
    Test context manager user to set path to parameters 
    '''
    name    = 'reso_no_dtf'
    ana_dir = Path(os.environ['ANADIR'])
    pars_path = ana_dir / f'fits/data/{name}/parameters.parquet'

    with ParameterReader.inputs_from(pars_path = pars_path):
        rdr  = ParameterReader(name = name)
        meas = rdr(
            brem     = brem, 
            block    = block, 
            comp     = comp,
            signal   = Component.bpkpjpsiee,
            cmb      = MVAWp.from_str('0.99'),
            prc      = MVAWp.from_str('0.40'),
            project  = Project.rk,
            q2bin    = Qsq.jpsi,
            trigger  = Trigger.rk_ee_os, 
        )

        print(meas)
# -----------------------
