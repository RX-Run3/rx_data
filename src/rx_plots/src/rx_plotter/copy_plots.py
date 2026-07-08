'''
Module holding CopyPlots class
'''
from pathlib     import Path
from pydantic    import BaseModel
from dmu.generic import utilities as gut

# -------------------------------------------------
class PlotCategory(BaseModel):
    '''
    Class representing kind of plots that needs to be copied
    '''
    paths      : dict[Path,Path]
# -------------------------------------------------
class CopyPlotsConf(BaseModel):
    '''
    Class configuring how plots will be copied
    '''
    extensions : list[str]
    categories : list[PlotCategory]
    # -------------------------------------------------
    @classmethod
    def from_name(cls, name : str) -> 'CopyPlotsConf':
        '''
        Parameters
        ----------------
        name: Name of file with configuration, e.g. fit_plots

        Return
        ----------------
        Instance of configuration
        '''
        data = gut.load_data(package = 'rx_plotter_data', fpath = f'copy/{name}.yaml')

        return cls(**data)
# -------------------------------------------------
class CopyPlots:
    '''
    Class meant to copy plots from a given set of directory paths to another
    '''
    # -------------------------------------------------
    def __init__(self, cfg : CopyPlotsConf):
        '''
        Parameters
        ----------------
        cfg: Config object
        '''
        self._cfg = cfg
    # -------------------------------------------------
    def run(self, dry_run : bool) -> None:
        '''
        Runs copy

        Parameters
        -----------------
        dry_run: If True will do everything but the actual copy of the files
        '''
    # -------------------------------------------------
    @classmethod
    def from_config_name(cls, name : str) -> 'CopyPlots':
        '''
        Parameters
        ----------------
        name: Name of config file

        Returns
        ----------------
        Instance of copy tool
        '''
        cfg = CopyPlotsConf.from_name(name = name)

        return cls(cfg = cfg)
# -------------------------------------------------
