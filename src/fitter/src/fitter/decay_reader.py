'''
This module contains the class DecayReader and its
derived classes KLLDecayReader and KPiLLDecayReader
'''

from fitter.pchain         import PChain
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('fitter:decay_reader')
#---------------------------
class DecayReader:
    '''
    Class used to attach decay weights to dataframe of inclusive decays
    '''
    #---------------------------
    def __init__(self):
        '''
        Takes particle chain instances
        '''
        self._Jpsi_id   = 443
        self._Psi2_id   = 100443
        self._Pion_id   = 211
        self._Phi_id    = 333
        self._Eta_id    = 221
        self._Kstar_id  = 313
        self._Kplus_id  = 321
        self._KShort_id = 310

        self._Bd_id = 511
        self._Bu_id = 521
        self._Bs_id = 531

        #From https://gitlab.cern.ch/LHCb-RD/ewp-rkstz/-/blob/master/analysis/kernel/inc/ConstDef.hpp
        self._Bc         = 541
        self._Lb         = 5122
        self._L0         = 3122
        self._Kst_c_id   = 323
        self._K_1_1270_z = 10313
        self._K_1_1270_c = 10323
        self._K_2_1430_c = 325
        self._K_2_1430_z = 315
        self._K_1_1400_z = 20313
        self._K_1_1400_c = 20323
        self._K0         = 311
        self._KLong      = 130
        self._Pi0        = 111
        self._Muon       = 13
        self._Electron   = 11
        self._Tau        = 15
        self._Proton     = 2212
        self._Neutron    = 2112
        self._Eta_prime  = 331
        self._Rho0       = 113
        self._Rho_c      = 213
        self._Omega      = 223
        self._D0         = 421
        self._Dp         = 411
        self._Ds         = 431
        self._Bst0       = 513
        self._Bst_plus   = 523
        self._Photon     = 22

        self._weight  : float        = 1.0
        self._l_chain : list[PChain] = []
        self._l_bid   : list[int]    = [self._Bd_id, self._Bu_id, self._Bs_id]
    #---------------------------
    def _get_jpsi_wgt(self, l1 : PChain, l2 : PChain) -> float:
        '''
        Parameters
        ----------------
        l1/2: Particle chain associated to L1/2 lepton

        Returns
        ----------------
        Weight associated to branching ratio corrections for leptons decay chain

        Taken from:

        https://gitlab.cern.ch/LHCb-RD/ewp-rkstz/-/blob/master/analysis/kernel/src/XJPsRescaler.cpp#L645

        Numbers were changed from that version, need further discussion and checks
        '''
        for bid in  self._l_bid:
            flg_1 = l1.match_upstream( self._Psi2_id, bid)
            flg_2 = l2.match_upstream( self._Psi2_id, bid)

            if not flg_1 and not flg_2:
                continue

            l1_from_jp = l1.match_mother(self._Jpsi_id)
            l2_from_jp = l2.match_mother(self._Jpsi_id)
            if   l1_from_jp or l2_from_jp:
                return 0.958 # Was 0.75

            l1_from_ps = l1.match_mother(self._Psi2_id)
            l2_from_ps = l2.match_mother(self._Psi2_id)
            if l1_from_ps or l2_from_ps:
                return 0.771 # Was 7.58

        return 1.0
    #---------------------------
    def _get_psi2_wgt(self, l1 : PChain, l2 : PChain) -> float:
        '''
        Parameters
        ----------------
        l1/2_ch: Particle chain associated to L1/2 lepton

        Returns
        ----------------
        Weight associated to branching ratio corrections for leptons decay chain
        when they come directly from a Psi2S
        '''
        weight= 1
        flg_1 = l1.match_upstream(self._Psi2_id, self._Bd_id)
        flg_2 = l2.match_upstream(self._Psi2_id, self._Bd_id)
        if flg_1 or flg_2:
            weight = 1.17

        flg_1 = l1.match_upstream(self._Psi2_id, self._Bu_id)
        flg_2 = l2.match_upstream(self._Psi2_id, self._Bu_id)
        if flg_1 or flg_2:
            weight = 1.35

        return weight
    #---------------------------
    def _either_track_has(self, pid : int) -> bool:
        '''
        Parameters
        --------------
        pid: Particle ID from PDG

        Returns
        --------------
        True if particle exists in any of the chains registered
        '''
        if not self._l_chain:
            raise ValueError('No chains were registered')

        for chain in self._l_chain:
            if chain.has_in_chain(pid):
                return True

        return False
    #---------------------------
    def _get_psi2_over_jpsi(self) -> float:
        '''
        Returns correction factor for branching fractions
        associated to psi2S chain
        '''
        flg_ps = self._either_track_has(self._Psi2_id)
        if not flg_ps:
            return 1.0

        flg_bu = self._either_track_has(self._Bu_id)
        flg_bd = self._either_track_has(self._Bd_id)
        flg_bs = self._either_track_has(self._Bs_id)

        if flg_bs:
            return ( 5.40E-4/ 1.0800E-3 ) / ( 0.0748/ 0.1077) #0.72

        if flg_bu:
            return ( 6.19E-4/ 1.0006E-3 ) / ( 0.0729/ 0.1595) #1.35

        if flg_bd:
            return ( 5.90E-4/ 1.2700E-3 ) / (0.07610/ 0.1850) #1.13

        return 1.0
    #---------------------------
    def _get_common_weights(
        self,
        l1 : PChain,
        l2 : PChain) -> float:
        '''
        Returns
        ----------------
        Weight for both k+ll and k+pi-ll candidates
        '''
        w1 = self._get_jpsi_wgt(l1=l1, l2=l2)
        w2 = self._get_psi2_wgt(l1=l1, l2=l2)
        w3 = self._get_psi2_over_jpsi()
        wt = w1 * w2 * w3

        log.verbose('-----------------------------')
        log.verbose(f'Jpsi wgt:           {w1:.3f}')
        log.verbose(f'psi2 wgt:           {w2:.3f}')
        log.verbose(f'Psi2 over Jpsi wgt: {w3:.3f}')
        log.verbose(f'Total wgt:          {wt:.3f}')

        return wt
