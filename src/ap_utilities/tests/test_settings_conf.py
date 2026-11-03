'''
Module used to test SettingsConf
'''
import pytest

from ap_utilities import SettingsConf
from ap_utilities import SamplesConf
from dmu.generic  import utilities as gut

# ---------------------------------------------
@pytest.mark.parametrize('settings', ['2024_sim10g', '2024_sim10f', '2024_sim10d'])
def test_settings_conf(settings : str):
    data       = gut.load_data(
        package= 'ap_utilities_data',
        fpath  = f'samples/{settings}.yaml')
    data.pop('settings_common', None)

    _ = SettingsConf(root = data)
# ---------------------------------------------
@pytest.mark.parametrize('analyses', ['by_priority'])
def test_samples_conf(analyses : str):
    data       = gut.load_data(
        package= 'ap_utilities_data',
        fpath  = f'analyses/{analyses}.yaml')
    data.pop('all', None)

    _ = SamplesConf(root = data)
