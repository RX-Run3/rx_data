'''
Module containing HOPVarCalculator class
'''
import math
import numpy

from typing     import Final
from ROOT       import RDF
from ROOT.Math  import LorentzVector, XYZVector
from dmu        import LogStore
from rx_common  import Project, Trigger

log = LogStore.add_logger('rx_data:hop_calculator')

_LORENTZ_DIM : Final[int] = 4
_EUCLID_DIM  : Final[int] = 3
# -------------------------------
class HOPCalculator:
    '''
    Class meant to calculate HOP variables from a ROOT dataframe. For info on HOP see:

    https://cds.cern.ch/record/2102345/files/LHCb-INT-2015-037.pdf
    '''
    # -------------------------------
    def __init__(
        self,
        rdf    : RDF.RNode,
        trigger: Trigger):
        '''
        Parameters
        -----------------
        rdf: ROOT dataframe with input needed to calculate HOP varibles
        trigger: HLT2 trigger name, needed to decide how to add vectors
        '''

        self._rdf           = rdf
        self._trigger       = trigger
        self._extra_branches= ['EVENTNUMBER', 'RUNNUMBER']
    # -------------------------------
    def _val_to_vector(self, arr_val : numpy.ndarray, ndim : int):
        if   ndim == _LORENTZ_DIM:
            [px, py, pz, pe] = arr_val.tolist()
            vector = LorentzVector('ROOT::Math::PxPyPzE4D<double>')(px, py, pz, pe)
        elif ndim == _EUCLID_DIM:
            [px, py, pz    ] = arr_val.tolist()
            vector = XYZVector(px, py, pz)
        else:
            raise NotImplementedError(f'Invalid dimentionality: {ndim}')

        return vector
    # -------------------------------
    def _get_xvector(self, name : str, ndim : int) -> list:
        '''
        Parameters
        -----------------
        name: Identifier of the object, i.e L1_P, Hadrons, etc.
        ndim: Number of dimensions for associated vector

        Returns
        -----------------
        List of vectors in dataframe, associated to object
        '''
        project = self._trigger.project

        if   name == 'Hadrons' and project in [Project.rkst, Project.rkst_no_pid]:
            l_h1 = self._get_xvector(name='H1_P', ndim=ndim)
            l_h2 = self._get_xvector(name='H2_P', ndim=ndim)
            l_hh = [ h1 + h2 for h1, h2 in zip(l_h1, l_h2, strict = True) ]

            return l_hh
        elif name == 'Hadrons' and project in [Project.rk, Project.rk_no_pid]:
            name = 'H_P'
        elif name in ['L1_P', 'L2_P', 'H1_P', 'H2_P', 'B_BPV', 'B_END_V']:
            pass
        else:
            raise ValueError(f'Invalid project/name: {project}/{name}')

        if   ndim == _LORENTZ_DIM:
            l_branch = [f'{name}X', f'{name}Y', f'{name}Z', f'{name}E']
        elif ndim == _EUCLID_DIM:
            l_branch = [f'{name}X', f'{name}Y', f'{name}Z']
        else:
            raise NotImplementedError(f'Invalid ndim={ndim}')

        d_data   = self._rdf.AsNumpy(l_branch)
        l_array  = [ d_data[branch] for branch in l_branch ]
        arr_dat  = numpy.array(l_array).T
        l_vec    = [ self._val_to_vector(arr_val, ndim) for arr_val in arr_dat ]

        return l_vec
    # -------------------------------
    def _get_alpha(
        self,
        pv : XYZVector,
        sv : XYZVector,
        l1 : LorentzVector,
        l2 : LorentzVector,
        hd : LorentzVector) -> float:
        '''
        Parameters
        -----------------
        pv(sv): 3D vector corresponding to position of primary (secondary) vertex
        l1(2) : Lorentz vector for lepton
        hd    : Lorentz vector for hadronic system, for Rk, kaon, for RKstar, sum of Kaon and Pion

        Returns
        -----------------
        Ratio of transverse momentum, (in reference frame perpendicular to direction of flight of B meson)
        of dilepton and hadronic system
        '''
        l1_3v     = l1.Vect()
        l2_3v     = l2.Vect()
        ll_3v     = l1_3v + l2_3v
        hd_3v     = hd.Vect()
        bp_dr     = sv - pv

        cos_thhad = bp_dr.Dot(hd_3v) / (hd_3v.R() * bp_dr.R())
        sin_thhad = math.sqrt(1.0 - cos_thhad ** 2)
        had_pt    = hd_3v.R() * sin_thhad

        cos_thll  = bp_dr.Dot(ll_3v) / (ll_3v.R() * bp_dr.R())
        sin_thll  = math.sqrt(1.0 - cos_thll ** 2 )
        ll_pt     = ll_3v.R() * sin_thll

        alpha     = had_pt / ll_pt if ll_pt > 0. else 1.0

        return alpha
    # -------------------------------
    def _correct_kinematics(self, alpha : float, particle : LorentzVector) -> LorentzVector:
        px = alpha * particle.px()
        py = alpha * particle.py()
        pz = alpha * particle.pz()
        ms =         particle.M()

        return LorentzVector('ROOT::Math::PxPyPzM4D<double>')(px, py, pz, ms)
    # -------------------------------
    def _get_values(self) -> tuple[list[float], list[float]]:
        l_l1 = self._get_xvector(ndim=4, name='L1_P'   )
        l_l2 = self._get_xvector(ndim=4, name='L2_P'   )
        l_hd = self._get_xvector(ndim=4, name='Hadrons')
        l_pv = self._get_xvector(ndim=3, name='B_BPV'  )
        l_sv = self._get_xvector(ndim=3, name='B_END_V')

        l_alpha = []
        l_mass  = []
        for pv, sv, l1, l2, hd in zip(l_pv, l_sv, l_l1, l_l2, l_hd, strict=True):
            alpha   = self._get_alpha(pv, sv, l1, l2, hd)
            l1_corr = self._correct_kinematics(alpha, l1)
            l2_corr = self._correct_kinematics(alpha, l2)
            mass    = (l1_corr + l2_corr + hd).M()

            l_alpha.append(alpha)
            l_mass.append(mass)

        return l_alpha, l_mass
    # -------------------------------
    def get_rdf(self, preffix : str) -> RDF.RNode:
        '''
        Parameters
        ----------------
        prefix: Prefix used for HOP variables, i.e. {prefix}_alpha, {prefix}_mass, ...

        Returns
        ----------------
        ROOT dataframe with HOP variables
        '''

        l_alpha, l_mass = self._get_values()
        arr_alpha       = numpy.array(l_alpha)
        arr_mass        = numpy.array(l_mass )
        d_data          = {f'{preffix}_alpha' : arr_alpha, f'{preffix}_mass' : arr_mass}

        # Add EVENTNUMBER, RUNNUMBER, etc
        d_ext           = self._rdf.AsNumpy(self._extra_branches)
        d_data.update(d_ext)

        rdf = RDF.FromNumpy(d_data)

        return rdf
# -------------------------------
