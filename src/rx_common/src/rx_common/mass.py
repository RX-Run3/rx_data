'''
Module holding Mass class
'''
from enum      import StrEnum
from dmu.stats import zfit
from functools import cached_property

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

    lb_dtf_jpsi  = 'Lb_cons_Jpsi_M'
    lb           = 'Lb_M'

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
    @cached_property
    def obs(self) -> zobs:
        '''
        zfit observable associated with mass
        '''
        obs = zfit.Space(
            obs    = 'mass',
            label  = self,
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
                return 4500, 7000
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
                return 4500, 7000
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
