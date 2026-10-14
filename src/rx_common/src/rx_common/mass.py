'''
Module holding Mass class
'''
from enum      import StrEnum
from dmu.stats import zfit
from functools import cached_property

from .qsq      import Qsq
from .project  import Project

zobs = zfit.Space
# -----------------------------------
class Mass(StrEnum):
    '''
    Class meant to represent variables found in ROOT trees

    Attributes
    -----------------
    lb/b         : Lambda/B meson mass
    lb/b_dtf_jpsi: Lambda/B meson mass with DTF constraint on Jpsi mass
    b            : Generic B mass as taken from DaVinci, no corrections
    b_bcor       : B meson mass with brem corrected electrons
    b_bcor_smr   : B meson mass with brem correction and smearing

    Attributes for MisID
    -----------------
    b_bcorr_pipi : B meson mass with electrons reconstructed as pions
    b_bcorr_kk   : B meson mass with electrons reconstructed as kaons
    '''

    lb_dtf_jpsi  = 'Lb_cons_Jpsi_M'
    lb           = 'Lb_M'

    b            = 'B_M'

    bp           = 'B_M'
    bp_dtf_jpsi  = 'B_const_mass_M'
    bp_dtf_psi2  = 'B_const_mass_psi2S_M'
    bp_bcor      = 'B_Mass'
    bp_bcor_smr  = 'B_Mass_smr'
    bp_kk        = 'B_Mass_hdkk'
    bp_pipi      = 'B_Mass_hdpipi'

    bd           = 'B_M'
    bd_dtf_jpsi  = 'B_const_mass_M'
    bd_dtf_psi2  = 'B_const_mass_psi2S_M'
    bd_bcor      = 'B_Mass'
    bd_bcor_smr  = 'B_Mass_smr'
    bd_kk        = 'B_Mass_hdkk'
    bd_pipi      = 'B_Mass_hdpipi'
    # ------------------------------
    @classmethod
    def dtf_from_qsq(cls, qsq : Qsq, project : Project) -> 'Mass':
        '''
        Parameters
        -----------------
        qsq    : q2-bin
        project: E.g. rk or rkst

        Returns
        -----------------
        DTF mass type for given q2-bin
        '''
        if project == Project.rk   and qsq == Qsq.jpsi:
            return Mass.bp_dtf_jpsi

        if project == Project.rk   and qsq == Qsq.psi2:
            return Mass.bp_dtf_psi2

        if project == Project.rkst and qsq == Qsq.jpsi:
            return Mass.bd_dtf_jpsi

        if project == Project.rkst and qsq == Qsq.psi2:
            return Mass.bd_dtf_psi2

        raise ValueError(f'Invalid project/q2-bin: {project}/{qsq}')
    # ------------------------------
    @classmethod
    def raw_from_project(cls, project : Project) -> 'Mass':
        '''
        Parameters
        -----------------
        project: E.g. rk or rkst

        Returns
        -----------------
        Raw mass type for given project 
        '''
        if project == Project.rk  :
            return Mass.bp_bcor

        if project == Project.rkst:
            return Mass.bd_bcor

        raise ValueError(f'Invalid project: {project}')
    # ------------------------------
    @property
    def is_dtf(self) -> bool:
        '''
        True if it is a mass with DTF constraints
        '''
        return '_const_' in self
    # ------------------------------
    @property
    def smeared_version(self) -> 'Mass':
        '''
        Smeared version of mass
        '''
        if self.endswith('_smr'):
            raise ValueError(f'Current mass is already smeared: {self}')

        smeared_value = f'{self.value}_smr'

        try:
            mass = Mass(value = smeared_value)
        except Exception as exc:
            raise ValueError(f'Cannot find mass: {smeared_value}') from exc

        return mass
    # ------------------------------
    @cached_property
    def obs(self) -> zobs:
        '''
        zfit observable associated with mass
        '''
        obs = zfit.Space(
            obs    = self.value,
            label  = self.latex,
            limits = self.limits)

        return obs
    # ------------------------------
    @property
    def latex(self) -> str:
        '''
        Latex string, for x-axis label
        '''
        match self:
            # ------------
            # Lambda_b
            # ------------
            case Mass.lb_dtf_jpsi:
                return r'$M_{DTF}^{J/\psi}(\Lambda_b)$'
            case Mass.lb:
                return r'$M(\Lambda_b)$'
            # ------------
            # B+
            # ------------
            case Mass.bp:
                return r'$M(B^+)$'
            case Mass.bp_dtf_jpsi:
                return r'$M_{DTF}^{J/\psi}(B^+)$'
            case Mass.bp_dtf_psi2:
                return r'$M_{DTF}^{\psi(2S)}(B^+)$'
            case Mass.bp_bcor:
                return r'$M_{corr}(B^+)$'
            case Mass.bp_bcor_smr:
                return r'$M_{corr}^{smr}(B^+)$'
            case Mass.bp_kk:
                return r'$M^{KK}(B^+)$'
            case Mass.bp_pipi:
                return r'$M^{\pi\pi}(B^+)$'
            # ------------
            # B0
            # ------------
            case Mass.bd:
                return r'$M(B^0)$'
            case Mass.bd_dtf_jpsi:
                return r'$M_{DTF}^{J/\psi}(B^0)$'
            case Mass.bd_dtf_psi2:
                return r'$M_{DTF}^{\psi(2S)}(B^0)$'
            case Mass.bd_bcor:
                return r'$M_{corr}(B^0)$'
            case Mass.bd_bcor_smr:
                return r'$M_{corr}^{smr}(B^0)$'
            case Mass.bd_kk:
                return r'$M^{KK}(B^0)$'
            case Mass.bd_pipi:
                return r'$M^{\pi\pi}(B^0)$'
            case _:
                raise ValueError(f'Cannot determine latex for: {self}')
    # ------------------------------
    @property
    def limits(self) -> tuple[float,float]:
        '''
        Range used for observable limits
        '''
        generic = 5000, 6000

        match self:
            # ------------
            # Lambda_b
            # ------------
            case Mass.lb_dtf_jpsi:
                return generic
            case Mass.lb:
                return generic
            # ------------
            # B+
            # ------------
            case Mass.bp:
                return 4600, 7000
            case Mass.bp_dtf_jpsi:
                return 5080, 5680
            case Mass.bp_dtf_psi2:
                return 5150, 5850
            case Mass.bp_bcor:
                return Mass.bp.limits
            case Mass.bp_bcor_smr:
                return Mass.bp.limits
            case Mass.bp_kk:
                return 4800, 6500
            case Mass.bp_pipi:
                return Mass.bp_kk.limits
            # ------------
            # B0
            # ------------
            case Mass.bd:
                return 4600, 7000
            case Mass.bd_dtf_jpsi:
                return 5080, 5680
            case Mass.bd_dtf_psi2:
                return 5150, 5850
            case Mass.bd_bcor:
                return Mass.bd.limits
            case Mass.bd_bcor_smr:
                return Mass.bd.limits
            case Mass.bd_kk:
                return 4800, 6500
            case Mass.bd_pipi:
                return Mass.bd_kk.limits
            case _:
                raise ValueError(f'Cannot determine mass range for: {self}')
# ------------------------------
