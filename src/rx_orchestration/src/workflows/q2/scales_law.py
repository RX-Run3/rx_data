'''
This script is meant to steer the calculation of mass scales and resolutions 
'''
import os
import json
import argparse
import matplotlib
from functools             import cache
from pathlib               import Path
from importlib.resources   import files
from .dependencies         import Dependencies

import law
from law.parameter         import Parameter
import luigi
from omegaconf             import DictConfig, ListConfig, OmegaConf
from dmu.generic           import utilities as gut
from dmu.logging.log_store import LogStore

matplotlib.use('Agg')
log=LogStore.add_logger('rx_orchestration:q2_scales')
# -------------------------------------
class Fit(law.Task):
    config_string : str = Parameter() # type: ignore
    kind          : str = Parameter() # type: ignore
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

        self._cfg                     = cfg
        self._cfg['args']['kind']     = self.kind 
        self._cfg['args']['syst']     = 'nom' 
        self._cfg['args']['logl']     = 20 
        self._cfg['args']['skip_fit'] = False 

        return self._cfg
    # -------------------------------------
    def output(self) -> list[law.LocalFileTarget]:
        '''
        Returns
        ---------------
        Name of required output, built from ANADIR and config settings
        '''
        cfg     = self._get_config()
        args    = cfg.args

        ana_dir = Path(os.environ['ANADIR'])

        path_1  = f'q2/fits/{args.vers}/{args.kind}'
        path_2  = f'{args.proj}_{args.year}'
        path_3  = f'{args.brem}_{args.block}_{args.syst}'

        out_dir = ana_dir / path_1 / path_2 / path_3
        out_dir.mkdir(parents=True, exist_ok=True)

        l_output = [ law.LocalFileTarget(out_dir / name) for name in cfg.outputs ]

        nout = len(l_output)
        log.debug(f'Using {nout} outputs')
        for output in l_output:
            log.debug(output)

        return l_output
    # -------------------------------------
    def requires(self) -> law.Task | None:
        '''
        Defines the sets of tasks in the workflow
        '''
        if self.kind == 'dat':
            return Fit(config_string = self.config_string, kind='sim')
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        from rx_q2_scripts.get_q2_tables import main as runner

        cfg = self._get_config() 
        runner(args=cfg.args)
# -------------------------------------
class Fits(law.WrapperTask):
    '''
    This class takes care of steering the workflow
    '''
    vers : str = law.Parameter() # type: ignore
    # ----------------------
    @cache
    @staticmethod
    def get_settings(cfg : DictConfig) -> list[str]:
        '''
        Parameters
        --------------
        cfg : Dictionary with configuration

        Returns
        --------------
        List of JSON strings defining what each job will do
        '''
        l_cfg    = [] 
        outputs  = OmegaConf.to_container(cfg.outputs, resolve=True)

        for args in cfg.l_args:
            args     = OmegaConf.to_container(args, resolve=True)
            json_str = json.dumps({'args' : args, 'outputs' : outputs}) 
            l_cfg.append(json_str)
    
        return l_cfg 
    # --------------------------
    def requires(self):
        '''
        Defines the sets of tasks in the workflow
        '''
        cfg = gut.load_conf(package='configs', fpath='rx_q2/fits.yaml')
        for args in cfg.l_args:
            args['vers'] = self.vers

        log.info(20 * '-')
        l_settings = Fits.get_settings(cfg=cfg)

        return [ Fit(config_string = settings, kind='dat') for settings in l_settings ]
# -------------------------------------
class Scale(law.Task, Dependencies):
    '''
    This task calculates the scales for a given project
    '''
    args         : dict[str,str] = luigi.DictParameter(default={}) # type: ignore
    outputs      : list[str]     = luigi.ListParameter(default=[]) # type: ignore
    dependencies : tuple         = law.Parameter()                 # type: ignore
    vers         : str           = law.Parameter()                 # type: ignore
    # ----------------------
    def requires(self) -> law.Task:
        return Fits(vers = self.vers)
    # ----------------------
    def output(self) -> list[law.LocalFileTarget]:
        l_path    = [ law.LocalFileTarget(out_dir) for out_dir in self.outputs ]
        hash_path = law.LocalFileTarget(self.hash_path)
        l_path.append(hash_path)

        return l_path
    # ----------------------
    def run(self):
        from rx_q2_scripts.dump_q2_ratios import main as runner

        data         = { key : val for key, val in self.args.items() }
        args         = OmegaConf.create(data)
        args['vers'] = self.vers

        self._touch_hash()

        runner(args=args)
# -------------------------------------
class Scales(law.Task):
    '''
    Task in charge of calculating scales and resolutions
    from fit parameters
    '''
    combined_scales : list[str] = luigi.ListParameter(default=[]) # type: ignore
    vers            : str       = luigi.Parameter() # type: ignore
    # --------------------------------
    def _get_outputs(self, args : DictConfig, names : ListConfig) -> list[str]:
        '''
        Returns
        ------------
        List of paths to files produced by each Scales job, e.g. fitting parameters, plots, etc.
        '''
        ana_dir = os.environ['ANADIR']

        return [ f'{ana_dir}/q2/fits/{self.vers}/plots/{args.project}/{name}' for name in names ]
    # --------------------------------
    def output(self) -> list[law.LocalFileTarget]:
        '''
        Returns
        -------------
        List of path to JSON files with combined scales, e.g. /x/y/parameters_ee.json
        '''
        return [ law.LocalFileTarget(file_path) for file_path in self.combined_scales ]
    # --------------------------------
    def run(self):
        '''
        Run combination of scales produced by each of the `Scale` tasks
        '''
        from rx_q2 import cli

        cli.combine_scales(version=self.vers)
    # --------------------------------
    def requires(self) -> list[Scale]:
        cfg_path= files('rx_q2_data').joinpath('plots/scales.yaml')
        cfg     = gut.load_conf(package='configs', fpath='rx_q2/scales.yaml')

        l_scale = []
        for args in cfg.args:
            outputs = self._get_outputs(args=args, names=cfg.outputs)
            scl     = Scale(
                args        =args, 
                outputs     =outputs, 
                vers        =self.vers,
                dependencies=[cfg_path])

            l_scale.append(scl)

        return l_scale
# ----------------------
class Resolution(law.WrapperTask):
    '''
    Task uses to steer calculation of scales, fits, etc, needed to
    measure resolution and scale effects
    '''
    # --------------------------------
    def _get_outputs(self, vers : str, names : ListConfig) -> list[str]:
        '''
        Parameters
        -------------
        vers : Version of current resolution job
        names: Names of the files needed, i.e. parameters_ee.json

        Returns
        -------------
        List of paths to JSON files where combined scales should be
        '''
        ana_dir = os.environ['ANADIR']

        return [ f'{ana_dir}/q2/fits/{vers}/{name}' for name in names ]
    # --------------------------------
    def requires(self) -> Scales:
        '''
        Returns task meant to calculate combined mass scales
        '''
        cfg = gut.load_conf(package='configs', fpath='rx_q2/scales.yaml')

        combined_scales = self._get_outputs(vers=cfg.vers, names=cfg.scales)

        return Scales(combined_scales=combined_scales, vers=cfg.vers)
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to steer mass scales and resolutions measurements')
    parser.add_argument('-l', '--loglvl' , type=int, help='Logging level', default=20)
    args = parser.parse_args()

    LogStore.set_level('rx_orchestration:q2_scales', args.loglvl)
# ----------------------
def main():
    _parse_args()
    law.run(argv=['Resolution', '--workers', '8', '--log-level', 'INFO'])
# ----------------------
if __name__ == "__main__":
    main()
