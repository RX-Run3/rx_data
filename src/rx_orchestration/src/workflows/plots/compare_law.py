'''
This script is meant to run the orchestration of comparison plots with
Luigi Analysis Workflow
'''
import os
import law
import json

from typing        import Final
from pathlib       import Path
from law.parameter import Parameter
from omegaconf     import DictConfig, OmegaConf
from dmu.generic   import utilities as gut
from dmu           import LogStore

log=LogStore.add_logger('rx_orchestration:compare_law')
_ANADIR : Final[Path]      = Path(os.environ['ANADIR'])
_BLOCKS : Final[list[int]] = [1, 2, 3, 4, 5, 6, 7, 8]
_BREMS  : Final[list[int]] = [-1, 1, 2]
_KINDS  : Final[list[str]] = ['resolution'] #, 'smear']
_MVAS   : Final[list[int]] = [0, 1]
# -------------------------------------
class CompareTask(law.Task):
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
        PLTDIR = _ANADIR / f'plots/comparison/{cfg.args.config}'
        names  = cfg.output[cfg.args.config]

        mva_name = 'drop_mva' if cfg.args.mva  == 0  else 'with_mva'
        brem_name= 'all'      if cfg.args.brem == -1 else cfg.args.brem
        dir_path = PLTDIR / f'{cfg.args.sample}/{cfg.args.trigger}/{cfg.args.q2_bin}/{brem_name}_{cfg.args.block}/{mva_name}'

        return [ law.LocalFileTarget(dir_path / name) for name in names ]
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        from rx_plotter_scripts.compare import main as compare

        cfg = self._get_config()

        compare(settings=cfg.args)
# -------------------------------------
class WrapCompare(law.WrapperTask):
    '''
    This class takes care of steering the workflow
    '''
    def _get_settings(self) -> list[str]:
        '''
        Returns
        --------------
        List of JSON strings defining what each job will do
        '''
        config = gut.load_conf(package='configs', fpath='rx_plots/compare.yaml')

        l_cfg = []
        for args in config['args']:
            q2bin   = args['q2_bin' ]
            sample  = args['sample' ]
            trigger = args['trigger']

            for block in _BLOCKS:
                for kind in _KINDS:
                    for brem in _BREMS:
                        for mva in _MVAS:
                            cfg            = {}
                            cfg['q2_bin' ] = q2bin
                            cfg['sample' ] = sample
                            cfg['trigger'] = trigger
                            cfg['config' ] = kind
                            cfg['substr' ] = None
                            cfg['brem'   ] = brem
                            cfg['block'  ] = block
                            cfg['mva'    ] = mva
                            cfg['emulate'] = 1

                            output   = OmegaConf.to_container(config.output, resolve=True)
                            json_str = json.dumps({'args' : cfg, 'output' : output})
                            l_cfg.append(json_str)
        ntask = len(l_cfg)
        log.info(f'Found {ntask} tasks')

        return l_cfg
    # --------------------------
    def requires(self):
        '''
        Defines the sets of tasks in the workflow
        '''
        l_settings = self._get_settings()
        for settings in l_settings:
            yield CompareTask(config_string = settings)
# -------------------------------------
def main():
    law.run(argv=['WrapCompare', '--workers', '8'])
# -------------------------------------
if __name__ == "__main__":
    main()
