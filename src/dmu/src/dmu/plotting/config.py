'''
Module holding configuration classes for plots
'''

import matplotlib.colors as mcolors

from pathlib   import Path
from typing    import Literal
from pydantic  import BaseModel, model_validator

# --------------------------------------
class LineConf(BaseModel):
    '''
    Class configuring lines in plots
    '''
    label : str
    ls    : Literal['-', '--', ':', '.-', '']
    c     : str 
    # ---------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'LineConf':
        if self.c not in mcolors.cnames:
            raise ValueError(f'Invalid color: {self.c}')

        return self
# --------------------------------------
class VLineConf(LineConf):
    '''
    Class configuring vertical lines in plots
    '''
    x : float
# --------------------------------------
class PlotConf(BaseModel):
    '''
    Class specifying how to plot a variable
    '''
    binning    : tuple[int,int,int]
    yscale     : Literal['linear', 'log'] 
    labels     : tuple[str,str]
    name       : str
    normalized : bool
    vline      : VLineConf
# --------------------------------------
class GenericConf(BaseModel):
    '''
    Class storing generic settings
    '''
    size : tuple[int,int]
# --------------------------------------
class Dataset(BaseModel):
    '''
    Class representing a source of data
    '''
    friends : dict[str,str]
# --------------------------------------
class DsetOverlayConf(BaseModel):
    '''
    Class controlling configuration of
    DsetOverlay
    '''
    datasets : dict[str,Dataset]
    general  : GenericConf
    saving   : Path
    plots    : dict[str,PlotConf]

