'''
Module with class used to swap mass hypotheses
'''
import pandas as pnd
import vector
import numpy

from ROOT         import RDF
from typing       import Literal, overload
from tqdm         import tqdm
from particle     import Particle         as part
from vector       import MomentumObject3D as v3d
from vector       import MomentumObject4D as v4d

from dmu          import LogStore
from dmu.generic  import typing_utilities as tut

log = LogStore.add_logger('rx_data:candidate_rebuilder')
#---------------------------------
class CandidateRebuilder:
    '''
    Class used to calculate track combinations under mass hypotheses
    changes
    '''
    #---------------------------------
    def __init__(
        self,
        rdf          : RDF.RNode,
        tracks       : set[str],
        replacements : dict[str,int],
        constraint   : tuple[int,set[str]] | None):
        '''
        Parameters
        --------------
        rdf        : ROOT dataframe
        tracks     : Set of strings representing particle prefixes, e.g. {L1, L2,...} 
        d_had      : Dictionary mapping hadron names with mass hypetheses to swap, e.g. {H : 312}
        constraint : Tuple with PDG ID and set of strings representing particles
                     whose combined mass is constrainted to the PDG ID's value
                     by default None
        '''
        self._rdf           = rdf
        self._tracks        = tracks 
        self._replacements  = replacements 
        self._constraint    = constraint

        self._df            = self._pnd_from_root(rdf)
        self._initialized   = False
    #---------------------------------
    def _pnd_from_root(self, rdf : RDF.RNode) -> pnd.DataFrame:
        l_col_all = sorted([ name.c_str() for name in rdf.GetColumnNames() ])
        s_col     = { name         for name in l_col_all if self._pick_column(name) }

        ncol  = len(s_col)
        log.debug(f'Using {ncol} columns for dataframe')

        d_data= rdf.AsNumpy(list(s_col))
        df    = pnd.DataFrame(d_data)

        return df
    #---------------------------------
    def _pick_column(self, name : str) -> bool:
        '''
        Parameters
        ----------------
        name: Name of column in dataframe

        Returns
        ----------------
        True if this is an ID or momentum column
        '''
        l_kin = []
        l_evt = ['EVENTNUMBER', 'RUNNUMBER']
        for par in self._tracks:
            l_kin += [
                f'{par}_PX',
                f'{par}_PY',
                f'{par}_PZ',
                f'{par}_PE',
                f'{par}_ID']

        pick = name in l_kin + l_evt

        if pick:
            log.debug(f'Using column: {name}')

        return pick
    #---------------------------------
    def _initialize(self):
        if self._initialized:
            return

        replacements = set(self._replacements.values())
        self._check_particle(tracks = replacements)

        tqdm.pandas(ascii=' -')

        self._initialized=True
    #---------------------------------
    def _check_particle(self, tracks : set[int]) -> None:
        for pdg_id in tracks:
            try:
                part.from_pdgid(value = pdg_id)
            except Exception as exc:
                raise ValueError(f'Cannot create particle for PDGID: {pdg_id}') from exc
    #---------------------------------
    def _get_4vec(self, row : pnd.Series, name : str) -> v4d:
        '''
        This function is needed because the PE (energy) of the particle was not stored
        in the ntuples
        '''
        px     = tut.numeric_from_series(row, f'{name}_PX', float)
        py     = tut.numeric_from_series(row, f'{name}_PY', float)
        pz     = tut.numeric_from_series(row, f'{name}_PZ', float)
        par_3d = v3d(px=px, py=py, pz=pz)

        par_id = tut.numeric_from_series(row, f'{name}_ID', int)
        par    = part.from_pdgid(par_id)
        ms     = par.mass
        if ms is None:
            raise ValueError(f'Cannot get mass from particle with PDG ID: {par_id}')
        vec    = vector.obj(pt=par_3d.pt, phi=par_3d.phi, eta=par_3d.eta, mass=ms)

        return vec
    #---------------------------------
    def _combine(
        self,
        row  : pnd.Series,
        kind : str) ->  float:
        '''
        Parameters
        ----------------------
        kind : If old, do not replace anything
        row  : Pandas dataframe row representing an entry in a ROOT tree, i.e. a candidate

        Returns
        ----------------------
        Mass of the combination of particles
        '''
        sum : None | v4d  = None
        for particle in self._tracks:
            if self._constraint and particle in self._constraint[1]:
                continue

            vec = self._get_4vec(row = row, name = particle)

            if kind == 'new':
                vec = self._update_mass(vec = vec, name = particle)

            if sum is None:
                sum = vec
                continue

            sum = sum + vec # type: ignore

        if self._constraint:
            sum = sum + self._get_constrained_combination(row = row) # type: ignore

        if sum is None:
            raise ValueError(f'No sum obtained, used tracks: {self._tracks}')

        return sum.mass
    # ----------------------
    def _get_constrained_combination(self, row : pnd.Series) -> v4d:
        '''
        Parameters
        -------------
        row: Row from input dataframe, associated to candidate with all kinematic information

        Returns
        -------------
        4-vector associated to particle combination that needs constraining
        '''
        if not self._constraint:
            raise ValueError('Cannot get constraints, constraints not passed')

        sum : v4d | None = None
        for particle in self._constraint[1]:
            vec = self._get_4vec(row = row, name = particle)

            if sum is None:
                sum = vec
            else:
                sum = sum + vec # type: ignore

        if sum is None:
            raise ValueError('No sum found to constrain')

        pdg_id   = self._constraint[0]
        particle = part.from_pdgid(pdg_id)

        mass = particle.mass
        if mass is None:
            raise ValueError(f'Cannot find mass for {particle} with ID: {pdg_id}')

        sum.mass = mass

        return sum
    # ----------------------
    def _update_mass(self, vec : v4d, name : str) -> v4d:
        '''
        Parameters
        -------------
        vec : 4-vector representing particle
        name: Name of particle, e.g. L1, L2, K...

        Returns
        -------------
        Particle after mass replacement 
        '''
        new_pdgid = self._replacements.get(name)

        if new_pdgid is None: 
            return vec

        particle = part.from_pdgid(value = new_pdgid)        

        new_mass = particle.mass
        if new_mass is None:
            raise ValueError(f'No mass found for {particle}, ID: {new_pdgid}')

        vec.mass = new_mass
        
        return vec 
    #---------------------------------
    def _calculate_mass(
        self, 
        progress_bar : bool, 
        kind         : str) -> pnd.Series:
        '''
        Parameters
        ---------------
        progress_bar: If true will use progress bar across candidates
        kind        : old/new
        '''
        args = kind,

        if not progress_bar:
            return self._df.apply(self._combine, args=args, axis=1)

        sr_mass = self._df.progress_apply( # type: ignore
            self._combine, 
            args = args,
            axis = 1)

        return sr_mass
    #---------------------------------
    @overload
    def get_df(
        self,
        format       : Literal['pandas'],
        prefix       : str,
        only_new     : bool = False,
        progress_bar : bool = False) -> pnd.DataFrame: ...
    @overload
    def get_df(
        self,
        format       : Literal['root'],
        prefix       : str,
        only_new     : bool = False,
        progress_bar : bool = False) -> RDF.RNode: ...
    def get_df(
        self,
        format       : Literal['pandas', 'root'],
        prefix       : str,
        only_new     : bool = False,
        progress_bar : bool = False) -> RDF.RNode | pnd.DataFrame:
        '''
        Parameters:
        ------------------
        format      : Either pandas or root, used to pick dataframe format
        prefix      : Will be used to name branches with masses as `{preffix}_mass_old/new` for the original and swapped masses
        progress_bar: If True, will show progress bar, by default false

        Returns:
        ------------------
        Pandas dataframe with orignal and swapped masses, i.e. masses after the mass hypothesis swap
        '''
        self._initialize()

        d_data : dict[str, numpy.ndarray] = {}

        kinds = ['new'] if only_new else ['old', 'new']
        for kind in kinds:
            sr_mass = self._calculate_mass(progress_bar, kind)
            d_data[f'{prefix}_mass_{kind}'] = sr_mass.to_numpy().flatten()

        if format == 'pandas':
            return pnd.DataFrame(d_data)

        try:
            rdf = RDF.FromNumpy(d_data)
        except RuntimeError as exc:
            for name, arr_val in d_data.items():
                log.error(f'{name}:')
                log.error(arr_val)
                log.error('')
            raise RuntimeError('Cannot create ROOT dataframe') from exc

        return rdf
#---------------------------------
