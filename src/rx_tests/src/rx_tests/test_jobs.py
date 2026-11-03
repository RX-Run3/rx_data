'''
Module holding TestJobs class
'''

import os
from pathlib  import Path
from rx_tests import TestConfig
from rx_tests import PackageConf

ANADIR = Path(os.environ['ANADIR'])
# --------------------
class TestJobs:
    '''
    Class meant to provide a dictionary with
    job names mapped to list of commands
    '''
    # --------------------
    def __init__(self, cfg : TestConfig):
        '''
        Parameters
        ---------------
        cfg: Configuration
        '''
        self._cfg = cfg
    # ----------------------
    def _cmd_from_cfg(
        self,
        group: int,
        test : str,
        cfg  : PackageConf) -> str:
        '''
        Parameters
        -------------
        cfg  : Config for package tests
        test : Name of test
        group: Index of group

        Returns
        -------------
        String representing basic pytest command
        '''
        out_path = ANADIR / self._cfg.output / f'{test}_{cfg.splits:03}_{group:03}.xml'

        val = f'pytest {cfg.path} --splits {cfg.splits} --group {group} --junitxml={out_path}'

        return val
    # --------------------
    def get_jobs(self) -> dict[str,list[str]]:
        '''
        Returns
        -----------------
        dictionary mapping job names to list of
        commands
        '''
        data : dict[str, list[str]] = dict()
        for test, cfg in self._cfg.projects.items():
            data[test] = [ self._cmd_from_cfg(cfg = cfg, group = group, test = test) for group in range(1, cfg.splits + 1) ]

        return data
# --------------------
