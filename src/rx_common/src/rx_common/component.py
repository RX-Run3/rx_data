'''
Module holding Component and CCbarComponent
'''

from functools import cache
from enum      import StrEnum, auto
from typing    import Literal

from .channel            import Channel
from ap_utilities.decays import utilities as aput

# -------------------------------
class MissingComponent(Exception):
    '''
    Exception meant to be raised when a component does
    not exist for a given MC sample
    '''
# -------------------------------
@cache
def _get_samples() -> dict[str,'Component']:
    '''
    Returns
    ----------------
    mapping between sample name and component
    '''
    return { cmp.sample : cmp for cmp in Component if cmp.has_sample }
# -------------------------------
class Component(StrEnum):
    '''
    Class meant to represent decay

    Naming constraints:

    - Except for data, undefined and combinatorial, all samples meant to be used with the electron/muon channel should end with ee/mm
    '''
    undefined      = auto()
    comb           = auto()
    ccbar          = auto()
    # -----
    # Data
    # -----
    data_24        = auto()
    data_24_mu_c1  = auto()
    data_24_mu_c2  = auto()
    data_24_mu_c3  = auto()
    data_24_mu_c4  = auto()
    data_24_md_c1  = auto()
    data_24_md_c2  = auto()
    data_24_md_c3  = auto()
    data_24_md_c4  = auto()
    # -----
    bpkkk          = auto()
    bpkpik         = auto()
    bpkpipi        = auto()
    # -----
    bpkpee         = auto()
    bpkpjpsiee     = auto()
    bpkppsi2ee     = auto()
    bpkpipiee      = auto()
    # -----
    bppijpsimm     = auto()
    bppijpsiee     = auto()
    # -----
    bpkpmm         = auto()
    bpkpjpsimm     = auto()
    bpkppsi2mm     = auto()
    # -----
    bdkstkpiee     = auto()
    bdkstkpijpsiee = auto()
    bdkstkpipsi2ee = auto()
    # -----
    bdkstkpimm     = auto()
    bdkstkpijpsimm = auto()
    bdkstkpipsi2mm = auto()
    # -----
    bpk1kpipiee    = auto()
    bpk2kpipiee    = auto()
    bpkxkpipiee    = auto()
    bpkstkpiee     = auto()
    bsphiee        = auto()
    # -----
    bpjpsixee      = auto()
    bdjpsixee      = auto()
    bsjpsixee      = auto()
    # -----
    bpjpsixmm      = auto()
    bdjpsixmm      = auto()
    bsjpsixmm      = auto()
    # -----
    bsphijpsimm    = auto()
    bsphijpsiee    = auto()
    # -----
    lbpkjpsimm     = auto()
    lbpkjpsiee     = auto()
    # -----
    # Emulated
    # -----
    bskstjpsimm    = auto()
    bskstjpsiee    = auto()

    bdkstjpsimm_swp= auto()
    bdkstjpsiee_swp= auto()
    # -----
    # Semileptonic
    # -----
    bpdnuknumm     = auto()
    bpdpiknumm     = auto()
    bpdnukpiee     = auto()
    bpdpiknuee     = auto()
    bpdnuknuee     = auto()
    # -----
    # Radiative
    # -----
    bdkstpi0       = auto()
    bsphigamma     = auto()
    # --------------------------------------------
    @property
    def scale(self) -> str:
        '''
        Name of scale parameter for this component's yield
        This makes sense when the component is constrained
        with respect to the signal
        '''
        return f's_{self.value}'
    # --------------------------------------------
    @classmethod
    def from_sample(cls, sample : str) -> 'Component':
        '''
        Parameters
        ----------------
        sample: String representing MC sample

        Returns
        ----------------
        Corresponding component
        '''
        samples = _get_samples()

        if sample in samples:
            return samples[sample]

        raise MissingComponent(f'Cannot find component for: {sample}')
    # --------------------------------------------
    @classmethod
    def has_component(cls, sample :  str) -> bool:
        '''
        Parameters
        ----------------
        sample: String representing MC sample

        Returns
        ----------------
        True if this sample is associated to fitting component
        '''

        return sample in _get_samples()
    # --------------------------------------------
    @property
    def has_sample(self) -> bool:
        '''
        True if there is a sample, MC or Data, associated to component
        '''
        if self in {Component.undefined, Component.comb, Component.ccbar}:
            return False

        return True
    # --------------------------------------------
    @property
    def is_mc(self) -> bool:
        '''
        True for simulated sample, false for real data
        '''

        if self in [
            Component.data_24,
            Component.data_24_mu_c1,
            Component.data_24_mu_c2,
            Component.data_24_mu_c3,
            Component.data_24_mu_c4,
            Component.data_24_md_c1,
            Component.data_24_md_c2,
            Component.data_24_md_c3,
            Component.data_24_md_c4]:
            return False

        return True
    # --------------------------------------------
    @property
    def event_type(self) -> str:
        '''
        Event type associated to MC
        It will raise on data
        '''
        if not self.is_mc:
            raise ValueError(f'Current sample is not MC but: {self}')

        return aput.read_event_type(nickname = self.sample)
    # --------------------------------------------
    @property
    def sample(self) -> str:
        match self:
          case Component.data_24:
            return 'DATA_24*'
          case Component.data_24_mu_c1:
            return 'DATA_24_MagUp_24c1'
          case Component.data_24_md_c1:
            return 'DATA_24_MagDown_24c1'
          case Component.data_24_mu_c2:
            return 'DATA_24_MagUp_24c2'
          case Component.data_24_md_c2:
            return 'DATA_24_MagDown_24c2'
          case Component.data_24_mu_c3:
            return 'DATA_24_MagUp_24c3'
          case Component.data_24_md_c3:
            return 'DATA_24_MagDown_24c3'
          case Component.data_24_mu_c4:
            return 'DATA_24_MagUp_24c4'
          case Component.data_24_md_c4:
            return 'DATA_24_MagDown_24c4'
          # -----
          case Component.bpkkk:
            return 'Bu_KplKplKmn_eq_sqDalitz_DPC'
          case Component.bpkpipi:
            return 'Bu_piplpimnKpl_eq_sqDalitz_DPC'
          case Component.bpkpik:
            return 'Bu_KplpiplKmn_eq_sqDalitz_DPC'
          # -----
          case Component.bpkpee:
            return 'Bu_Kee_eq_btosllball05_DPC'
          case Component.bpkpjpsiee:
            return 'Bu_JpsiK_ee_eq_DPC'
          case Component.bpkppsi2ee:
            return 'Bu_psi2SK_ee_eq_DPC'
          case Component.bpkpipiee:
            return 'Bu_Kpipiee_eq_DPC_LSFLAT'
          # -----
          case Component.bppijpsimm:
            return 'Bu_JpsiPi_mm_eq_DPC'
          case Component.bppijpsiee:
            return 'Bu_JpsiPi_ee_eq_DPC'
          # -----
          case Component.bpkpmm:
            return 'Bu_Kmumu_eq_btosllball05_DPC'
          case Component.bpkpjpsimm:
            return 'Bu_JpsiK_mm_eq_DPC'
          case Component.bpkppsi2mm:
            return 'Bu_psi2SK_mm_eq_DPC'
          # -----
          case Component.bdkstkpiee:
            return 'Bd_Kstee_eq_btosllball05_DPC'
          case Component.bdkstkpijpsiee:
            return 'Bd_JpsiKst_ee_eq_DPC'
          case Component.bdkstkpipsi2ee:
            return 'Bd_psi2SKst_ee_eq_DPC'
          # -----
          case Component.bdkstkpimm:
            return 'Bd_Kstmumu_eq_btosllball05_DPC'
          case Component.bdkstkpijpsimm:
            return 'Bd_JpsiKst_mm_eq_DPC'
          case Component.bdkstkpipsi2mm:
            return 'Bd_psi2SKst_mm_eq_DPC'
          # -----
          case Component.bpk1kpipiee:
            return 'Bu_K1ee_eq_DPC'
          case Component.bpk2kpipiee:
            return 'Bu_K2stee_Kpipi_eq_mK1430_DPC'
          case Component.bpkxkpipiee:
            return 'Bu_KxKpipiee'
          case Component.bpkstkpiee:
            return 'Bu_Kstee_Kpi0_eq_btosllball05_DPC'
          case Component.bsphiee:
            return 'Bs_phiee_eq_Ball_DPC'
          # -----
          case Component.bpjpsixee:
            return 'Bu_JpsiX_ee_eq_JpsiInAcc'
          case Component.bdjpsixee:
            return 'Bd_JpsiX_ee_eq_JpsiInAcc'
          case Component.bsjpsixee:
            return 'Bs_JpsiX_ee_eq_JpsiInAcc'
          # -----
          case Component.bpjpsixmm:
            return 'Bu_JpsiX_mm_eq_JpsiInAcc'
          case Component.bdjpsixmm:
            return 'Bd_JpsiX_mm_eq_JpsiInAcc'
          case Component.bsjpsixmm:
            return 'Bs_JpsiX_mm_eq_JpsiInAcc'
          # -----
          case Component.bsphijpsimm:
            return 'Bs_Jpsiphi_mm_eq_CPV_update2012_DPC'
          case Component.bsphijpsiee:
            return 'Bs_Jpsiphi_ee_eq_CPV_update2012_DPC'
          # -----
          case Component.lbpkjpsimm:
            return 'Lb_JpsipK_mm_eq_phsp_DPC'
          case Component.lbpkjpsiee:
            return 'Lb_JpsipK_ee_eq_phsp_DPC'
          # -----
          case Component.bpdnuknumm:
            return 'Bu_D0munu_Kmunu_eq_DPC'
          case Component.bpdpiknumm:
            return 'Bu_D0pi_Kmunu_eq_DPC'
          case Component.bpdnukpiee:
            return 'Bu_D0enu_Kpi_eq_DPC_TC'
          case Component.bpdpiknuee:
            return 'Bu_D0pi_Kenu_eq_DPC_TC'
          case Component.bpdnuknuee:
            return 'Bu_D0enu_Kenu_eq_DPC_ptCut200MeV_visMass4G'
          # -----
          # Emulated samples
          # -----
          case Component.bskstjpsimm:
            return 'Bs_JpsiKst_mm_eq_DPC'
          case Component.bskstjpsiee:
            return 'Bs_JpsiKst_ee_eq_DPC'
          case Component.bdkstjpsimm_swp:
            return 'Bd_JpsiKst_mm_had_swp'
          case Component.bdkstjpsiee_swp:
            return 'Bd_JpsiKst_ee_had_swp'
          case Component.bdkstpi0:
            return 'Bd_Kstpi0_eq_TC_Kst982width100_HighPtPi0'
          case Component.bsphigamma:
            return 'Bs_phigamma_eq_HighPtGamma_DPC'
          case _:
            raise ValueError(f'No sample defined for: {self}')
    # --------------------------------------------
    @property
    def subdecays(self) -> list[str]:
        '''
        Returns list of subdecays
        '''
        match self.name:
            case 'bpkpee':
                return ['bpkp']
            case 'bpkpmm':
                return ['bpkp']
            case 'bdkstkpiee':
                return ['bdks', 'k+kp']
            case 'bdkstkpimm':
                return ['bdks', 'k+kp']
            # ------
            case 'bpkpjpsiee':
                return ['bpjk', 'jpee']
            case 'bpkpjpsimm':
                return ['bpjk', 'jpmm']
            case 'bpkppsi2ee':
                return ['bppsk', 'psee']
            case 'bpkppsi2mm':
                return ['bppsk', 'psmm']
            # ------
            case 'bdkstkpijpsiee':
                return ['bdjkst' , 'jpee', 'kstkpi']
            case 'bdkstkpijpsimm':
                return ['bdjkst' , 'jpmm', 'kstkpi']
            case 'bdkstkpipsi2ee':
                return ['bdpskst', 'psee', 'kstkpi']
            case 'bdkstkpipsi2mm':
                return ['bdpskst', 'psmm', 'kstkpi']
            # ------
            case 'bsphiee':
                return ['bsph', 'phkk']
            case 'bpk1kpipiee':
                return ['bpk1', 'k13h']
            case 'bpk2kpipiee':
                return ['bpk2', 'k23h']
            case 'bpkstkpiee':
                return ['bpks', 'kokp']
            case _:
                raise NotImplementedError(f'Cannot find subdecays for: {self.name}')
    # --------------------------------------------
    @classmethod
    def get_mc_samples(cls) -> list['Component']:
        '''
        Returns
        ---------------
        List of MC samples known to analysis
        '''
        return [ sample for sample in cls if sample.has_mc() ]
    # --------------------------------------------
    def has_mc(self) -> bool:
        if self in [Component.undefined, Component.comb, Component.data_24]:
            return False

        return True
    # --------------------------------------------
    def __str__(self):
        '''
        Returns
        ----------------
        String representing sample name, e.g. bpkpee
        '''
        return self.name
    # --------------------------------------------
    @property
    def latex(self) -> str:
        '''
        Returns
        ----------------
        Latex string for decay associated to sample
        '''
        match self:
            case Component.bpkpjpsiee:
                return r'$B^+\to K^+J/\psi(\to e^+e^-)$'
            case Component.bpkpjpsimm:
                return r'$B^+\to K^+J/\psi(\to \mu^+\mu^-)$'
            case Component.bpkpee:
                return r'$B^+\to K^+e^+e^-$'
            case Component.bpkpmm:
                return r'$B^+\to K^+\mu^+\mu^-$'
            case _:
                return self.name
    # --------------------------------------------
    @property
    def channel(self) -> Channel:
        '''
        Returns
        ----------------
        Channel to which current sample belongs
        '''
        if self.name.endswith('ee'):
            return Channel.ee

        if self.name.endswith('mm'):
            return Channel.mm

        raise ValueError(f'Sample {self} does not belong to electron or muon Channel')
    # --------------------------------------------
    @classmethod
    def inclusive(cls, channel : Channel) -> list['CCbarComponent']:
        '''
        Parameters
        --------------
        channel: E.g. ee, mm

        Returns
        --------------
        List of charmonium components
        '''
        if channel == Channel.ee:
            return [
                Component.bpjpsixee,
                Component.bdjpsixee,
                Component.bsjpsixee]

        if channel == Channel.mm:
            return [
                Component.bpjpsixmm,
                Component.bdjpsixmm,
                Component.bsjpsixmm]

        raise ValueError(f'Invalid channel: {channel}')
# --------------------------------------------
CCbarComponent = Literal[
    Component.bpjpsixee,
    Component.bdjpsixee,
    Component.bsjpsixee,
    # --------
    Component.bpjpsixmm,
    Component.bdjpsixmm,
    Component.bsjpsixmm]
