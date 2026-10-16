'''
Module holding ZFitPlotterConf
'''
from typing    import Self
from pydantic  import BaseModel, Field

#----------------------------------------
class ZFitPlotterConf(BaseModel, frozen = True):
    '''
    Class meant to hold configuration for ZFitPlotter
    '''
    nbins           : int
    stacked         : bool
    plot_components : list[str]                 = Field(default_factory=list)
    plot_range      : tuple[float,float] | None = None
    ext_text        : str                       = ''
    title           : str | None                = None
    skip_pulls      : bool                      = False
    d_leg           : dict[str,str]             = Field(default_factory=dict)
    # ---------------------------
    @classmethod
    def default(cls, stacked : bool = True) -> Self:
        '''
        Returns default instance of current class
        '''
        return cls(
            nbins           = 50,
            plot_components = [],
            stacked         = stacked)
#----------------------------------------
