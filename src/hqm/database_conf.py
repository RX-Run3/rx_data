'''
Module holding DatabaseConf class
'''

import os
from pathlib      import Path
from pydantic     import BaseModel
from dmu.generic  import utilities as gut
from rx_common    import Cuts, Trigger, Component

# ----------------------
class DatabaseConf(BaseModel, frozen = True):
    '''
    Class meant to hold configuration for DatabaseBuilder
    '''
    selection: dict[Cuts, str]
    columns  : list[str]
    db_dir   : Path
    # ----------------------
    def get_path(self, comp : Component, trig : Trigger) -> Path:
        '''
        Parameters
        --------------
        comp: Denotes sample where path will go/be read
        trig: Hlt2 trigger

        Returns
        --------------
        Path to parquet file with data
        '''
        anadir = Path(os.environ['ANADIR'])
        path   = anadir / self.db_dir / f'{comp}_{trig}' / 'data.parquet'
        path.parent.mkdir(parents = True, exist_ok = True)

        return path
    # ----------------------
    def has_output(self, comp : Component,trig : Trigger) -> bool:
        '''
        True if an output is already present
        '''
        path = self.get_path(comp = comp, trig = trig)

        return path.exists()
    # ----------------------
    @classmethod
    def load(cls) -> 'DatabaseConf':
        data = gut.load_data(package = 'hqm_data', fpath = 'config/database_builder.yaml')

        return cls(**data)
# ----------------------
