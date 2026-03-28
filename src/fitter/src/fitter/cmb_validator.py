
from pydantic    import BaseModel
from functools   import cached_property
from dmu.stats   import FitConf
from dmu.generic import utilities as gut

from dmu import LogStore

log=LogStore.add_logger('fitter:cmb_validator')
# ----------------------
class CmbValidatorConf(BaseModel):
    '''
    Configuration needed to validate
    combinatorial model
    '''
    sel : str
    cut : str
    fit : str
    # ----------------------
    @cached_property
    def selection(self) -> dict[str,str]:
        '''
        Dictionary with selection needed to get dataset
        '''
        key  = self.sel
        data = gut.load_data(package = 'fitter_data', fpath = 'combinatorial/selections.yaml')
        if self.sel not in data:
            for val in data:
                log.error(f'\"{val}\"')
            raise ValueError(f'Cutflow \"{key}\" not found in config')

        log.debug(f'Picking selection: {self.sel}')

        return data[self.sel] 
    # ----------------------
    @cached_property
    def cutflow(self) -> dict[str,str]:
        '''
        Dictionary with cutflow to study
        '''
        key = self.cut

        data = gut.load_data(package = 'fitter_data', fpath = 'combinatorial/cutflows.yaml')
        if key not in data:
            for val in data:
                log.error(f'\"{val}\"')
            raise ValueError(f'Cutflow \"{key}\" not found in config')

        log.debug(f'Picking cutflow: \"{key}\"')

        return data[key] 
    # ----------------------
    @cached_property
    def fit_cfg(self) -> FitConf:
        '''
        Dictionary with cutflow to study
        '''
        key = self.fit

        data = gut.load_data(package = 'fitter_data', fpath = 'combinatorial/fits.yaml')
        if key not in data:
            for val in data:
                log.error(f'\"{val}\"')
            raise ValueError(f'Fit config \"{key}\" not found')

        log.debug(f'Picking fit config: \"{key}\"')

        return FitConf(**data[key])
# ----------------------
class CmbValidator:
    '''
    Class meant to validate combinatorial model
    '''
    # ---------------------------
    def __init__(self, cfg : CmbValidatorConf):
        '''
        Parameters
        ----------------
        cfg: Configuration needed for fits, etc
        '''
        self._cfg = cfg
    # ---------------------------
    def run(self) -> None:
        '''
        Runs validation
        '''
# ---------------------------
