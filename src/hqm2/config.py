from dmu                 import LogStore
from pathlib             import Path
from importlib.resources import files
from dmu.stats           import FitConf
from pydantic            import BaseModel
from rx_common           import Block, Trigger

log=LogStore.add_logger('rx_hqm:config')
#-------------------------------------------------------------------
class BinningConf(BaseModel, frozen = True):
    variable : str
    '''
    Name of variable to bin with
    '''
    bin      : int
    '''
    Index of bin
    '''
    cut      : str
    '''
    Expression defining cut
    '''
#-------------------------------------------------------------------
class Conf(BaseModel, frozen = True):
    binning : BinningConf | None
    fitting : FitConf
    # -----------------------------------------------
    @staticmethod
    def print_config(name) -> None:
        if not hasattr(Conf, name):
            log.error(f'Cannot find {name} in configuration')
            raise

        d_data = getattr(Conf, name)
        log.info(80 * '-')
        log.info(f'{"Setting":<30}{"Value":<50}')
        log.info(80 * '-')
        for key, val in d_data.items():
            log.info(f'{key:<30}{val:<50}')
    # -----------------------------------------------
    @staticmethod
    def make_path(
        kind    : str, 
        fname   : str,
        block   : Block, 
        trigger : Trigger) -> Path:
        '''
        Function will make a path and return it. 

        Parameters 
        -----------------
        kind   : Name of directory meant to sybolize what data will be stored there, e.g. fits, trfc
        fname  : Optional, file name, e.g. data.json
        Block  : E.g. block 1,...8 
        trigger: E.g. rk_ee_os 

        Returns
        -----------------
        Path to either file or directory
        '''
        if len(Conf.binning) == 0:
            binning = 'int'
        else:
            var     = Conf.binning['var']
            ibin    = Conf.binning['bin']
            binning = f'{var}_{ibin}'

        if trigger is not None:
            dir_path = files('hqm2_data').joinpath(f'{kind}/{binning}/{block}/{trigger}')
        else:
            dir_path = files('hqm2_data').joinpath(f'{kind}/{binning}/{block}')

        dir_path = Path(str(dir_path))
        dir_path.mkdir(parents = True, exist_ok = True)

        if fname is None:
            return dir_path

        return dir_path / fname 
#-------------------------------------------------------------------
