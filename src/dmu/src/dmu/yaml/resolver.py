'''
This module contains the YamlResolver class
'''

from typing import Any, Mapping

from dmu.logging.log_store import LogStore
from dmu.generic           import utilities as gut

# TODO: Improve detection of cycles
log=LogStore.add_logger('dmu:yaml:resolver')
# ----------------------
class Resolver:
    '''
    This class will:

    - Take a dictionary mapping simple types (int or str) to strings
    - The strings in the values will contain fields like {var} where `var`
      is a key
    - The instance will return the value for a given key, with all
      the variales resolved
    '''
    # ----------------------
    def __init__(self, cfg : Mapping[str|int,str]) -> None:
        '''
        Parameters
        -------------
        cfg: Dictionary like object with potentially unresolved, but resolvable fields
        '''
        self._cfg            = self._config_from_input(cfg=cfg)
        self._max_iterations = 20
    # ----------------------
    def _config_from_input(self, cfg : Mapping[str|int,str]) -> dict[str,str]:
        '''
        Parameters
        -------------
        cfg: Config as given by user

        Returns
        -------------
        Config after preprocessing
        '''
        cfg_rep : dict[str,str] = { str(key) : value for key, value in cfg.items()}
        if 'input' not in cfg_rep:
            return cfg_rep

        [package, fpath] = cfg_rep['input']
        cfg_ext = gut.load_conf(package=package, fpath=fpath)

        del cfg_rep['input']

        cfg_rep.update(cfg_ext)

        return cfg_rep
    # ----------------------
    def __contains__(self, item : str|int) -> bool:
        '''
        Parameters
        -------------
        item: Key of underlying dictionary
        '''

        return item in self._cfg
    # ----------------------
    def __getitem__(self, key : str|int) -> Any:
        '''
        Parameters
        -------------
        key: Key of dictionary for which value is needed

        Returns
        -------------
        Integer, float, string, etc
        '''
        key = str(key)

        if key not in self._cfg:
            raise KeyError(f'Cannot find {key}')

        expr = self._cfg[key]
        if not isinstance(expr, str):
            return expr

        if f'{{{key}}}' in expr:
            raise ValueError(f'Circular reference at first level for key: {key}')

        prev    = None
        counter = 0
        while prev != expr and counter < self._max_iterations:
            log.debug(f'Resolving: {expr}')

            prev     = expr
            counter += 1
            expr     = expr.format(**self._cfg)

        if counter == self._max_iterations:
            raise ValueError(f'Maximum number of itearations, {self._max_iterations} reached, circular reference is likely')

        return expr
# ----------------------
