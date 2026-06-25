'''
Module holding configuration classes for plots
'''

import matplotlib.colors as mcolors

from omegaconf import OmegaConf
from pathlib   import Path
from typing    import Literal
from pydantic  import BaseModel, model_validator

LineStyles = Literal['-', '--', ':', '.-', '']
HistTypes  = Literal['step', 'fill', 'bar', 'barstep', 'band']
# --------------------------------------
class HistConf(BaseModel):
    '''
    Class meant to hold configuration to
    style plots of histograms
    '''
    linestyle: LineStyles
    histtype : HistTypes
# --------------------------------------
class SavingConf(BaseModel):
    '''
    Class holding configuration needed to save plots
    '''
    plt_dir : Path
# --------------------------------------
class LineConf(BaseModel):
    '''
    Class configuring lines in plots
    '''
    label     : str
    linestyle : LineStyles 
    color     : str 
    # ---------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'LineConf':
        if self.color not in mcolors.cnames:
            raise ValueError(f'Invalid color: {self.color}')

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
    styling    : dict[str,HistConf]
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
class OverlayConf(BaseModel):
    '''
    Class holding configuration for overlays
    of variables 
    '''
    general  : GenericConf
    saving   : SavingConf 
    plots    : dict[str,PlotConf]
    # --------------------------------------
    def copy_cfg(self, suffix : str) -> 'OverlayConf':
        '''
        Parameters
        ----------------
        suffix: Used for naming to distinguish this config

        Returns
        ----------------
        Copy of current object with prefix wherever it makes sense, e.g. paths
        '''
        plt_dir    = str(self.saving.plt_dir)
        new_plt_dir= plt_dir.replace('.png', f'_{suffix}.png')
        new_saving = self.saving.model_copy(update = {'plt_dir' : new_plt_dir})

        return self.model_copy(update = {'saving' : new_saving})
    # --------------------------------------
    @property
    def as_dictconfig(self):
        data = self.model_dump()
        return OmegaConf.create(data)
# --------------------------------------
class DsetOverlayConf(OverlayConf):
    '''
    Class controlling configuration of
    DsetOverlay
    '''
    datasets : dict[str,Dataset]
# --------------------------------------
