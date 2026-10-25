'''
This script is meant to steer the classifier
'''
import os
import json
import argparse
from functools             import cache
from pathlib               import Path

import law
from law.parameter         import Parameter
from omegaconf             import DictConfig, OmegaConf
from dmu.generic           import utilities as gut
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('rx_orchestration:train_law')
# -------------------------------------
class TrainTask(law.Task):
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
        args     = cfg.args
        ANADIR   = os.environ['ANADIR']
        MVADIR   = Path(ANADIR) / 'mva' / args.project / args.kind / args.version / args.q2bin
        l_output = [ law.LocalFileTarget(MVADIR / name) for name in cfg.outputs ]

        nout = len(l_output)
        log.info(f'Using {nout} outputs')
        for output in l_output:
            log.debug(output)

        return l_output
    # -------------------------------------
    def run(self):
        '''
        Runs comparison
        '''
        from rx_classifier_scripts.train_classifier import main as runner

        cfg = self._get_config() 
        runner(cfg=cfg.args)
# -------------------------------------
class WrapTrain(law.WrapperTask):
    '''
    This class takes care of steering the workflow
    '''
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

        for args in cfg.args:
            args     = OmegaConf.to_container(args, resolve=True)
            json_str = json.dumps({'args' : args, 'outputs' : outputs}) 
            l_cfg.append(json_str)
    
        return l_cfg 
    # --------------------------
    def requires(self):
        '''
        Defines the sets of tasks in the workflow
        '''
        cfg = gut.load_conf(package='configs', fpath='rx_classifier/train.yaml')

        log.info(20 * '-')
        l_settings = WrapTrain.get_settings(cfg=cfg)
        for settings in l_settings:
            yield TrainTask(config_string = settings)
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to steer classifier training')
    parser.add_argument('-l', '--loglvl' , type=int, help='Logging level', default=20)
    args = parser.parse_args()

    LogStore.set_level('rx_orchestration:train_law', args.loglvl)
# ----------------------
def main():
    _parse_args()
    law.run(argv=['WrapTrain', '--workers', '8', '--log-level', 'INFO'])
# ----------------------
if __name__ == "__main__":
    main()
