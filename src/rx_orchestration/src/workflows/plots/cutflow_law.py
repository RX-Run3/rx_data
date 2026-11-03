'''
Script used to orchestrate plots made by the `cutflow` script
'''
import os
import law
import json
import argparse

from dataclasses   import dataclass
from typing        import Final, cast
from pathlib       import Path
from functools     import cache
from law.parameter import Parameter
from dmu           import LogStore
from dmu.generic   import utilities as gut
from omegaconf     import DictConfig, OmegaConf

log=LogStore.add_logger('rx_orchestration:cutflow_law')

_KINDS   : Final[list[str]]     = ['cleanup', 'ss_shape', 'bdt', 'mass_shaping']
_CONFIGS : Final[dict[str,str]] = {
    'cleanup'     : 'cutflow_os.yaml',
    'ss_shape'    : 'cutflow_ss.yaml',
    'bdt'         : 'bdt.yaml',
    'mass_shaping': 'mass_shaping.yaml'}
# -------------------------------------
@dataclass(frozen = True)
class Conf:
    '''
    Class used to configure current script
    '''
    dry_run : bool
    nproc   : int
# -------------------------------------
class CutflowTask(law.Task):
    config_string : str = Parameter() # type: ignore
    # -------------------------------------
    def _get_config(self) -> DictConfig:
        '''
        Returns
        --------------------
        Transform JSON string `config_string` with configuration to DictConfig
        and returns it
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
        cfg    = self._get_config()
        ANADIR = os.environ['ANADIR']
        PLTDIR = Path(ANADIR) / f'plots/cutflow/{cfg.args.config}'

        dir_path = PLTDIR / f'{cfg.args.sample}_{cfg.args.trigger}_{cfg.args.q2bin}'

        return [ law.LocalFileTarget(dir_path / name) for name in cfg.output ]
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        from rx_plotter_scripts.cutflow import main as cutflow

        cfg  = self._get_config()
        obj  = OmegaConf.to_object(cfg = cfg)
        obj  = cast(dict[str,dict[str,str]], obj)

        cutflow(args = obj['args'])
# -------------------------------------
class WrapCutflow(law.WrapperTask):
    '''
    This class takes care of steering the workflow
    '''
    @cache
    @staticmethod
    # ----------------------
    def _get_config(kind : str) -> DictConfig:
        '''
        Parameters
        -------------
        kind: Type of check, e.g. cleanup

        Returns
        -------------
        Dictionary with configuration, from YAML file
        '''
        fname  = _CONFIGS.get(kind)
        if fname is None:
            raise ValueError(f'No config found for: {kind}')

        config = gut.load_conf(package='configs', fpath=f'rx_plots/{fname}')

        return config
    # ----------------------
    @cache
    @staticmethod
    def get_settings() -> list[str]:
        '''
        Returns
        --------------
        List of JSON strings defining what each job will do
        '''
        l_cfg = []
        for kind in _KINDS:
            config = WrapCutflow._get_config(kind=kind)

            for args in config['args']:
                q2bin   = args['q2bin'  ]
                sample  = args['sample' ]
                trigger = args['trigger']

                cfg             = {}
                cfg['q2bin'   ] = q2bin
                cfg['sample'  ] = sample
                cfg['trigger' ] = trigger
                cfg['config'  ] = kind

                output   = OmegaConf.to_container(config.output, resolve=True)
                json_str = json.dumps({'args' : cfg, 'output' : output})
                l_cfg.append(json_str)

        return l_cfg
    # --------------------------
    def requires(self):
        '''
        Defines the sets of tasks in the workflow
        '''
        l_settings = WrapCutflow.get_settings()
        for settings in l_settings:
            yield CutflowTask(config_string = settings)
# ----------------------
def _parse_args() -> Conf:
    '''
    Parses arguments passed by user

    Returns
    --------------
    Instance of configuration data class, built from arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to steer workflow for cutflows with LAW')
    parser.add_argument('-d', '--dry_run' , action = 'store_true', help='If used will do dry run')
    parser.add_argument('-n', '--nproc'   , type   = int         , help='Number of workers', required = True)
    args = parser.parse_args()

    return Conf(
        nproc   = args.nproc,
        dry_run = args.dry_run)
# ----------------------
def main():
    l_settings = WrapCutflow.get_settings()
    cfg        = _parse_args()
    nworkers   = min(cfg.nproc, len(l_settings))

    if cfg.dry_run:
        law.run(argv=['WrapCutflow', '--workers', str(nworkers), '--log-level', 'INFO', '--print-status', '-1'])
    else:
        law.run(argv=['WrapCutflow', '--workers', str(nworkers), '--log-level', 'INFO'])
# ----------------------
if __name__ == "__main__":
    main()
