'''
Module with tests for TestConfig class
'''

from rx_tests import TestConfig

# ----------------------
def test_from_package():
    '''
    Test building config for testing from
    name of project and config file
    '''
    cfg = TestConfig.from_package(
        package   = 'rx_tests_data',
        file_path = 'config.yaml')

    assert 'ap_utilities'          in cfg.projects
    assert cfg.projects.ap_utilities.splits == 1
# ----------------------
def test_filter():
    '''
    Test filtering out all projects but one
    '''
    cfg = TestConfig.from_package(
        package   = 'rx_tests_data',
        file_path = 'config.yaml')

    cfg = cfg.filter(project = 'ap_utilities')

    assert len(cfg.projects.root) == 1
    assert 'ap_utilities'          in cfg.projects
    assert cfg.projects.ap_utilities.splits == 1
# ----------------------
