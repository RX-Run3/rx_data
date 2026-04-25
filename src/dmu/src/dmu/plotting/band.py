'''
Module containing BandPlotter class
'''
import pandas as pnd
from pydantic import BaseModel

# ---------------------------------------
class Style(BaseModel):
    '''
    Class meant to configure styling of plot
    '''
    yrange   : tuple[float,float]
    xrotation: int 
    alpha    : float
    color    : str
# ---------------------------------------
class BandPlotterConf(BaseModel):
    '''
    Configuration needed for BandPlotter
    '''
# ---------------------------------------
class BandPlotter:
    '''
    Class meant to plot bands representing quantities
    with error bands
    '''
    # ----------------------------
    def __init__(
        self, 
        cfg : BandPlotterConf, 
        df  : pnd.DataFrame):
        '''
        Parameter
        ------------
        cfg: Configuration object
        df : DataFame with input data to plot
        '''
        self._cfg = cfg
        self._df  = df
    # ----------------------------
    def plot(self) -> None:
        '''
        Runs plotting
        '''
# ---------------------------------------
