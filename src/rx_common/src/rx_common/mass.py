'''
Module holding Mass class
'''
from enum      import StrEnum, auto
from dmu.stats import zfit
from functools import cached_property

from .qsq      import Qsq
from .project  import Project
from .trigger  import Trigger

zobs = zfit.Space
# -----------------------------------
class Mass(StrEnum):
    '''
    Class meant to represent variables found in ROOT trees

    Attributes
    -----------------
    lb/b         : Lambda/B meson mass
    lb/b_dtf_jpsi: Lambda/B meson mass with DTF constraint on Jpsi mass
    b_bcor       : B meson mass with brem corrected electrons
    b_bcor_smr   : B meson mass with brem correction and smearing

    Attributes for MisID
    -----------------
    b_bcorr_pipi : B meson mass with electrons reconstructed as pions
    b_bcorr_kk   : B meson mass with electrons reconstructed as kaons
    '''
    bp           = auto()
    '''B+ mass'''
    bp_dtf_jpsi  = auto()
    '''B+ mass with DTF constraint on Jpsi mass'''
    bp_dtf_psi2  = auto()
    '''B+ mass with DTF constraint on psi2S mass'''
    bp_bcor      = auto()
    '''B+ mass with brem corrected electrons'''
    bp_bcor_smr  = auto()
    '''B+ mass with brem correction and smearing'''
    bp_kk        = auto()
    '''B+ mass with electrons reconstructed as kaons'''
    bp_pipi      = auto()
    '''B+ mass with electrons reconstructed as pions'''

    bd           = auto()
    '''B0 mass'''
    bd_dtf_jpsi  = auto()
    '''B0 mass with DTF constraint on Jpsi mass'''
    bd_dtf_psi2  = auto()
    '''B0 mass with DTF constraint on psi2S mass'''
    bd_bcor      = auto()
    '''B0 mass with brem corrected electrons'''
    bd_bcor_smr  = auto()
    '''B0 mass with brem correction and smearing'''
    bd_kk        = auto()
    '''B0 mass with electrons reconstructed as kaons'''
    bd_pipi      = auto()
    '''B0 mass with electrons reconstructed as pions'''

    swp_kmm_mkm  = auto()
    '''Mass of Kmu pair for Kmumu final states where
    kaon and muon are swapped and kaon is given muon
    mass hypothesis'''
    # ------------------------------
    @property
    def branch_name(self) -> str:
        '''
        Branch name in ROOT trees
        '''
        match self:
            case Mass.bp | Mass.bd:
                return 'B_M'
            case Mass.bp_dtf_jpsi | Mass.bd_dtf_jpsi:
                return 'B_const_mass_M'
            case Mass.bp_dtf_psi2 | Mass.bd_dtf_psi2:
                return 'B_const_mass_psi2S_M'
            case Mass.bp_bcor | Mass.bd_bcor:
                return 'B_Mass'
            case Mass.bp_bcor_smr | Mass.bd_bcor_smr:
                return 'B_Mass_smr'
            case Mass.bp_kk | Mass.bd_kk:
                return 'B_Mass_hdkk'
            case Mass.bp_pipi | Mass.bd_pipi:
                return 'B_Mass_hdpipi'
            case Mass.swp_kmm_mkm:
                return 'swp_jpsi_misid_mass_swp'
            case _:
                raise ValueError(f'Cannot determine branch name for: {self}')
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
        return '_dtf_' in self.name
    # ------------------------------
    @property
    def smeared_version(self) -> 'Mass':
        '''
        Smeared version of mass
        '''
        if self.name.endswith('_smr'):
            raise ValueError(f'Current mass is already smeared: {self.name}')

        smeared_name = f'{self.name}_smr'

        try:
            mass = Mass[smeared_name]
        except Exception as exc:
            raise ValueError(f'Cannot find mass: {smeared_name}') from exc

        return mass
    # ------------------------------
    @cached_property
    def obs(self) -> zobs:
        '''
        zfit observable associated with mass
        '''
        obs = zfit.Space(
            obs    = self.latex,
            label  = self.name,
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
            # Swap masses
            # ------------
            case Mass.swp_kmm_mkm:
                return r'$M(K_{\to\ell},\ell)$'
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
        match self:
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
            case Mass.swp_kmm_mkm:
                return 2600, 3300
            case _:
                raise ValueError(f'Cannot determine mass range for: {self}')
# ------------------------------
class MassDef(StrEnum):
    '''Meant to represent way in which
    masses were calculated'''

    default = auto()
    '''No correction applied on top of what DaVinci does'''

    brem_corr = auto()
    '''From electrons to which custom brem recovery was applied
    needed in 2024 data'''
    # ---------------------
    def mass_from_trigger(self, trigger : Trigger) -> Mass:
        '''
        Parameters
        ---------------
        trigger: Hlt2 trigger

        Returns
        ---------------
        Specific version of mass associated to both this MassDef and the passed trigger
        '''
        if trigger.is_muon and self == MassDef.default and trigger.project == Project.rk:
            return Mass.bp

        if trigger.is_muon and self == MassDef.default and trigger.project == Project.rkst:
            return Mass.bd

        if trigger.is_muon:
            raise ValueError(f'Invalid trigger {trigger} for mass definition {self}')

        if trigger.is_electron and self == MassDef.default and trigger.project == Project.rk:
            return Mass.bp

        if trigger.is_electron and self == MassDef.default and trigger.project == Project.rkst:
            return Mass.bd

        if trigger.is_electron and self == MassDef.brem_corr and trigger.project == Project.rk:
            return Mass.bp_bcor

        if trigger.is_electron and self == MassDef.brem_corr and trigger.project == Project.rkst:
            return Mass.bd_bcor

        raise ValueError(f'Invalid trigger/mass definition combination: {trigger}/{self}')
# -----------------------------------