#---------------------------
class KLLDecayReader(DecayReader):
    '''
    Class used to retrieve decay weights for KLL candidates
    '''
    #---------------------------
    def __init__(self, l1 : PChain, l2 : PChain, kp : PChain):
        super().__init__()
        self._l_chain = [l1, l2, kp]

        self._l1 = l1
        self._l2 = l2
        self._kp = kp
    #---------------------------
    def _get_kp_wgt(self, kp : PChain) -> float:
        '''
        Returns correction weights for branching fraction associated
        to kaon chain
        '''
        weight = 1.0
        if kp.match_decay( [self._Pion_id, self._KShort_id             ]):
            weight *= 0.5

        if kp.match_decay( [self._Kplus_id, self._Phi_id, self._Bd_id]):
            weight *= 0.5/0.9974

        if kp.match_decay( [self._Kplus_id, self._Phi_id, self._Bu_id]):
            weight *= 0.5/0.7597

        if kp.match_decay( [self._Pion_id, self._Eta_id] ):
            weight *= 0.28/0.4

        if kp.match_decay( [self._Kplus_id, self._Kstar_id] ):
            weight *= 0.66 / 0.7993

        if kp.match_decay( [self._Kplus_id, self._Kst_c_id] ):
            weight *= 0.33 / 0.4993

        if kp.match_decay( [self._Kplus_id, self._K_2_1430_c]):
            weight *= 0.1670/0.2485

        return weight
    #---------------------------
    def get_weight(self) -> float:
        '''
        Returns:

        wt (float): Weight for candidate
        '''
        w1 = self._get_common_weights(l1=self._l1, l2=self._l2)
        w2 = self._get_kp_wgt(kp=self._kp)

        return w1 * w2
