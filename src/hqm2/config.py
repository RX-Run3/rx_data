import os

from log_store           import log_store
from importlib.resources import files

log=log_store.add_logger('rx_hqm2:config')
#-------------------------------------------------------------------
class config:
    binning=dict()

    @staticmethod
    def print_config(name):
        if not hasattr(config, name):
            log.error(f'Cannot find {name} in configuration')
            raise

        d_data = getattr(config, name)
        log.info(80 * '-')
        log.info(f'{"Setting":<30}{"Value":<50}')
        log.info(80 * '-')
        for key, val in d_data.items():
            log.info(f'{key:<30}{val:<50}')

    @staticmethod
    def make_data_path(kind=None, dset=None, dname=None, fname=None):
        '''
        Function will make a path and return it. 

        Parameters 
        -----------------
        kind  (str): Name of directory meant to sybolize what data will be stored there, e.g. fits, trfc
        dset  (str): Year, e.g. r1, r2p1
        dname (str): Optional, descriptive name for kind of data stored, e.g. ctrl_ETOS
        fname (str): Optional, file name, e.g. data.json

        Returns
        -----------------
        string holding path to either file or directory
        '''
        try:
            var     = config.binning['var']
            ibin    = config.binning['bin']
            binning = f'{var}_{ibin}'
        except KeyError:
            binning = 'int'

        if dname is not None:
            dir_path = files('hqm2_data').joinpath(f'{kind}/{binning}/{dset}/{dname}')
        else:
            dir_path = files('hqm2_data').joinpath(f'{kind}/{binning}/{dset}')

        dir_path = str(dir_path)
        os.makedirs(dir_path, exist_ok=True)

        if fname is None:
            return dir_path

        return f'{dir_path}/{fname}'
#-------------------------------------------------------------------
