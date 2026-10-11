'''
Module holding Component and CCbarComponent
'''

from functools           import cache
from enum                import StrEnum, auto
from typing              import Literal
from ap_utilities.decays import utilities as aput
from pathlib             import Path

from .channel            import Channel
from .branching_fraction import BranchingFraction

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
    mc             = auto()
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
    bdkpipi        = auto()
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
    bppsi2xee      = auto()
    bdpsi2xee      = auto()
    bspsi2xee      = auto()
    # -----
    bpjpsixmm      = auto()
    bdjpsixmm      = auto()
    bsjpsixmm      = auto()
    # -----
    bppsi2xmm      = auto()
    bdpsi2xmm      = auto()
    bspsi2xmm      = auto()
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
    bskstpsi2mm    = auto()
    bskstpsi2ee    = auto()

    bdkstjpsimm_had_swp= auto()
    bdkstjpsiee_had_swp= auto()

    bdkstjpsimm_mix_swp= auto()
    bdkstjpsiee_mix_swp= auto()

    bpkpjpsimm_mix_swp = auto()
    bpkpjpsiee_mix_swp = auto()
    # -----
    # Semileptonic
    # -----
    bpdnuknumm     = auto()
    bpdpiknumm     = auto()
    # ------
    bpdnukpiee     = auto()
    bpdpiknuee     = auto()
    bpdnuknuee     = auto()
    # ------
    bdkpipienu     = auto()
    bdkpienuenu    = auto()
    bdkpimunumunu  = auto()
    # -----
    # Radiative
    # -----
    bdkstpi0       = auto()
    bsphigamma     = auto()
    # --------------------------------------------
    @property
    def metadata(self) -> dict[str,str]:
        '''
        Dictionary with basic information on component:

        Event Type, Decay
        '''
        return { 'Event Type' : self.event_type, 'Decay' : self.latex }
    # --------------------------------------------
    @classmethod
    def is_valid(cls, arg : int | str) -> bool:
        '''
        Parameters
        ---------------
        arg: Either the event type or a string

        Returns
        ---------------
        True if argument represents a valid sample
        '''
        if isinstance(arg, int):
            try:
                cls.from_event_type(arg)
                return True
            except:
                return False

        if isinstance(arg, str):
            try:
                cls.from_sample(arg)
                return True
            except:
                return False
    # --------------------------------------------
    @property
    def is_composed(self) -> bool:
        '''
        If true, this sample is made of subsamples, e.g. ccbar or data_24
        '''
        if self in { Component.data_24, Component.bpkxkpipiee }:
            return True

        return False
    @property
    # --------------------------------------------
    def subsamples(self) -> list['Component']:
        '''
        If not a composite sample, list with itself
        If it is composite, list with components
        '''
        if not self.is_composed:
            return [self]

        if self == Component.data_24:
            return [
                Component.data_24_md_c2, Component.data_24_mu_c2,
                Component.data_24_md_c3, Component.data_24_mu_c3,
                Component.data_24_md_c4, Component.data_24_mu_c4]

        if self == Component.bpkxkpipiee:
            return [Component.bpk1kpipiee, Component.bpk2kpipiee]

        raise ValueError(f'The code should not reach this place: {self}')
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
        sample: String representing MC sample, can be lower or mixed case

        Returns
        ----------------
        Corresponding component
        '''
        sample  = sample.lower()
        sample  = aput.name_from_lower_case(lower_case = sample)
        samples = _get_samples()

        if sample in samples:
            return samples[sample]

        raise MissingComponent(f'Cannot find component for: {sample}')
    # --------------------------------------------
    @classmethod
    def from_event_type(cls, etype : int) -> 'Component':
        '''
        Parameters
        -----------------
        etype: Event type

        Returns
        -----------------
        Instance of component
        '''
        sample = aput.read_decay_name(event_type = etype)

        return cls.from_sample(sample = sample)
    # --------------------------------------------
    @classmethod
    def from_path(cls, path : Path) -> 'Component':
        '''
        Parameters
        ----------------
        path: Path to file

        Returns
        ----------------
        Component whose name is part of the path as '/{component}/'
        '''
        components : list['Component'] = []
        for comp in cls:
            if f'/{comp}/' not in str(path):
                continue

            components.append(comp)

        if len(components) != 1:
            raise ValueError(f'Not found one and only one component in: {path}')

        return components[0]
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
        components = {
            Component.bppsi2xee,
            Component.bdpsi2xee,
            Component.bspsi2xee,
            # ---------------
            Component.bppsi2xmm,
            Component.bdpsi2xmm,
            Component.bspsi2xmm,
            # ---------------
            Component.undefined, 
            Component.comb, 
            Component.ccbar, 
            Component.mc}

        if self in components:
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
            return 'Bd_JpsiKst_update2012_ee_eq_DPC'
          case Component.bdkstkpipsi2ee:
            return 'Bd_psi2SKst_ee_eq_DPC'
          # -----
          case Component.bdkstkpimm:
            return 'Bd_Kstmumu_eq_btosllball05_DPC'
          case Component.bdkstkpijpsimm:
            return 'Bd_JpsiKst_update2012_mm_eq_DPC'
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
          # -----
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
          # -------
          case Component.bskstpsi2mm:
            return 'Bs_psi2SKst_mm_eq_DPC'
          case Component.bskstpsi2ee:
            return 'Bs_psi2SKst_ee_eq_DPC'
          # -------
          case Component.bdkstjpsimm_had_swp:
            return 'Bd_JpsiKst_mm_had_swp'
          case Component.bdkstjpsiee_had_swp:
            return 'Bd_JpsiKst_ee_had_swp'
          # -------
          case Component.bdkstjpsimm_mix_swp:
            return 'Bd_JpsiKst_mm_mix_swp'
          case Component.bdkstjpsiee_mix_swp:
            return 'Bd_JpsiKst_ee_mix_swp'
          # -------
          case Component.bpkpjpsimm_mix_swp:
            return 'Bu_JpsiK_mm_eq_DPC_mix_swp'
          case Component.bpkpjpsiee_mix_swp:
            return 'Bu_JpsiK_ee_eq_DPC_mix_swp'
          # -------
          case Component.bdkstpi0:
            return 'Bd_Kstpi0_eq_TC_Kst982width100_HighPtPi0'
          case Component.bsphigamma:
            return 'Bs_phigamma_eq_HighPtGamma_DPC'
          case Component.bdkpipienu:
            return 'Bd_Dstplenu_eq_PHSP_TC'
          case Component.bdkpienuenu:
            return 'Bd_Denu_Kstenu_eq_VIA_HVM_EGDWC'
          case Component.bdkpimunumunu:
            return 'Bd_Dmunu_Kstmunu_eq_DPC'
          case Component.bdkpipi:
            return 'Bd_piplpimnKst_eq_sqDalitz_DPC'
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
            case 'bpkstkpiee':
                return ['bpks', 'kokp']
            case 'bsphiee':
                return ['bsph', 'phkk']
            case 'bpk1kpipiee':
                return ['bpk1', 'k13h']
            case 'bpk2kpipiee':
                return ['bpk2', 'k23h']
            # ------
            case 'bpkpjpsiee':
                return ['bpjk', 'jpee']
            case 'bpkpjpsimm':
                return ['bpjk', 'jpmm']
            # ------
            case 'bppijpsiee':
                return ['bpjp'   , 'jpee']
            case 'bppijpsimm':
                return ['bpjp'   , 'jpmm']
            case 'bdkstkpijpsiee':
                return ['bdjkst' , 'jpee', 'kokp']
            case 'bdkstjpsiee_had_swp':
                return ['bdjkst' , 'jpee', 'kokp']
            case 'bdkstkpijpsimm':
                return ['bdjkst' , 'jpmm', 'kokp']
            case 'bdkstjpsimm_had_swp':
                return ['bdjkst' , 'jpmm', 'kokp']
            case 'bskstjpsiee':
                return ['bsjkst' , 'jpee', 'kokp']
            case 'bskstjpsimm':
                return ['bsjkst' , 'jpmm', 'kokp']
            case 'bsphijpsiee':
                return ['bsphjp' , 'jpee', 'phkk']
            case 'bsphijpsimm':                 
                return ['bsphjp' , 'jpmm', 'phkk']
            case 'lbpkjpsiee':
                return ['lbpkjpsi', 'jpee']
            case 'lbpkjpsimm':
                return ['lbpkjpsi', 'jpmm']
            # ------
            case 'bpkppsi2ee':
                return ['bppsk'  , 'psee']
            case 'bpkppsi2mm':
                return ['bppsk'  , 'psmm']
            case 'bdkstkpipsi2ee':
                return ['bdpkst' , 'psee', 'kokp']
            case 'bdkstkpipsi2mm':
                return ['bdpkst' , 'psmm', 'kokp']
            case 'bskstpsi2ee':
                return ['bspkst' , 'psee', 'kokp']
            case 'bskstpsi2mm':
                return ['bspkst' , 'psmm', 'kokp']
            # ------
            case _:
                raise NotImplementedError(f'Cannot find subdecays for: {self.name}')
    # --------------------------------------------
    @property
    def brf(self) -> BranchingFraction:
        '''
        Branching fraction associated to component
        '''
        return BranchingFraction.from_decays(decays = self.subdecays, latex = self.latex)
    # --------------------------------------------
    @classmethod
    def get_mc_samples(cls) -> list['Component']:
        '''
        Returns
        ---------------
        List of MC samples known to analysis
        '''
        return [ sample for sample in cls if sample.is_mc ]
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
    def original(self) -> 'Component':
        '''
        In case this is a derived sample (e.g. from double misID)
        this method will return the original version
        '''
        if self == Component.bdkstjpsiee_had_swp:
            return Component.bdkstkpijpsiee

        if self == Component.bdkstjpsimm_had_swp:
            return Component.bdkstkpijpsimm

        return self
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
            case Component.bppijpsiee:
                return r'$B^+\to \pi^+J/\psi(\to e^+e^-)$'
            case Component.bpkpjpsimm:
                return r'$B^+\to K^+J/\psi(\to \mu^+\mu^-)$'
            case Component.bppijpsimm:
                return r'$B^+\to \pi^+J/\psi(\to \mu^+\mu^-)$'
            case Component.bpkpee:
                return r'$B^+\to K^+e^+e^-$'
            case Component.bsphiee:
                return r'$B_s \to \phi(\to K^+K^-)e^+e^-$'
            case Component.bpkpmm:
                return r'$B^+\to K^+\mu^+\mu^-$'
            case Component.bdkstkpimm:
                return r'$B_d\to K^*(\to K^+\pi^-)\mu^+\mu^-$'
            case Component.bdkstkpiee:
                return r'$B_d\to K^*(\to K^+\pi^-)e^+e^-$'
            # --------------
            case Component.bpjpsixee:
                return r'$B^+\to J/\psi(\to e^+e^-)X$'
            case Component.bdjpsixee:
                return r'$B_d\to J/\psi(\to e^+e^-)X$'
            case Component.bsjpsixee:
                return r'$B_s\to J/\psi(\to e^+e^-)X$'
            # --------------
            case Component.bppsi2xee:
                return r'$B^+\to \psi(2S)(\to e^+e^-)X$'
            case Component.bdpsi2xee:
                return r'$B_d\to \psi(2S)(\to e^+e^-)X$'
            case Component.bspsi2xee:
                return r'$B_s\to \psi(2S)(\to e^+e^-)X$'
            # --------------
            case Component.bpjpsixmm:
                return r'$B^+\to J/\psi(\to \mu^+\mu^-)X$'
            case Component.bdjpsixmm:
                return r'$B_d\to J/\psi(\to \mu^+\mu^-)X$'
            case Component.bsjpsixmm:
                return r'$B_s\to J/\psi(\to \mu^+\mu^-)X$'
            # --------------
            case Component.bppsi2xmm:
                return r'$B^+\to \psi(2S)(\to \mu^+\mu^-)X$'
            case Component.bdpsi2xmm:
                return r'$B_d\to \psi(2S)(\to \mu^+\mu^-)X$'
            case Component.bspsi2xmm:
                return r'$B_s\to \psi(2S)(\to \mu^+\mu^-)X$'
            # --------------
            case Component.bdkstkpijpsiee:
                return r'$B_d\to K^*(\to K^+\pi^-) J/\psi(\to e^+e^-)$'
            case Component.bdkstkpijpsimm:
                return r'$B_d\to K^*(\to K^+\pi^-) J/\psi(\to \mu^+\mu^-)$'
            case Component.lbpkjpsiee:
                return r'$\Lambda_{b}\to K^+\bar{p} J/\psi(\to e^+e^-)$'
            case Component.lbpkjpsimm:
                return r'$\Lambda_{b}\to K^+\bar{p} J/\psi(\to \mu^+\mu^-)$'
            case Component.bsphijpsiee:
                return r'$B_s\to \phi(\to K^+K^-) J/\psi(\to e^+e^-)$'
            case Component.bsphijpsimm:
                return r'$B_s\to \phi(\to K^+K^-) J/\psi(\to \mu^+\mu^-)$'
            case Component.bpk1kpipiee:
                return r'$B^+\to K_1(\to K^+\pi^+\pi^-) e^+e^-$'
            case Component.bpk2kpipiee:
                return r'$B^+\to K_2(\to K^+\pi^+\pi^-) e^+e^-$'
            case Component.bpkppsi2mm:
                return r'$B^+\to K^+ \psi(2S)(\to \mu^+\mu^-)$'
            case Component.bpkppsi2ee:
                return r'$B^+\to K^+ \psi(2S)(\to e^+e^-)$'
            case Component.bpkstkpiee:
                return r'$B^+\to K^{*+}(\to K^+\pi^0) e^+e^-$'
            case Component.bdkstkpipsi2ee:
                return r'$B_d \to K^*(\to K^+\pi^-)\psi(2S)(\to e^+e^-)$'
            case Component.bdkstkpipsi2mm:
                return r'$B_d \to K^*(\to K^+\pi^-)\psi(2S)(\to \mu^+\mu^-)$'
            case Component.bskstjpsiee:
                return r'$B_s \to K^*(\to K^+\pi^-)J/\psi(\to e^+e^-)$'
            case Component.bskstjpsimm:
                return r'$B_s \to K^*(\to K^+\pi^-)J/\psi(\to \mu^+\mu^-)$'
            case Component.bskstpsi2ee:
                return r'$B_s \to K^*(\to K^+\pi^-)\psi(2S)(\to e^+e^-)$'
            case Component.bskstpsi2mm:
                return r'$B_s \to K^*(\to K^+\pi^-)\psi(2S)(\to \mu^+\mu^-)$'
            case Component.bsphigamma:
                return r'$B_s \to \phi(\to K^+K^-)\gamma$'
            case Component.bdkstpi0:
                return r'$B_d \to K^*(\to K^+ \pi^-)\pi^0(\to \gamma\gamma)$'
            case Component.bpkpipiee:
                return r'$B^+ \to K^+ \pi^+ \pi^- e^+e^-$'
            # -------------------------------------------------
            # Hadronic mis-ID
            # -------------------------------------------------
            case Component.bpkkk:
                return r'$B^+ \to K^+K^-K^+$'
            case Component.bpkpipi:
                return r'$B^+ \to K^+\pi^-\pi^+$'
            case Component.bpkpik:
                return r'$B^+ \to K^+\pi^-K^+$'
            case Component.bdkpipi:
                return r'$B_d \to K^*(\to K^+\pi^-)\pi^+\pi^-$'
            # -------------------------------------------------
            # Semileptonic
            # -------------------------------------------------
            case Component.bpdpiknumm:
                return r'$B^+ \to (\overline{D}{}^0 \to K^+ \mu^- \overline{\nu}_\mu) \pi^+$'
            case Component.bpdnuknumm:
                return r'$B^- \to (D^0 \to K^- \mu^+ \nu_\mu) \, \mu^- \overline{\nu}_\mu$'
            case Component.bdkpimunumunu:
                return r'$B_d \to (D^- \to (K^{*0} \to K^+ \pi^-) \, \mu^- \overline{\nu}_\mu) \, \mu^+ \nu_\mu$'
            # ---------------------------
            case Component.bdkpipienu:
                return r'$B_d \to (D^{*-} \to (\overline{D}{}^0 \to K^+ \pi^-) \pi^-) \, e^+ \nu_e$'
            case Component.bdkpienuenu:
                return r'$B_d \to (D^- \to (K^{*0} \to K^+ \pi^-) \, e^- \overline{\nu}_e) \, e^+ \nu_e$'
            # ---------------------------
            case Component.bpdnukpiee:
                return r'$B^+ \to (\overline{D}{}^0 \to K^+ \pi^-) e^+ \nu_e$'
            case Component.bpdpiknuee:
                return r'$B^+ \to (\overline{D}{}^0 \to K^+ e^- \overline{\nu}_e) \, \pi^+$'
            case Component.bpdnuknuee:
                return r'$B^+ \to (\overline{D}{}^0 \to K^+ e^- \overline{\nu}_e) \, e^+ \nu_e$'
            # ---------------------------
            case Component.bdkstjpsiee_had_swp:
                return r'$B_d\to K^*(\to K^+_{\to\pi^+}\pi^-_{\to K^-})J/\psi(\to e^+e^-)$'
            case Component.bdkstjpsimm_had_swp:
                return r'$B_d\to K^*(\to K^+_{\to\pi^+}\pi^-_{\to K^-})J/\psi(\to \mu^+\mu^-)$'
            case Component.bpkpjpsiee_mix_swp:
                return r'$B_d\to K^*(\to K^+\pi^-_{\to e^-})J/\psi(\to e^+e^-_{\to \pi^-})$'
            case Component.bpkpjpsimm_mix_swp:
                return r'$B_d\to K^*(\to K^+\pi^-_{\to \mu^-})J/\psi(\to \mu^+\mu^-_{\to \pi^-})$'
            # ---------------------------
            case Component.data_24:
                return 'Data'
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
