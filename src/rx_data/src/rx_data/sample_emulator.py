'''
Module holding SampleEmulator class
'''
import json

from ROOT        import RDF
from dmu         import LogStore
from typing      import Any, Final
from dmu.generic import utilities as gut
from pydantic    import BaseModel, RootModel
from rx_common   import Block, Component

log=LogStore.add_logger('rx_data:sample_emulator')

_MASSES : Final[dict[int,float]] = {
    11 : 0.51099895,     # Electron mass in MeV
    13 : 105.6583755,    # Muon mass in MeV
    321: 493.677,        # Charged Kaon mass in MeV
    211: 139.57039,      # Charged Pion mass in MeV
}
'''Dictionary mapping PDG ID with particle mass in MeV'''
# ----------------------
class SamplesConf(RootModel[dict[Component,float]], frozen=True, strict=True):
    '''
    Class meant to represent a cocktail of samples
    and the fractions of each

    Attributes:
    ------------------
    root: Dictionary mapping sample name (e.g. Bs_JpsiKst_ee_eq_DPC) to
          fraction of it in cocktail
    '''
    # --------------------------------------
    def __str__(self):
        msg = '\n'
        msg+= 20 * '-' + '\n'
        msg+= 'Cocktail components\n'
        msg+= 20 * '-' + '\n'
        for component, fraction in self.root.items():
            msg += f'{component:<30}{fraction:.3g}\n'

        return msg
    # --------------------------------------
    @property
    def is_cocktail(self) -> bool:
        '''
        True if this is a set of samples instead of one
        '''
        return len(self.root) > 1
    # --------------------------------------
    @property
    def is_data(self) -> bool:
        '''
        True if all keys are data samples
        '''
        for component in self.root:
            if component.is_mc:
                return False

        return True
    # --------------------------------------
    def emulated_only_by(self, sample : str) -> bool:
        '''
        Parameters
        -------------
        sample: Name of MC sample

        Returns
        -------------
        True if current config describes `sample` as the only
        emulator sample
        '''
        if len(self.root) != 1:
            return False

        (emulator, frac), = self.root.items()

        if frac != 1:
            raise ValueError(f'Found single emulating sample with fraction: {frac}')

        return emulator == sample
    # --------------------------------------
    def model_post_init(self, context : Any) -> None:
        self.__validate_fraction()

        return super().model_post_init(context)
    # --------------------------------------
    def __validate_fraction(self):
        fractions = list(self.root.values())

        if not all(0.0 < fraction <= 1.0 for fraction in fractions):
            raise ValueError(f'Invalid sample fractions: {self}')

        if sum(fractions) != 1:
            raise ValueError(f'Sum of sample fractions not 1: {fractions}')
# ----------------------
class EmulationConf(BaseModel, frozen=True, extra='forbid', strict=True):
    '''
    Class meant to represent configuration needed
    to emulate a sample
    '''
    samples  : SamplesConf
    '''Used to configure build of sample cocktails'''

    patching : dict[Block, Block] = dict()
    '''Dictionary meant to allow patching blocks of data'''

    redefine : dict[str  ,   str] = dict()
    '''Dictionary used to update candidate information, e.g. B -> B + 30
    meant to change mass hypotheses of particles or mother IDs'''

    trk_swap : dict[str  ,   str] = dict()
    '''Dictionary mapping particle prefixes, e.g. L1 -> H
    meant to be used to swap values of columns'''

    masses   : dict[str, dict[str,int]] = dict()
    '''Dictionary describing how to rebuild mass columns'''
    # --------------------------------------
    def model_post_init(self, context : Any) -> None:
        '''
        Validates fields
        '''
        self._validate_patching()

        return super().model_post_init(context)
    # --------------------------------------
    def _validate_patching(self):
        for init, fnal in self.patching.items():
            if init == fnal:
                raise ValueError('Initial and final block cannot be the same')
# ----------------------
class EmulatorConf(RootModel[dict[Component, EmulationConf]], frozen=True, strict=True):
    '''
    Class meant to represent configuration needed to emulate
    samples
    '''
