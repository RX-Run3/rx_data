'''
Class holding FitParametersConf and classes needed by it
'''
import yaml

from pydantic  import BaseModel, Field, RootModel
from rx_common import Project, Qsq, Trigger, Brem

# ----------------------
class Axis(BaseModel):
    '''
    Class meant to represent an axis
    '''
    name  : str
    values: list[str|int]
# ----------------------
class Info(BaseModel):
    '''
    Class meant to hold metadata type of information
    '''
    trigger : Trigger
    project : Project
    q2bin   : Qsq
    brem    : Brem
# ----------------------
class GraphConf(BaseModel):
    '''
    Class meant to represent config for a single graph
    '''
    info  : Info
    error : str
    label : str
    color : str
# ----------------------
class PlotConf(BaseModel):
    '''
    Class representing configurations for plots that
    will go in a canvas
    '''
    yrange : list[float|None] = Field(min_length=2, max_length=2)
    size   : list[int  ]      = Field(min_length=2, max_length=2)
    xlabel : str
    ylabel : str
    title  : str
    graphs : dict[str,GraphConf]
    xaxis  : Axis
# ----------------------
class FitParametersConf(RootModel):
    '''
    Class meant to hold parameters needed for plotting
    '''
    root : dict[str,PlotConf]
    # -------------------------
    def __str__(self):
        data = self.model_dump(mode='deep')

        return yaml.dump(data)
    # -------------------------
    def __repr__(self):
        return self.__str__()
