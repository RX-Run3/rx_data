'''
Script used to orchestrate plots made by different scripts
meant to do checks, e.g. efficiency vs q2
'''
import os
import json
import law
import importlib

from pathlib               import Path
from functools             import cache
from typing                import Final
from law.parameter         import Parameter
from omegaconf             import DictConfig, OmegaConf
from dmu.generic           import utilities as gut
from dmu                   import LogStore

log=LogStore.add_logger('rx_orchestration:checks_law')

_KIND_TO_MODULE : Final[dict[str,str]] = {
    'efficiency_vs_q2': 'rx_plotter_scripts.efficiency_vs_q2',
    'validate_nopid'  : 'rx_plotter_scripts.validate_nopid',
    'leakage'         : 'rx_plotter_scripts.leakage',
    'high_q2cut'      : 'rx_plotter_scripts.high_q2cut',
}

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# -------------------------------------
class ChecksTask(law.Task):
    config_string : str = Parameter() # type: ignore
    kind          : str = Parameter() # type: ignore
    # -------------------------------------
    def _get_config(self) -> DictConfig:
        '''
        Returns
        --------------------
        Transform JSON string `config_string` with configuration to 
        DictConfig with arguments and outputs
        '''
        if hasattr(self, '_cfg'):
            return self._cfg

        if not isinstance(self.config_string, str):
            raise ValueError('Configuration string not a string')

        cfg = OmegaConf.create(self.config_string)
        if not isinstance(cfg, DictConfig):
            raise ValueError('cfg not a DictConfig')

        self._cfg = cfg

        return self._cfg
    # -------------------------------------
    def output(self) -> list[law.LocalFileTarget]:
        '''
        Returns
        ---------------
        Name of required output, built from ANADIR and config settings
        '''
        cfg     = self._get_config()
        plt_dir = _ANADIR / f'plots/checks/{self.kind}'

        if   self.kind == 'efficiency_vs_q2':
            dir_path = plt_dir / f'{cfg.args.component}_{cfg.args.trigger}'
        elif self.kind == 'high_q2cut':
            dir_path = plt_dir / f'{cfg.args.component}/{cfg.args.run}'
        elif self.kind == 'leakage':
            dir_path = plt_dir / f'{cfg.args.component}_{cfg.args.trigger}'
        elif self.kind in ['validate_nopid']:
            dir_path = plt_dir 
        else:
            raise ValueError(f'Invalid kind: {self.kind}')

        l_output = [ law.LocalFileTarget(dir_path / name) for name in cfg.outputs ]

        nout = len(l_output)
        log.info(f'Using {nout} outputs for {self.kind}')

        return l_output
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        if self.kind not in _KIND_TO_MODULE: 
            raise ValueError(f'Invalid kind: {self.kind}')

        module = importlib.import_module(_KIND_TO_MODULE[self.kind])
        runner = module.main

        cfg  = self._get_config() 
        args = OmegaConf.to_object(cfg.args)
        runner(args=args)
# -------------------------------------
class WrapChecks(law.WrapperTask):
    '''
    This class takes care of steering the workflow
    '''
    # ----------------------
    @cache
    @staticmethod
    def get_settings(cfg_full : DictConfig, kind : str) -> list[str]:
        '''
        Parameters
        --------------
        kind: Type of check, e.g. efficiency_vs_q2

        Returns
        --------------
        List of JSON strings defining what each job will do
        '''
        l_cfg    = [] 
        cfg_kind = cfg_full[kind]
        outputs  = OmegaConf.to_container(cfg_kind.outputs, resolve=True)

        for args in cfg_kind.args:
            args_dict= OmegaConf.to_container(args, resolve=True)
            json_str = json.dumps({'args' : args_dict, 'outputs' : outputs}) 
            l_cfg.append(json_str)
    
        return l_cfg 
    # --------------------------
    def requires(self):
        '''
        Defines the sets of tasks in the workflow
        '''
        cfg = gut.load_conf(package='configs', fpath='rx_plots/checks.yaml')

        log.info(20 * '-')
        for kind in _KIND_TO_MODULE: 
            log.info(f'Running: {kind}')
            l_settings = WrapChecks.get_settings(cfg_full=cfg, kind=kind)
            for settings in l_settings:
                yield ChecksTask(config_string = settings, kind = kind)
# ----------------------
def main():
    law.run(argv=['WrapChecks', '--workers', '8', '--log-level', 'INFO'])
# ----------------------
if __name__ == "__main__":
    main()