# ----------------------
class SampleEmulator:
    '''
    Class meant to:

    - Open config file with emulation settings
    - Provide emulating sample name
    - Postprocess original sample to make it suitable for emulation
    '''
    # ----------------------
    def __init__(self, sample : Component) -> None:
        '''
        Parameters
        ---------------
        sample: Sample to emulate e.g. bpkpee
        '''
        fpath       = 'emulated_trees/config.yaml'
        data        = gut.load_data(package='rx_data_data', fpath=fpath)
        data_string = json.dumps(data)
        cfg         = EmulatorConf.model_validate_json(data_string)

        if sample in cfg.root:
            log.warning(f'Emulating {sample}')
            self._cfg = cfg.root[sample]
            return

        log.info(f'Not emulating {sample}')
        samples   = SamplesConf({sample : 1.0})
        self._cfg = EmulationConf(samples = samples)
    # ----------------------
    def _run_redefine(
        self,
        rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf : DataFrame before redefinitions

        Returns
        -------------
        Dataframe after definitiions
        '''
        for var, expr in self._cfg.redefine.items():
            assert isinstance(var, str)

            log.debug(f'{var:<10}{"--->"}\n{expr}')
            rdf = rdf.Redefine(var, expr)

        return rdf
    # ----------------------
    def _update_cocktail_weights(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: Dataframe

        Returns
        -------------
        Dataframe with cocktail weights added
        '''
        if not self._cfg.samples.is_cocktail:
            return rdf

        # TODO: Needs to be implemented when EVENTTYPE branch be fixed
        # Hard to pick correct weight per-sample otherwise
        log.warning(f'Not adding cocktail weights for: {self._cfg.samples}')

        return rdf
    # ----------------------
    def _swap_tracks(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ----------------
        rdf: ROOT dataframe

        Returns
        ----------------
        Dataframe with track swapping, if requested through `trk_swap`
        '''
        if not self._cfg.trk_swap:
            return rdf

        cols = [ col.c_str() for col in rdf.GetColumnNames() ]

        for col_1, col_2 in self._cfg.trk_swap.items():
            rdf = self._swap_columns(
                rdf   = rdf,
                cols  = cols,
                prf_1 = col_1,
                prf_2 = col_2)

        return rdf
    # ----------------------
    def _swap_columns(
        self,
        rdf   : RDF.RNode,
        cols  : list[str],
        prf_1 : str,
        prf_2 : str) -> RDF.RNode:
        '''
        Parameters
        --------------
        rdf  : ROOT dataframe
        cols : All columns in dataframe
        prf_x: Column prefixes for columns to be swapped, e.g. L1, H

        Returns
        --------------
        Dataframe with `prf_1` and `prf_2` columns swapped
        '''
        vars_1 = { col.removeprefix(prf_1) for col in cols if col.startswith(prf_1) }
        vars_2 = { col.removeprefix(prf_2) for col in cols if col.startswith(prf_2) }
        all_vars = vars_1 | vars_2

        for var in all_vars:
            rdf = self._swap_var(
                rdf  = rdf,
                cols = cols,
                var_1= f'{prf_1}{var}',
                var_2= f'{prf_2}{var}')

        return rdf
    # ---------------------
    def _swap_var(
        self,
        rdf   : RDF.RNode,
        cols  : list[str],
        var_1 : str,
        var_2 : str) -> RDF.RNode:
        '''
        Parameters
        ----------------
        rdf  : Dataframe where swapping will happen
        cols : List with column names
        var_x: Column names to be swapped

        Returns
        ----------------
        Dataframe with columns swapped, if either column does not
        exist the swapped value will be a nan
        '''
        if var_1 not in cols:
            return rdf.Redefine(var_2, 'std::numeric_limits<double>::quiet_NaN()')

        if var_2 not in cols:
            return rdf.Redefine(var_1, 'std::numeric_limits<double>::quiet_NaN()')

        tmp = f'tmp_{var_1}'
        rdf = rdf.Define(tmp  , var_1)

        rdf = rdf.Redefine(var_1, var_2)
        rdf = rdf.Redefine(var_2,   tmp)

        return rdf
    # ---------------------
    def _rebuild_masses(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ---------------
        rdf: Dataframe before mass rebuilding

        Returns
        ---------------
        Dataframe after mass rebuilding
        '''
        if not self._cfg.masses:
            return rdf

        for name, tracks in self._cfg.masses.items():
            rdf = self._add_mass(rdf = rdf, name = name, tracks = tracks)

        return rdf
    # ---------------------
    def _add_mass(self, rdf : RDF.RNode, name : str, tracks : dict[str,int]) -> RDF.RNode:
        '''
        Parameters
        ---------------
        rdf   : Dataframe before mass rebuilding
        name  : Name of column storing mass, e.g. `Kstar_M`
        tracks: Dictionary mapping particle names to PDG ID used to extract mass

        Returns
        ---------------
        DataFrame with mass column added
        '''
        vec_str : list[str] = []
        sum_str : list[str] = []

        log.debug(f'Rebuilding: {name}')

        counter = 1
        for track, pdg_id in tracks.items():
            trk_expr = self._get_vector_expr(track, pdg_id, counter)
            vec_str.append(trk_expr)
            sum_str.append(f't{counter}')

            counter += 1

        expr_1 = ';'.join(vec_str)
        expr_2 = '+'.join(sum_str)
        expr   = f'{expr_1}; auto sum = {expr_2}; return sum.M();'

        log.debug('')
        log.debug(f'{name}:\n{expr}')
        log.debug('')

        rdf = rdf.Redefine(name, expr)

        return rdf
    # ---------------------
    def _get_vector_expr(
        self,
        track  : str,
        pdg_id : int,
        counter: int) -> str:
        '''
        Parameters
        ------------------
        track  : Name of track, e.g. L1
        pdg_id : E.g. 11 for electron, needed to pick mass
        counter: Used as index for 4-vector

        Returns
        ------------------
        Expression describing 4-vector for track
        '''
        pdg_id = abs(pdg_id)
        mass   = _MASSES[pdg_id]

        return f'ROOT::Math::PtEtaPhiMVector t{counter}({track}_PT, {track}_ETA, {track}_PHI, {mass})'
    # ---------------------
    @property
    def samples(self) -> SamplesConf:
        '''
        Object specifying how to build sample passed in initializer
        '''
        return self._cfg.samples
    # ----------------------
    def post_process(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataFrame

        Returns
        -------------
        Dataframe after redefinitions, etc
        '''
        size = rdf.Count().GetValue()
        if size == 0:
            log.warning('Not running emulation for empty dataframe')
            return rdf

        rdf = self._update_cocktail_weights(rdf = rdf)
        rdf = self._swap_tracks(rdf=rdf)
        rdf = self._rebuild_masses(rdf = rdf)
        rdf = self._run_redefine(rdf=rdf)

        return rdf
# ----------------------
