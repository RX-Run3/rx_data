'''
Module used to define variables whose values are decay nicknames
'''
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('rx_efficiencies:decay_names')
# -----------------------------------
class DecayNames:
    '''
    Class used to hold names of decays for ease of use in the rest of the code
    '''
    # --------------------------
    # correspondence between variable and name
    # of sample when e.g. saving to disk
    # --------------------------
    # NOTE: The names have to start with bp,bu or bs,
    # so that code downstream uses this name to pick up hadronization fractions

    l_nick_name = [
        'bdkskpiee',
        'bpkpee',
        'bpkpjpsiee',
        'bpkskpiee',
        'bsphiee',
        'bpk1kpipiee',
        'bpk2kpipiee']

    l_latex     = [
        r'$B_d\to K^{*0}(\to K^+\pi^-)e^+e^-$',
        r'$B^+\to K^+e^+e^-$',
        r'$B^+\to K^+ J/\psi(\to e^+e^-)$',
        r'$B^+\to K^{*+}(\to K^+\pi^0)e^+e^-$',
        r'$B_s\to \phi(1020)e^+e^-$',
        r'$B^+\to K_1(1270)^+(\to K^+\pi^+\pi^-)e^+e^-$',
        r'$B^+\to K_2(1430)^+(\to X \to K^+\pi^+\pi^-)e^+e^-$']

    l_sample    = [
        'Bd_Kstee_eq_btosllball05_DPC',
        'Bu_Kee_eq_btosllball05_DPC',
        'Bu_JpsiK_ee_eq_DPC',
        'Bu_Kstee_Kpi0_eq_btosllball05_DPC',
        'Bs_phiee_eq_Ball_DPC',
        'Bu_K1ee_eq_DPC',
        'Bu_K2stee_Kpipi_eq_mK1430_DPC']

    l_dec       = [
        ['bdks', 'k+kp'],
        ['bpkp'],
        ['bpjk', 'jpee'],
        ['bpks', 'kokp'],
        ['bsph', 'phkk'],
        ['bpk1', 'k13h'],
        ['bpk2', 'k23h']]
    # --------------------------
    # correspondence between decay variables and latex
    # --------------------------
    tex = dict(zip(l_nick_name, l_latex    , strict=True))
    sam = dict(zip(l_nick_name, l_sample   , strict=True))
    dec = dict(zip(l_nick_name, l_dec      , strict=True))
    nic = dict(zip(l_sample   , l_nick_name, strict=True))

    tex_nic : dict[str,str]       = dict(zip(l_latex , l_nick_name, strict=True))
    sam_dec : dict[str,list[str]] = dict(zip(l_sample, l_dec      , strict=True))
    # -----------------------------------
    @staticmethod
    def get_decays() -> list[str]:
        '''
        Returns list of decay nicknames
        '''
        # TODO: Need to find K1 and K2 branching fractions. Are these decays important?
        return DecayNames.l_nick_name
    # -----------------------------------
    @staticmethod
    def tex_from_decay(decay : str) -> str:
        '''
        Returns latex string for a given decay nickname
        '''
        if decay not in DecayNames.tex:
            for elm in DecayNames.tex:
                log.info(elm)
            raise ValueError(f'Decay {decay} not found')

        return DecayNames.tex[decay]
    # -----------------------------------
    @staticmethod
    def nickname_from_latex(latex : str) -> str:
        '''
        Returns nickname for given latex decay
        '''
        if latex not in DecayNames.tex_nic:
            for elm in DecayNames.tex_nic:
                log.info(elm)
            raise ValueError(f'Latex {latex} not found')

        return DecayNames.tex_nic[latex]
    # -----------------------------------
    @staticmethod
    def nic_from_sample(sample : str) -> str:
        '''
        Returns decay nickname from sample nick name
        '''
        if sample not in DecayNames.nic:
            for elm in DecayNames.nic:
                log.info(elm)

            raise ValueError(f'Sample {sample} not found')

        return DecayNames.nic[sample]
    # -----------------------------------
    @staticmethod
    def sample_from_decay(decay : str, fall_back : str|None=None) -> str:
        '''
        Parameters
        ---------------
        decay: Nickname of decay, e.g. bukee
        fall_back: Optional, if given and if the nickname is not found, will return this string

        Returns
        ---------------
        Nickname of sample, e.g. Bu_Kee_eq_btosllball05_DPC or fall_back
        If no fall back was specified and sample is not found, will raise
        '''
        if decay in DecayNames.sam:
            return DecayNames.sam[decay]

        if fall_back is not None:
            return fall_back

        for elm in DecayNames.sam:
            log.info(elm)

        raise ValueError(f'Decay {decay} not found')
    # -----------------------------------
    @staticmethod
    def subdecays_from_nickname(nickname : str) -> list[str]:
        '''
        Takes nickname of decay, returns list of subdecays, needed to build branching fractions
        '''
        if nickname not in DecayNames.dec:
            for elm in DecayNames.sam:
                log.info(elm)
            raise ValueError(f'Decay {nickname} not found')

        return DecayNames.dec[nickname]
    # -----------------------------------
    @staticmethod
    def subdecays_from_sample(sample : str) -> list[str]:
        '''
        Takes sample name, returns list of subdecays, needed to build branching fractions
        '''
        if sample not in DecayNames.sam_dec:
            for elm in DecayNames.sam:
                log.info(elm)
            raise ValueError(f'Decay {sample} not found')

        return DecayNames.sam_dec[sample]
# -----------------------------------
