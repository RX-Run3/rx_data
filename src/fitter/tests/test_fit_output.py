'''
Tests for FitOutput class
'''
import pytest

from pathlib   import Path
from typing    import Final
from rx_common import Component
from fitter    import FitOutput
from dmu       import LogStore

_PATHS : Final[list[str]] = [
    './990_700_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    './990_700_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/data_24/fit/brem_xx1_brem_xx2/brem_x12/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/bpkppsi2ee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rk/ee/psi2/bpkppsi2ee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/mm/jpsi/bskstjpsimm/fit/brem_xx0/brem_xx0/parameters.json',
    './990_700_b3/reso/rkst/mm/jpsi/data_24/fit/brem_xx0/brem_xx0/parameters.json',
    './990_700_b3/reso/rkst/mm/jpsi/bdkstkpijpsimm/fit/brem_xx0/brem_xx0/parameters.json',
    './990_700_b3/reso/rkst/mm/psi2/data_24/fit/brem_xx0/brem_xx0/parameters.json',
    './990_700_b3/reso/rkst/mm/psi2/bdkstkpipsi2mm/fit/brem_xx0/brem_xx0/parameters.json',
    './990_700_b3/reso/rkst/mm/psi2/bskstpsi2mm/fit/brem_xx0/brem_xx0/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_x12/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/bskstjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/bskstjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/bdkstkpijpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/jpsi/bdkstkpijpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/data_24/fit/brem_xx1_brem_xx2/brem_x12/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bdkstkpipsi2ee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bdkstkpipsi2ee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bskstjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bskstjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bskstpsi2ee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bskstpsi2ee/fit/brem_xx1/brem_xx1/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bdkstkpijpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    './990_700_b3/reso/rkst/ee/psi2/bdkstkpijpsiee/fit/brem_xx1/brem_xx1/parameters.json',
]

log=LogStore.add_logger('test_fit_output')

@pytest.mark.parametrize('path', _PATHS[:1])
def test_simple(path : Path):
    obj = FitOutput(path = path)
    assert obj.signal  in Component 

    log.info(f'Output is validity {obj.is_valid} for {obj.signal}')
