'''
Script used to orchestrate plots made by the `cutflow` script
'''
import os
import json
import law

from typing        import Final
from pathlib       import Path
from functools     import cache
from law.parameter import Parameter
from omegaconf     import DictConfig, OmegaConf
from dmu.generic   import utilities as gut
from dmu           import LogStore

log=LogStore.add_logger('rx_orchestration:overlay_law')

_ANADIR: Final[Path]      = Path(os.environ['ANADIR'])
_KINDS : Final[list[str]] = [
    'psi2S_suppression',
    'block_quality', 
    'block_no_tail',
    'q2_prec_mva',
    'resolution',
    'tail_cut',
    'ecal_xy',
    'q2_cut',
    'brem',
    'npv']
# -------------------------------------
class OverlayTask(law.Task):
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
        cfg      = self._get_config()
        PLTDIR   = _ANADIR / f'plots/overlay/{cfg.args.config}'
        if cfg.args.brem == -1:
            brem = 'all'
        else:
            brem = f'{cfg.args.brem:03}'

        dir_path = PLTDIR / cfg.args.sample / cfg.args.trigger / cfg.args.q2bin / brem

        return [ law.LocalFileTarget(dir_path / name) for name in cfg.output ]
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        from rx_plotter_scripts.overlay import main as overlay

        cfg = self._get_config() 

        overlay(cfg=cfg.args)
# -------------------------------------
class WrapOverlay(law.WrapperTask):
    '''
    This class takes care of steering the workflow
    '''
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
            config = gut.load_conf(package='configs', fpath=f'rx_plots/overlay/{kind}.yaml')
    
            for args in config['args']:
                q2bin   = args['q2bin'  ]
                sample  = args['sample' ]
                trigger = args['trigger']
                brem    = args['brem'   ]

                cfg             = {}
                cfg['q2bin'   ] = q2bin 
                cfg['sample'  ] = sample
                cfg['trigger' ] = trigger
                cfg['config'  ] = kind 
                cfg['substr'  ] = None 
                cfg['brem'    ] = brem
                cfg['nthreads'] = 1 # Luigi will run in parallel anyway

                output   = OmegaConf.to_container(config.output, resolve=True)
                json_str = json.dumps({'args' : cfg, 'output' : output}) 
                l_cfg.append(json_str)
    
        return l_cfg 
    # --------------------------
    def requires(self):
        '''
        Defines the sets of tasks in the workflow
        '''
        l_settings = WrapOverlay.get_settings()
        for settings in l_settings:
            yield OverlayTask(config_string = settings)
# ----------------------
def main():
    l_settings  = WrapOverlay.get_settings()
    nworkers    = min(8, len(l_settings))

    law.run(argv=['WrapOverlay', '--workers', str(nworkers), '--log-level', 'INFO'])
# ----------------------
if __name__ == "__main__":
    main()
