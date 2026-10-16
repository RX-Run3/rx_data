'''
Module holding ZFitPlotterConf
'''
from typing          import Self
from pydantic        import BaseModel, Field
from matplotlib.axes import Axes

#----------------------------------------
class ZFitPlotterConf(BaseModel, frozen = True):
    '''
    Class meant to hold configuration for ZFitPlotter
    '''
    model_config = {"arbitrary_types_allowed": True}

    title           : str | None                     = None
    stacked         : bool                           = True
    blind           : tuple[str, float, float] | None = None
    no_data         : bool                           = False
    ranges          : list[tuple[float, float]] | None = None
    nbins           : int                            = 50
    unit            : str                            = r'$\rm{MeV}/\it{c}^{2}$'
    xlabel          : str                            = ''
    ylabel          : str                            = ''
    d_leg           : dict[str, str]                 = Field(default_factory=dict)
    d_col           : dict[str, str]                 = Field(default_factory=dict)
    plot_range      : tuple[float, float] | None     = None
    plot_components : list[str]                      = Field(default_factory=list)
    ext_text        : str | None                     = None
    add_pars        : str | list[str] | None         = None
    ymax            : float | None                   = None
    skip_pulls      : bool                           = False
    pull_styling    : bool                           = True
    yscale          : str                            = 'linear'
    axs             : tuple[Axes, ...] | None        = None
    figsize         : tuple[int, int]                = (13, 7)
    leg_loc         : str                            = 'best'
    # ---------------------------
    @classmethod
    def default(cls, stacked : bool = True) -> Self:
        '''
        Returns default instance of current class
        '''
        return cls(stacked = stacked)
#----------------------------------------
