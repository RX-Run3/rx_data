'''
Script used to orchestrate plots made by the `plot_2d` script
'''
import os
import json
import law

from pathlib       import Path
from functools     import cache
from typing        import Final
from law.parameter import Parameter
from omegaconf     import DictConfig, OmegaConf
from dmu.generic   import utilities as gut
from dmu           import LogStore

log=LogStore.add_logger('rx_orchestration:plot_2d_law')
_ANADIR : Final[Path]      = Path(os.environ['ANADIR'])
_KINDS  : Final[list[str]] = ['mass_q2', 'cmb_prc']
# -------------------------------------
class Plot2DTask(law.Task):
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
        PLTDIR   = _ANADIR / f'plots/2d/{cfg.args.config}'
        dir_path = PLTDIR / cfg.args.sample / cfg.args.trigger

        return [ law.LocalFileTarget(dir_path / name) for name in cfg.output ]
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        from rx_plotter_scripts.plot_2d import main as plot_2d 

        cfg = self._get_config() 

        plot_2d(cfg=cfg.args)
# -------------------------------------
class WrapPlot2D(law.WrapperTask):
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
        kind: Type of check, e.g. block quality 

        Returns
        -------------
        Dictionary with configuration, from YAML file
        '''
        if   kind in _KINDS:
            fname = f'{kind}.yaml'
        else:
            raise ValueError(f'Invalid kind of plot: {kind}')
        
        config = gut.load_conf(package='configs', fpath=f'rx_plots/2d/{fname}')

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
            config = WrapPlot2D._get_config(kind=kind)

            for args in config['args']:
                sample  = args['sample' ]
                trigger = args['trigger']
                q2bin   = args['q2bin'  ]

                cfg             = {}
                cfg['sample'  ] = sample
                cfg['trigger' ] = trigger
                cfg['q2bin'   ] = q2bin 
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
        l_settings = WrapPlot2D.get_settings()
        for settings in l_settings:
            yield Plot2DTask(config_string = settings)
# ----------------------
def main():
    l_settings  = WrapPlot2D.get_settings()
    nworkers    = min(8, len(l_settings))

    law.run(argv=['WrapPlot2D', '--workers', str(nworkers), '--log-level', 'INFO'])
# ----------------------
if __name__ == "__main__":
    main()
