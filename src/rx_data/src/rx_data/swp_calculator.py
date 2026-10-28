'''
Module with class used to swap mass hypotheses
'''
import math
import pandas as pnd
import random
import vector

from ROOT        import RDF
from tqdm        import tqdm
from particle    import Particle         as part
from vector      import MomentumObject3D as v3d
from vector      import MomentumObject4D as v4d

from dmu         import LogStore
from dmu.generic import typing_utilities as tut 

log = LogStore.add_logger('rx_data:swp_calculator')
#---------------------------------
class SWPCalculator:
    '''
    Class used to calculate di-track masses, after mass hypothesis swaps
    '''
    #---------------------------------
    def __init__(
        self,
        rdf   : RDF.RNode,
        d_lep : dict[str,int],
        d_had : dict[str,int]):
        '''
        Parameters
        --------------
        rdf   : ROOT dataframe
        d_lep : Dictionary mapping lepton names with mass hypotheses to swap, e.g. {L1 : 13, L2 : 13}
        d_had : Dictionary mapping hadron names with mass hypetheses to swap, e.g. {H : 312}
        '''
        self._rdf    = rdf
        self._d_lep  = d_lep
        self._d_had  = d_had

        self._extra_branches= ['EVENTNUMBER', 'RUNNUMBER']
        self._df            = self._pnd_from_root(rdf)
        self._initialized   = False

        self._use_ss : bool
    #---------------------------------
    def _pnd_from_root(self, rdf : RDF.RNode) -> pnd.DataFrame:
        s_col_all = { name.c_str() for name in rdf.GetColumnNames() }
        s_col     = { name         for name in s_col_all if self._pick_column(name) }

        ncol  = len(s_col)
        log.debug(f'Using {ncol} columns for dataframe')

        d_data= rdf.AsNumpy(list(s_col))
        df    = pnd.DataFrame(d_data)

        return df
    #---------------------------------
    def _pick_column(self, name : str) -> bool:
        l_par = list(self._d_lep) + list(self._d_had)
        l_kin = []
        for par in l_par:
            l_kin += [
                    f'{par}_PX',
                    f'{par}_PY',
                    f'{par}_PZ',
                    f'{par}_PE',
                    f'{par}_ID']

        return name in l_kin
    #---------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._check_particle(self._d_lep)
        self._check_particle(self._d_had)

        tqdm.pandas(ascii=' -')

        self._initialized=True
    #---------------------------------
    def _check_particle(self, d_part):
        if not isinstance(d_part, dict):
            raise ValueError(f'Dictionary expected, found: {d_part}')

        for pdg_id in d_part.values():
            try:
                part.from_pdgid(pdg_id)
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
    def _build_mass(
        self,
        row    : pnd.Series,
        d_part : dict[str,int]) -> float:
        '''
        Parameters
        -----------------
        row: Pandas dataframe row representing candidate
        d_part: Dictionary with:
            key  : Name of particle
            value: PDGID needed for mass swap
        '''
        l_vec = []
        for name, new_id in d_part.items():
            vec_1 = self._get_4vec(row, name)
            old_id= row[f'{name}_ID']
            par   = part.from_pdgid(new_id)
            ms    = par.mass
            if not isinstance(ms, float):
                raise TypeError(f'Failed to determine the mass for particle with PDGID: {new_id}')

            log.debug(f'{name}: {vec_1.mass:0f}({old_id}) -> {ms:.0f}({new_id})')

            vec_2 = v4d(pt=vec_1.pt, eta=vec_1.eta, phi=vec_1.phi, mass=ms)
            l_vec.append(vec_2)

        if len(l_vec) != 2:
            raise ValueError('Not found two and only two particles')

        vec_1 = l_vec[0]
        vec_2 = l_vec[1]
        vec   = vec_1 + vec_2
        mass  = float(vec.mass)

        return mass
    #---------------------------------
    def _combine(
        self,
        row        : pnd.Series,
        had_name   : str,
        kind       : str,
        new_had_id : int) ->  float:
        '''
        Parameters
        ----------------------
        row        : Pandas dataframe row representing an entry in a ROOT tree, i.e. a candidate
        had_name   : Name of prefix for hadron in tree, e.g. H
        kind       : Type of mass, e.g. org, swp. For swap of mass hypotheses or original ones
        new_had_id : PDGID for hadron when swapping of hypotheses is needed

        Returns
        ----------------------
        Mass of the combination of particles
        '''
        old_had_id           = tut.numeric_from_series(row, f'{had_name}_ID', int)
        had                  = part.from_pdgid(old_had_id)
        masses : list[float] = []
        for lep_name, new_lep_id in self._d_lep.items():
            old_lep_id = tut.numeric_from_series(row, f'{lep_name}_ID', int)
            lep        = part.from_pdgid(old_lep_id)

            if lep.charge == had.charge:
                continue

            lep_id = new_lep_id if kind == 'swp' else old_lep_id
            had_id = new_had_id if kind == 'swp' else old_had_id

            mass   = self._build_mass(row, {had_name : had_id, lep_name : lep_id})

            masses.append(mass)

        if not masses and self._use_ss:
            log.debug('No valid OS hadron-lepton combinations found in SS line, return mass = NaN')
            return math.nan

        if self._use_ss:
            log.debug('Multiple valid OS hadron-lepton combination found in SS line, returning random combination')
            return random.choice(masses)

        ncmb = len(masses)
        if ncmb != 1 and not self._use_ss:
            raise ValueError('Not one and only one hadron-lepton combinations found')

        log.debug('Found one hadron-lepton combination in OS line')

        return masses[0]
    #---------------------------------
    def _calculate_mass(self, progress_bar : bool, had_name : str, kind : str, new_had_id : int) -> pnd.Series:
        if progress_bar:
            # TODO: This shows error in type analyzer, progress bar is enable through TQDM
            sr_mass = self._df.progress_apply( # type: ignore
                self._combine, 
                args=(had_name, kind, new_had_id), 
                axis=1)
        else:
            sr_mass = self._df.apply(self._combine, args=(had_name, kind, new_had_id), axis=1)

        return sr_mass
    #---------------------------------
    def get_rdf(
        self,
        preffix      : str,
        progress_bar : bool = False,
        use_ss       : bool = False) -> RDF.RNode:
        '''
        Parameters:
        ------------------
        preffix: Will be used to name branches with masses as `{preffix}_mass_org/swp` for the original and swapped masses
        progress_bar: If True, will show progress bar, by default false
        use_ss: If true, it will combine tracks with same sign, instead of opposite, False by default

        Returns:
        ------------------
        Pandas dataframe with orignal and swapped masses, i.e. masses after the mass hypothesis swap
        '''
        if use_ss:
            log.warning('Building candidates from Same Sign tracks')

        self._use_ss = use_ss
        self._initialize()

        d_data = {}
        for had_name, new_had_id in self._d_had.items():
            for kind in ['org', 'swp']:
                log.info(f'Adding column for {had_name}/{new_had_id}/{kind}')

                sr_mass = self._calculate_mass(progress_bar, had_name, kind, new_had_id)
                d_data[f'{preffix}_mass_{kind}'] = sr_mass.to_numpy().flatten()

        d_extra = self._rdf.AsNumpy(self._extra_branches)
        d_data.update(d_extra)

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