#---------------------------
class KPiLLDecayReader(DecayReader):
    '''
    Class used to retrieve decay weights for KPILL candidates
    '''
    # ----------------------
    def __init__(
        self,
        l1 : PChain,
        l2 : PChain,
        kp : PChain,
        pi : PChain):
        '''
        Parameters
        --------------
        PChain instances for final state tracks
        '''
        super().__init__()
        self._l_chain = [l1, l2, kp, pi]

        self._l1 = l1
        self._l2 = l2
        self._kp = kp
        self._pi = pi
    # ----------------------
    def _get_phi_weight(self) -> float:
        '''
        Returns
        -------------
        Weight correcting branching fraction in chains with phi decays
        '''
        if self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Phi_id, self._Bd_id]):
            return 0.5 / 0.9974

        if self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Phi_id, self._Bu_id]):
            return 0.5 / 0.7597

        rho0_upstream = self._pi.match_upstream(daughter_id = self._Rho0 , mother_id= self._Phi_id)
        rhoc_upstream = self._pi.match_upstream(daughter_id = self._Rho_c, mother_id= self._Phi_id)
        is_pion       = self._pi.match_id(iD = self._Pion_id)
        weight        = 0.0425 / 0.0665

        if rho0_upstream and is_pion:
            return weight

        if rhoc_upstream and is_pion:
            return weight

        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Phi_id]):
            return weight

        return 1.0
    # ----------------------
    def _get_kshort_weight(self) -> float:
        '''
        Returns
        -------------
        Weights correcting chains with Kshort decays
        '''
        if self._pi.match_decay(l_dec_id = [self._Pion_id, self._KShort_id]):
            return 0.5

        if self._kp.match_decay(l_dec_id = [self._Pion_id, self._KShort_id]):
            return 0.5

        return 1.0
    # ----------------------
    def _get_eta_weight(self) -> float:
        '''
        Returns
        -------------
        Weight associated to decay chains with eta mesons
        '''
        cond_kp = self._kp.match_decay(l_dec_id = [self._Pion_id, self._Eta_id])
        cond_pi = self._pi.match_decay(l_dec_id = [self._Pion_id, self._Eta_id])

        if cond_kp or cond_pi:
            return 0.28 / 0.4

        return 1.0
    # ----------------------
    def _get_kstar_weight(self) -> float:
        '''
        Returns
        -------------
        Weight associated to chains containing Kstar
        '''
        kplus_kstart_kp = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id])
        kplus_kstart_pi = self._pi.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id])

        if kplus_kstart_kp or kplus_kstart_pi:
            return 0.66 / 0.7993

        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._KShort_id, self._Kstar_id]):
            return 0.33 / 0.20

        kst_c_pi_1 = self._pi.match_decay(l_dec_id=[self._Pion_id,                  self._Kst_c_id])
        kst_c_pi_2 = self._pi.match_decay(l_dec_id=[self._Pion_id, self._KShort_id, self._Kst_c_id])
        if kst_c_pi_1 or kst_c_pi_2:
            return 0.66 / 0.4993

        if self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id]):
            return 0.33 / 0.4993

        return 1.0
    # ----------------------
    def _get_k10_weight(self) -> float:
        '''
        Returns
        -------------
        Weight associated to chains with
        '''
        kplus_k1_rho = self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho_c, self._K_1_1270_z])
        k_k1         = self._kp.match_decay(l_dec_id=[self._Kplus_id,             self._K_1_1270_z])
        if k_k1 and kplus_k1_rho:
            return 0.2800 / 0.3796

        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho0, self._K_1_1270_z]):
            return 0.1400 / 0.0949

        pi_k1     = self._pi.match_decay(l_dec_id=[self._Pion_id,                  self._K_1_1270_z])
        k_kstc_k1 = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id, self._K_1_1270_z])
        if pi_k1 and k_kstc_k1:
            return 0.1067 / 0.0965

        k_k1_2    = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._K_1_1270_z])
        pi_k1_2   = self._pi.match_decay(l_dec_id=[self._Pion_id , self._K_1_1270_z])
        if k_k1_2 and pi_k1_2:
            return 0.1244 / 0.1686

        k_kst_k1  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_1_1270_z])
        pi_kst_k1 = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_1_1270_z])
        if k_kst_k1 and pi_kst_k1:
            return 0.0533 / 0.0602

        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Omega, self._K_1_1270_z]):
            return 0.1100 / 0.0744

        return 1.0
    # ----------------------
    def _get_k1c_weight(self) -> float:
        '''
        Returns
        -------------
        Weight for chains with K_1_1270_c
        '''
        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho_c, self._K_1_1270_c]):
            return 0.2800 / 0.1838

        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho0 , self._K_1_1270_c]):
            return 0.1400 / 0.1838

        pi_kst_k1c_1 = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_1_1270_c])
        k_kst_k1c_1  = self._kp.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_1_1270_c])
        pi_k1c_2     = self._pi.match_decay(l_dec_id=[self._Pion_id ,                 self._K_1_1270_c])
        k_kst_k1c_2  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_1_1270_c])

        if (pi_kst_k1c_1 and k_kst_k1c_1) or (pi_k1c_2 and k_kst_k1c_2):
            return 0.1067 / 0.1166

        pi_omega_k1c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Omega, self._K_1_1270_c])
        k_k1c_1      = self._kp.match_decay(l_dec_id=[self._Kplus_id,              self._K_1_1270_c])

        if pi_omega_k1c and k_k1c_1:
            return 0.1100 / 0.1440

        pi_k1c_3     = self._pi.match_decay(l_dec_id=[self._Pion_id , self._K_1_1270_c])
        k_k1c_2      = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._K_1_1270_c])

        if pi_k1c_3 and k_k1c_2:
            return 0.1444 / 0.1895

        return 1.0
    # ----------------------
    def _get_k2c_weight(self) -> float:
        '''
        Returns
        -------------
        Weights associated to chains with K_2_1430_c
        '''
        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._KShort_id, self._K_2_1430_c]):
            return 0.3340 / 0.2485

        pi_k2c          = self._pi.match_decay(l_dec_id=[self._Pion_id,                  self._K_2_1430_c])
        k_pi_kshort_k2c = self._kp.match_decay(l_dec_id=[self._Pion_id, self._KShort_id, self._K_2_1430_c])
        if pi_k2c and k_pi_kshort_k2c:
            return 0.3340 / 0.2485

        if self._kp.match_decay(l_dec_id=[self._Kplus_id, self._K_2_1430_c]):
            return 0.1670 / 0.2485

        k_kst_k2c  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_2_1430_c])
        pi_kst_k2c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_2_1430_c])
        if k_kst_k2c and pi_kst_k2c:
            return 0.1645 / 0.2095

        k_kst_k2c_2 = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_2_1430_c])
        pi_k2c_2    = self._pi.match_decay(l_dec_id=[self._Pion_id ,                 self._K_2_1430_c])
        if k_kst_k2c_2 and pi_k2c_2:
            return 0.1645 / 0.2095

        k_kstc_k2c  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id, self._K_2_1430_c])
        pi_kstc_k2c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kst_c_id, self._K_2_1430_c])
        if k_kstc_k2c and pi_kstc_k2c:
            return (0.0835 + 0.0450 * 2) / (0.0839 + 0.0539)

        k_kstc_k2c_2 = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id, self._K_2_1430_c])
        pi_k2c_3     = self._pi.match_decay(l_dec_id=[self._Pion_id ,                 self._K_2_1430_c])
        if k_kstc_k2c_2 and pi_k2c_3:
            return 0.0450 / 0.0539

        if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho_c, self._K_2_1430_c]):
            return 0.0580 / 0.0442

        k_k2c_2     = self._kp.match_decay(l_dec_id=[self._Kplus_id,             self._K_2_1430_c])
        pi_rho0_k2c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Rho0, self._K_2_1430_c])
        if k_k2c_2 and pi_rho0_k2c:
            return (0.0290 * 2) / 0.0449

        return 1.0
    # ----------------------
    def _get_k2z_weight(self) -> float:
        '''
        Returns
        -------------
        Weights associated to chains with K_2_1430_z
        '''
        k_k2z        = self._kp.match_decay(l_dec_id=[self._Kplus_id,                 self._K_2_1430_z])
        pi_k2z       = self._pi.match_decay(l_dec_id=[self._Pion_id ,                 self._K_2_1430_z])

        k_kstc_k2z   = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id, self._K_2_1430_z])
        pi_kstc_k2z  = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kst_c_id, self._K_2_1430_z])

        k_kst_k2z    = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_2_1430_z])
        pi_kst_k2z   = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_2_1430_z])

        if k_k2z and pi_k2z:
            return 0.3340 / 0.4407

        if k_kstc_k2z and pi_kstc_k2z:
            return (0.1645 + 0.0450) / (0.1492 + 0.0480)

        if k_kstc_k2z and pi_k2z:
            return (0.1645 + 0.0450) / (0.1492 + 0.0480)

        if k_kst_k2z and pi_kst_k2z:
            return (0.0835 + 0.0450 * 2) / (0.0932 + 0.0599)

        if k_kst_k2z and pi_k2z:
            return 1.0  # not covered!

        pi_rho_c_k2z = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Rho_c   , self._K_2_1430_z])
        if k_k2z and pi_rho_c_k2z:
            return 0.0580 / 0.0786  # not covered!

        pi_rho0_k2z  = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Rho0    , self._K_2_1430_z])
        if pi_rho0_k2z:
            return (0.0290 * 2) / 0.0200  # no omega in dec file.

        return 1.0
    # ----------------------
    def _get_k1z_weight(self) -> float:
        '''
        Returns
        -------------
        Weight for chains with K_1_1400_z
        '''
        k_kstc_k1_1400_z  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id, self._K_1_1400_z])
        pi_k1_1400_z      = self._pi.match_decay(l_dec_id=[self._Pion_id ,                 self._K_1_1400_z])
        pi_kstc_k1_1400_z = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kst_c_id, self._K_1_1400_z])
        if k_kstc_k1_1400_z and (pi_k1_1400_z or pi_kstc_k1_1400_z):
            return 0.6300 / 0.5849

        k_k1_1400_z        = self._kp.match_decay(l_dec_id=[self._Kplus_id,                self._K_1_1400_z])
        pi_rho_c_k1_1400_z = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Rho_c,   self._K_1_1400_z])
        if k_k1_1400_z and pi_rho_c_k1_1400_z:
            return 0.0200 / 0.0278

        k_kst_k1_1400_z  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_1_1400_z])
        pi_kst_k1_1400_z = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_1_1400_z])
        if k_kst_k1_1400_z and pi_kst_k1_1400_z:
            return 0.3100 / 0.3594

        if not (self._kp.match_mother(  self._K_1_1400_z) or
                self._kp.match_gmother( self._K_1_1400_z) or
                self._kp.match_ggmother(self._K_1_1400_z)):

            pi_rho0_k1_1400_z   = self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho0     , self._K_1_1400_z])
            pi_kshort_k1_1400_z = self._pi.match_decay(l_dec_id=[self._Pion_id, self._KShort_id, self._K_1_1400_z])
            if pi_rho0_k1_1400_z or pi_kshort_k1_1400_z:
                return 0.0100 / 0.0070

            pi_omega_k1_1400_z = self._pi.match_decay(l_dec_id=[self._Pion_id, self._Omega, self._K_1_1400_z])
            if pi_omega_k1_1400_z:
                return 0.0100 / 0.0069

            if self._pi.match_decay(l_dec_id=[self._Pion_id, self._K_1_1400_z]):
                return 0.0133 / 0.0093

        return 1.0
    # ----------------------
    def _get_k14c_weight(self) -> float:
        '''
        Returns
        -------------
        Weight for chains with K_1_1400_c
        '''
        k_kst_k1_1400_c  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kstar_id, self._K_1_1400_c])
        pi_kst_k1_1400_c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kstar_id, self._K_1_1400_c])
        if k_kst_k1_1400_c and pi_kst_k1_1400_c:
            return 0.6300 / 0.6714

        k_kstc_k1_1400_c  = self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Kst_c_id, self._K_1_1400_c])
        pi_kstc_k1_1400_c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Kst_c_id, self._K_1_1400_c])
        if k_kstc_k1_1400_c and pi_kstc_k1_1400_c:
            return 0.3100 / 0.2646

        if not (self._kp.match_mother(  self._K_1_1400_c) or
                self._kp.match_gmother( self._K_1_1400_c) or
                self._kp.match_ggmother(self._K_1_1400_c)):

            if self._pi.match_decay(l_dec_id=[self._Pion_id, self._Rho_c, self._K_1_1400_c]):
                return 0.0200 / 0.0128

        k_k1_1400_c       = self._kp.match_decay(l_dec_id=[self._Kplus_id,             self._K_1_1400_c])
        pi_rho0_k1_1400_c = self._pi.match_decay(l_dec_id=[self._Pion_id , self._Rho0, self._K_1_1400_c])
        if k_k1_1400_c and pi_rho0_k1_1400_c:
            return 0.0100 / 0.0128

        pi_k1_1400_c = self._pi.match_decay(l_dec_id=[self._Pion_id, self._K_1_1400_c])
        if k_k1_1400_c and pi_k1_1400_c:
            return 0.0133 / 0.0170

        pi_omega_k1_1400_c = self._pi.match_decay(l_dec_id=[self._Pion_id, self._Omega, self._K_1_1400_c])
        if k_k1_1400_c and pi_omega_k1_1400_c:
            return 0.0100 / 0.0128

        if not (self._pi.match_mother(  self._K_1_1400_c) or
                self._pi.match_gmother( self._K_1_1400_c) or
                self._pi.match_ggmother(self._K_1_1400_c)):

            if self._kp.match_decay(l_dec_id=[self._Kplus_id, self._K_1_1400_c]):
                return 0.0067 / 0.0086

        return 1.0
    # ----------------------
    def _get_bsks_weight(self) -> float:
        '''
        Returns
        -------------
        The Bs -> Ks Kst0 J/Psi(Psi) is simulated with a PHSP model, however the Kst0 peaking structure is fully in the B.R.
        Moreover the B.R> is off by a factor 2 since it uses only KS ( the dec fraction ). We must scale the B.R. by a factor 2x .
        '''
        if not self._kp.match_decay(l_dec_id=[self._Kplus_id, self._Bs_id]):
            return 1.0

        if not self._pi.match_decay(l_dec_id=[self._Pion_id , self._Bs_id]):
            return 1.0

        l1_jpsi_bs = self._l1.match_upstream(daughter_id=self._Jpsi_id, mother_id=self._Bs_id)
        l2_jpsi_bs = self._l2.match_upstream(daughter_id=self._Jpsi_id, mother_id=self._Bs_id)

        if l1_jpsi_bs or l2_jpsi_bs:
            return ( 9.2e-4 / 1.08e-3 ) / ( 0.0427 / 0.1077 ) * 3

        l1_psi2_bs = self._l1.match_upstream(daughter_id=self._Psi2_id, mother_id=self._Bs_id)
        l2_psi2_bs = self._l2.match_upstream(daughter_id=self._Psi2_id, mother_id=self._Bs_id)

        if l1_psi2_bs or l2_psi2_bs:
            return 2.0 * 3.0

        return 1.0
    # ----------------------
    def get_weight(self) -> float:
        '''
        Returns
        -------------
        Weight needed to correct for branching fraction bug in cocktail sample
        '''
        wt_common = self._get_common_weights(l1=self._l1, l2=self._l2)
        wt_phi    = self._get_phi_weight()
        wt_kshort = self._get_kshort_weight()
        wt_eta    = self._get_eta_weight()
        wt_kstar  = self._get_kstar_weight()
        wt_k10    = self._get_k10_weight()
        wt_k1c    = self._get_k1c_weight()
        wt_k2c    = self._get_k2c_weight()
        wt_k2z    = self._get_k2z_weight()
        wt_k1z    = self._get_k1z_weight()
        wt_k14c   = self._get_k14c_weight()
        wt_bsks   = self._get_bsks_weight()

        wt  = wt_common * wt_phi * wt_kshort * wt_eta
        wt *= wt_kstar * wt_k10 * wt_k1c * wt_k2c * wt_k2z * wt_k1z
        wt *= wt_k14c * wt_bsks

        return wt
#---------------------------
