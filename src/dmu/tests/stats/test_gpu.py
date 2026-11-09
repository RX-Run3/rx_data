'''
Tests for code in gpu.py
'''

from pytest_mock     import MockerFixture
from _pytest.logging import LogCaptureFixture
from dmu.stats       import check_for_gpu

# ----------------------
def test_check_for_gpu_available(mocker : MockerFixture, caplog : LogCaptureFixture) -> None:
    '''
    Test check_for_gpu when GPU is available
    '''
    mocker.patch('tensorflow.config.list_physical_devices', return_value=['GPU:0'])
    check_for_gpu()
    assert "GPU is available" in caplog.text
# ----------------------
def test_check_for_gpu_not_available(mocker : MockerFixture, caplog : LogCaptureFixture) -> None:
    '''
    Test check_for_gpu when GPU is not available
    '''
    mocker.patch('tensorflow.config.list_physical_devices', return_value=[])
    check_for_gpu()
    assert "GPU is not available" in caplog.text
# ----------------------
