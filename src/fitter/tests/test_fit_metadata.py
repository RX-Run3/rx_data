'''
Module with tests for FitMetadata class
'''

import pytest
from pathlib import Path

from rx_common import Component
from fitter    import FitMetadata

_DATA_PATHS = [
    'reso_no_dtf/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/950_500_b8/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/950_500_b8/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/990_600_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/990_600_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/950_600_b7/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/950_600_b7/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/950_700_b2/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/950_700_b2/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/950_500_b5/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/950_500_b5/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
]

_SIGN_PATHS = [
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b4/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx1_b6/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b2/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b5/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b8/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx1_b3/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx1_b7/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx1_b5/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx1_b4/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b3/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b1/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx1_b8/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b7/parameters.json',
    'conv_150/500-800_400_all/rare/rk/ee/low/bpkpee/fit/brem_x12/brem_xx2_b6/parameters.json',
]
# --------------------------------------------------
@pytest.mark.parametrize('path', _DATA_PATHS)
def test_from_data_path(path : Path):
    path = Path(path)
    comp = Component.data_24

    FitMetadata.from_pars_path(
        path = path,
        comp = comp)
# --------------------------------------------------
@pytest.mark.parametrize('path', _SIGN_PATHS)
def test_from_sign_path(path : Path):
    path = Path(path)
    comp = Component.bpkpee

    FitMetadata.from_pars_path(
        path = path,
        comp = comp)
# --------------------------------------------------
