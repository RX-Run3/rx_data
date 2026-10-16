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
    model_config = {"arbitrary_types_allowed": True, "use_attribute_docstrings": True}

    title : str | None = None
    '''Title'''

    stacked : bool = True
    '''If true will stack the PDFs'''

    blind : tuple[str, float, float] | None = None
    '''PDF name for the signal if blinding is needed, followed by blinding range, min and max.'''

    no_data : bool = False
    '''If true data won't be plotted as well as pull'''

    ranges : list[tuple[float, float]] | None = None
    '''List of tuples with ranges if any was used for the fit, e.g. [(0, 3), (7, 10)]'''

    nbins : int = 50
    '''Bin numbers'''

    unit : str = r'$\rm{MeV}/\it{c}^{2}$'
    '''Unit for x axis, default is MeV/c^2'''

    xlabel : str = ''
    '''xlabel'''

    ylabel : str = ''
    '''ylabel'''

    d_leg : dict[str, str] = Field(default_factory=dict)
    '''Customize legend'''

    d_col : dict[str, str] = Field(default_factory=dict)
    '''Dictionary mapping fit component to color name'''

    plot_range : tuple[float, float] | None = None
    '''Tuple with lower and upper bound for plot'''

    plot_components : list[str] = Field(default_factory=list)
    '''List of strings, with names of PDFs, which are expected to be sums of PDFs and whose components should be plotted separately'''

    ext_text : str | None = None
    '''Text that can be added to plot'''

    add_pars : str | list[str] | None = None
    '''List of names of parameters to be added or string with value 'all' to add all fit parameters. If this is used, plot won't use LHCb style.'''

    ymax : float | None = None
    '''Optional, if specified will be used to set the maximum in plot'''

    skip_pulls : bool = False
    '''Will not draw pulls if True, default False'''

    pull_styling : bool = True
    '''Will add lines at +/-3 and set range to +/-5 for pull plots, by default True'''

    yscale : str = 'linear'
    '''Scale for y axis of main plot, either log or linear'''

    axs : tuple[Axes, ...] | None = None
    '''Axes tuple'''

    figsize : tuple[int, int] = (13, 7)
    '''Tuple with figure size, default (13, 7)'''

    leg_loc : str = 'best'
    '''Location of legend, default 'best' '''
    # ---------------------------
    @classmethod
    def default(cls, stacked : bool = True) -> Self:
        '''
        Returns default instance of current class
        '''
        return cls(stacked = stacked)
#----------------------------------------
