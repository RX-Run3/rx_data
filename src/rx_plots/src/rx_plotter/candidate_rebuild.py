'''
Module containing Candidate class
'''
import os

from contextlib   import ExitStack
from typing       import Final
from dmu.plotting import OverlayConf
from dmu.plotting import Plotter1D
from ROOT         import RDF
from pydantic     import BaseModel, RootModel, model_validator
from rx_common    import Component, Cuts, Qsq, Trigger
from rx_data      import CandidateRebuilder, RDFGetter
from rx_selection import selection as sel

_ANADIR : Final[str] = os.environ['ANADIR']
# ------------------------------------------------
class SwapConf(RootModel[dict[str, dict[str, int]]]):
    '''
    Class representing ID swap configuration
    Keys are labels of swaps, inner dictionary keys
    are particle labels and values are PDG ID to swap for
    '''
    def __iter__(self): # type: ignore[override]
        return iter(self.root)

    def __getitem__(self, key):
        return self.root[key]

    def items(self):
        return self.root.items()
    # --------------------------------
    @property
    def particles(self) -> set[str]:
        '''
        All particles involved in swaps
        '''
        particles : list[str] = []
        for swaps in self.root.values():
            particles.extend(swaps.keys())

        return set(particles)
# ------------------------------------------------
class CandidateRebuildConf(BaseModel):
    '''
    Class meant to hold configuration needed
    to plot rebuilt candidates
    '''
    selection  : dict[Cuts, str] | None
    q2bin      : Qsq
    trigger    : Trigger
    sample     : Component
    particles  : set[str]
    constraint : tuple[int,set[str]]
    swaps      : SwapConf
    plots      : OverlayConf
    # ------------------------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def _pre_validate(cls, data):
        trigger = data['trigger']
        sample  = data['sample' ]
        path    = data['plots']['saving']['plt_dir']
        path    =f'{_ANADIR}/plots/{path}/{trigger}-{sample}'

        data['plots']['saving']['plt_dir'] = path

        return data
    # ------------------------------------------------
    @model_validator(mode = 'after')
    def _post_validate(self) -> 'CandidateRebuildConf':
        if not self.particles:
            raise ValueError('Missing particles')

        if not all(swp in self.particles for swp in self.swaps.particles):
            raise ValueError(f'At least one swap does not involve a valid particle: {self.swaps}')

        _, parts = self.constraint
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
        with ExitStack() as stack:
            if self._cfg.selection:
                ctx_sel = sel.custom_selection(d_sel = self._cfg.selection)
                stack.enter_context(ctx_sel)

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

        for category, swap in self._cfg.swaps.items():
            bdr = CandidateRebuilder(
                rdf          = rdf,
                replacements = swap,
                constraint   = self._cfg.constraint,
                tracks       = self._cfg.particles)

            rdf_swap  = bdr.get_df(
                progress_bar = True,
                only_new     = False,
                prefix       = 'plots',
                kind         = 'root')

            d_rdf : dict[str,RDF.RNode] = {}

            d_rdf['Old'] = rdf_swap.Define('Mass', 'plots_mass_old')
            d_rdf['New'] = rdf_swap.Define('Mass', 'plots_mass_new')

            plt_cfg = self._cfg.plots.copy_cfg(suffix = category)
            ptr = Plotter1D(d_rdf = d_rdf, cfg = plt_cfg.as_dictconfig)
            ptr.run()
# ------------------------------------------------
