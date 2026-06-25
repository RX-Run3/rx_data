'''
Module containing Candidate class
'''
from dmu.plotting import OverlayConf
from dmu.plotting import Plotter1D
from ROOT         import RDF # type: ignore
from pydantic     import BaseModel, model_validator
from rx_common    import Component, Qsq, Trigger
from rx_data      import CandidateRebuilder, RDFGetter
from rx_selection import selection as sel 

# ------------------------------------------------
class CandidateRebuildConf(BaseModel):
    '''
    Class meant to hold configuration needed
    to plot rebuilt candidates
    '''
    q2bin       : Qsq
    trigger     : Trigger
    sample      : Component
    particles   : set[str]
    constraints : dict[int,list[str]]
    swaps       : dict[str,int]
    plots       : OverlayConf
    # ------------------------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'CandidateRebuildConf':
        if not self.particles:
            raise ValueError('Missing particles')

        if not all(swp in self.particles for swp in self.swaps):
            raise ValueError(f'At least one swap does not involve a valid particle: {self.swaps}')

        for parts in self.constraints.values():
            if not all(part in self.particles for part in parts):
                raise ValueError(f'At least one constraint contains invalid particles: {parts}')

        return self
# ------------------------------------------------
class CandidateRebuild:
    '''
    Class meant to plot quantities associated to
    rebuilt candidates
    '''
    # --------------------------------
    def __init__(self, cfg : CandidateRebuildConf):
        '''
        Parameters
        -----------------
        cfg: configuration object
        '''
        self._cfg = cfg
    # --------------------------------
    def _filter_rdf(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ---------------
        rdf: ROOT dataframe before selection

        Returns
        ---------------
        ROOT dataframe after selection
        '''
        rdf = sel.apply_full_selection(
            rdf     = rdf, 
            q2bin   = self._cfg.q2bin,
            process = self._cfg.sample, 
            trigger = self._cfg.trigger)

        return rdf
    # --------------------------------
    def run(self) -> None:
        gtr = RDFGetter(
            trigger = self._cfg.trigger,
            sample  = self._cfg.sample)
        rdf = gtr.get_rdf(per_file = False)
        rdf = self._filter_rdf(rdf = rdf)

        bdr = CandidateRebuilder(
            rdf          = rdf,
            replacements = self._cfg.swaps,
            tracks       = self._cfg.particles)

        rdf  = bdr.get_df(
            progress_bar = True,
            only_new     = False,
            prefix       = 'plots',
            format       = 'root')

        d_rdf : dict[str,RDF.RNode] = {}

        d_rdf['Old'] = rdf.Define('Mass', 'plots_mass_old')
        d_rdf['New'] = rdf.Define('Mass', 'plots_mass_New')

        ptr = Plotter1D(d_rdf = d_rdf, cfg = self._cfg.plots.as_dictconfig)
        ptr.run()
# ------------------------------------------------
