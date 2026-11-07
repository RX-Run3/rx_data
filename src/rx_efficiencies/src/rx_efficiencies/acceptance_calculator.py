'''
Module holding AcceptanceCalculator class
'''

import os
import matplotlib.pyplot as plt

from ROOT      import RDF
from dmu       import LogStore
from typing    import Final
from pathlib   import Path
from functools import cached_property
from rx_common import Channel, Project

log = LogStore.add_logger('prec_acceptances::calculator')

_MIN_THETA   : Final[float]    = 0.010
_MAX_THETA   : Final[float]    = 0.400
_LEPTONS     : Final[set[str]] = {'ep', 'em', 'mup', 'mum'}

# Components associated to these tracks are in
# rx_efficiencies/utilities.py
_RK_HADRONS    : Final[list[set[str]]] = [
    {'Kp_0', 'pi0_0'},
    {'Kp_0', 'pim_0'},
    {'Kp_0'},
    {'pip_0'},
    {'Kp_0', 'Km_0'},
]
_RKST_HADRONS  : Final[list[set[str]]] = [
    {'Kp_0', 'pim_0'},
    {'Kp_0', 'pim_0', 'pip_0'},
    {'Kp_0', 'Km_0'},
    {'Kp_0', 'pm_0'},
]
#-----------------------------
class AcceptanceCalculator:
    '''
    Class meant to calculate geometric acceptances from a Tree created by RapidSim in the 4pi
    acceptance.
    '''
    #-----------------------------
    def __init__(
        self,
        rdf    : RDF.RNode,
        channel: Channel,
        project: Project):
        '''
        Parameters
        ----------------
        rdf    : DataFrame with ntuple made by RapidSim
        channel: Either ee or mm
        project: Either rk or rkst, needed to define tracks used to calculate acceptance
        '''
        if channel not in {Channel.ee, Channel.mm}:
            raise ValueError(f'Invalid channel: {channel}')

        self._channel = channel

        if project not in {Project.rk, Project.rkst}:
            raise ValueError(f'Invalid project: {project}')

        self._project     = project

        self._rdf         = rdf
        self._plot_dir : Path

        self._initialized = False
    #-----------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._validate_ntuple()

        for track in self._all_tracks:
            self._rdf = self._rdf.Define(f'{track}_et', f'{track}_eta_TRUE')
            self._rdf = self._rdf.Define(f'{track}_th', f'2 * TMath::ATan( TMath::Exp(-{track}_et) )')
            self._rdf = self._rdf.Define(f'{track}_in', f'({track}_th > {_MIN_THETA}) && ({track}_th < {_MAX_THETA})')

            self._plot_split(
                rdf   = self._rdf,
                theta = f'{track}_th',
                flag  = f'{track}_in')

            self._plot(self._rdf, f'{track}_et')

        self._initialized = True
    # ----------------------
    def _validate_ntuple(self) -> None:
        '''
        Validates consistency of ntuple and project choice
        '''
        fail = False
        for lepton in self._leptons:
            if lepton not in self._all_tracks:
                log.error(f'Lepton {lepton} not found')
                fail = True

        if fail:
            raise ValueError('At least one lepton was not found')
    #-----------------------------
    @property
    def plot_dir(self) -> Path:
        '''
        Returns path to directory where validation plots go
        '''
        return self._plot_dir
    #-----------------------------
    @plot_dir.setter
    def plot_dir(self, value : Path) -> None:
        try:
            os.makedirs(value, exist_ok=True)
        except:
            log.error(f'Cannot make: {value}')
            raise

        self._plot_dir = value
    #-----------------------------
    def _plot_split(
        self,
        rdf   : RDF.RNode,
        theta : str,
        flag  : str) -> None:
        '''
        Parameters
        --------------
        rdf  : DataFrame with kinematics
        theta: e.g. ep_0_th
        flag : e.g. ep_0_in
        '''
        rdf_in = rdf.Filter(f'{flag} == 1')
        rdf_ot = rdf.Filter(f'{flag} == 0')

        arr_in = rdf_in.AsNumpy([theta])[theta]
        arr_ot = rdf_ot.AsNumpy([theta])[theta]

        plt.hist(arr_in, bins=100, range=(0, 3.1415), alpha=0.7, color='r', label='In')
        plt.hist(arr_ot, bins=100, range=(0, 3.1415), alpha=0.7, color='b', label='Out')
        plt.legend()
        plt.ylabel('Entries')
        plt.xlabel(r'$\theta$[rad]')

        plot_path=f'{self._plot_dir}/{theta}.png'
        log.info(f'Saving to: {plot_path}')
        plt.savefig(plot_path)
        plt.close('all')
    #-----------------------------
    def _plot(
        self,
        rdf : RDF.RNode,
        var : str) -> None:
        '''
        Plots variable in dataframe
        '''
        arr_var = rdf.AsNumpy([var])[var]

        plt.hist(arr_var, bins=100, range=(-6, +6), alpha=0.7, color='b', label='Out')
        plt.ylabel('Entries')
        plt.xlabel(r'$\eta$')

        plt.savefig(f'{self._plot_dir}/{var}.png')
        plt.close('all')
    #-----------------------------
    @cached_property
    def _all_tracks(self) -> set[str]:
        '''
        Returns
        -------------
        List of strings, each of them is the name of a track, e.g. ep_0
        '''
        v_col = self._rdf.GetColumnNames()
        l_col = [ col.c_str() for col in v_col ]
        l_trk = [ trk         for trk in l_col if trk.endswith('_eta_TRUE')]
        l_trk = [ trk.replace('_eta_TRUE', '') for trk in l_trk ]

        log.info('Found following tracks:')
        for trk in l_trk:
            log.info(trk)

        return set(l_trk)
    #-----------------------------
    @cached_property
    def _all_hadrons(self) -> set[str]:
        '''
        Returns
        -------------
        List of strings, each of them is the name of a hadron track, e.g. Kp_0
        '''
        hadrons : set[str] = set()
        for track in self._all_tracks:
            if any(track.startswith(lep) for lep in _LEPTONS):
                continue

            hadrons.add(track)

        return hadrons
    #-----------------------------
    @cached_property
    def _leptons(self) -> tuple[str,str]:
        '''
        Returns
        -----------
        Tuple with strings with names for leptons in ntuple
        '''
        if self._channel == Channel.ee:
            return 'ep_0', 'em_0'

        if self._channel == Channel.mm:
            return 'mup_0', 'mum_0'

        raise ValueError(f'Invalid channel: {self._channel}')
    #-----------------------------
    def _get_numerators(self) -> tuple[int,int]:
        '''
        Returns
        -------------------
        Tuple with number of track sets passing acceptance

        first element : Physical acceptance, i.e. what would be seen in the targetted final state
        second element: LHCb acceptance, i.e. all the track (even the unused ones) need to be in acceptance
        '''
        rdf          = self._rdf
        l_all_trk_in = [ f'{trk}_in' for trk in self._all_tracks ]
        all_in       = '&&'.join(l_all_trk_in)
        rdf          = rdf.Define('is_lhc', all_in)

        _lep_plus, _lep_minus = self._leptons
        lep_acceptance = f'{_lep_plus}_in && {_lep_minus}_in'

        if   self._project == Project.rk:
            rdf = self._define_phy_rk(  rdf=rdf, lep_acceptance=lep_acceptance)
        elif self._project == Project.rkst:
            rdf = self._define_phy_rkst(rdf=rdf, lep_acceptance=lep_acceptance)
        else:
            raise ValueError(f'Invalid project: {self._project}')

        nlhc = rdf.Sum('is_lhc').GetValue()
        nphy = rdf.Sum('is_phy').GetValue()

        return nphy, nlhc
    # ----------------------
    def _define_phy_rk(self, rdf : RDF.RNode, lep_acceptance : str) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT DataFrame
        lep_acceptance: String defining condition for lepton acceptance

        Returns
        -------------
        DataFrame with is_phy defined
        '''
        if self._all_hadrons not in _RK_HADRONS:
            raise ValueError(f'Hadrons {self._all_hadrons} not expected in RK project')

        if self._all_hadrons == {'Kp_0', 'Km_0'}:
            # For Bs -> phi(KK) ll case
            return rdf.Define('is_phy', f'{lep_acceptance} && (Kp_0_in || Km_0_in)')

        if self._all_hadrons == {'pip_0'}:
            # Cabibbo suppressed B -> pi ll
            return rdf.Define('is_phy', f'{lep_acceptance} && pip_0_in')

        if self._all_hadrons in [{'Kp_0'}, {'Kp_0', 'pim_0'}, {'Kp_0', 'pi0_0'}]:
            # Signal or part reco
            return rdf.Define('is_phy', f'{lep_acceptance} && Kp_0_in')

        raise ValueError(f'For project {self._project}, found tracks: {self._all_tracks}')
    # ----------------------
    def _define_phy_rkst(self, rdf : RDF.RNode, lep_acceptance : str) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT DataFrame
        lep_acceptance: String defining condition for lepton acceptance

        Returns
        -------------
        DataFrame with is_phy defined
        '''
        if self._all_hadrons not in _RKST_HADRONS:
            raise ValueError(f'Hadrons {self._all_hadrons} not expected in RK* project')

        if self._all_hadrons == {'Kp_0', 'pim_0'}:
            # Signal, rare or resonant
            return rdf.Define('is_phy', f'{lep_acceptance} && Kp_0_in && pim_0_in')

        if self._all_hadrons == {'Kp_0', 'pim_0', 'pip_0'}:
            # Part reco
            return rdf.Define('is_phy', f'{lep_acceptance} && Kp_0_in && pim_0_in')

        if self._all_hadrons == {'Kp_0', 'Km_0'}:
            # Kaon mis-ID, K -> pi in resonant mode
            return rdf.Define('is_phy', f'{lep_acceptance} && Kp_0_in && Km_0_in')

        if self._all_hadrons == {'Kp_0', 'pm_0'}:
            # Single or double misid Kp -> K pi in resonant mode
            return rdf.Define('is_phy', f'{lep_acceptance} && Kp_0_in && pm_0_in')

        raise ValueError(f'For project {self._project} found hadron tracks: {self._all_hadrons}')
    #-----------------------------
    def get_acceptances(self) -> tuple[float,float]:
        '''
        Will return tuple with acceptances:

        physical: That contributes to the PRec of RK
        LHCb: Where all tracks are inside the LHCb acceptance
        '''
        self._initialize()
        ntot       = self._rdf.Count().GetValue()
        ntot       = float(ntot)
        nphy, nlhc = self._get_numerators()

        eff_phy, eff_lhc = (nphy/ntot), (nlhc/ntot)

        log.info(f'Physical: {eff_phy:.3f}')
        log.info(f'LHCb:     {eff_lhc:.3f}')

        return eff_phy, eff_lhc
#-----------------------------
