'''
This module will configure pytest tests
'''
import pytest

pytest_plugins = ['patch_classes']
# -----------------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action = "store_true",
        default= False,
        help   = "If used, it will turn on slow tests")
# -----------------------------------
@pytest.fixture
def slow_mode(request):
    """Returns True if --runslow is passed, False otherwise."""
    return request.config.getoption("--slow")
# -----------------------------------

