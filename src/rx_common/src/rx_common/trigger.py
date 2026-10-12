
from enum        import StrEnum, auto

from .project    import Project
from .channel    import Channel
from .component  import Component
from .qsq        import Qsq

class Trigger(StrEnum):
    '''
    Class meant to represent MVA HLT2 triggers
    '''
    rk_ee_os     = auto()
    rk_me_os     = auto()
    rk_ee_ss     = auto()
    rk_ee_nopid  = auto()
    rk_ee_cal    = auto()
    rk_ee_misid  = auto()
    rk_mm_os     = auto()
    rk_mm_nopid  = auto()
    rk_mm_ss     = auto()
    # -----------
    rkst_ee_os   = auto()
    rkst_me_os   = auto()
    rkst_ee_ss   = auto()
    rkst_ee_nopid= auto()
    rkst_ee_cal  = auto()
    rkst_ee_misid= auto()
    rkst_mm_os   = auto()
    rkst_mm_nopid= auto()
    rkst_mm_ss   = auto()
    # -----------
    @classmethod
    def get_main_trigger(
        cls, 
        channel : Channel, 
        project : Project) -> 'Trigger':
        '''
        Parameters
        ----------------
        channel: E.g. ee, mm
        project: E.g. rk, rkst

        Returns
        ----------------
        Trigger used for this project/channel combination
        for actual measurement
        '''
        for trig in cls:
            if not trig.is_main:
                continue

            if trig.channel != channel:
                continue

            if trig.project != project:
                continue

            return trig

        raise ValueError(f'Cannot find main trigger for: {project}/{channel}')
    # -----------
    @property
    def reso_jpsi_signal(self) -> Component:
        '''
        Component associated to trigger in resonant mode
        for the jpsi bin
        '''
        match self:
            case Trigger.rk_ee_os:
                return Component.bpkpjpsiee
            case Trigger.rk_mm_os:
                return Component.bpkpjpsimm
            case Trigger.rkst_ee_os:
                return Component.bdkstkpijpsiee
            case Trigger.rkst_mm_os:
                return Component.bdkstkpijpsimm
            case _:
                raise ValueError(f'No resonant signal component for: {self}')
    # -----------
    @property
    def reso_psi2_signal(self) -> Component:
        '''
        Component associated to trigger in resonant mode
        for the psi2S bin
        '''
        match self:
            case Trigger.rk_ee_os:
                return Component.bpkppsi2ee
            case Trigger.rk_mm_os:
                return Component.bpkppsi2mm
            case Trigger.rkst_ee_os:
                return Component.bdkstkpipsi2ee
            case Trigger.rkst_mm_os:
                return Component.bdkstkpipsi2mm
            case _:
                raise ValueError(f'No resonant signal component for: {self}')
    # -----------
    @property
    def rare_signal(self) -> Component:
        '''
        Component associated to trigger in rare mode
        '''
        match self:
            case Trigger.rk_ee_os:
                return Component.bpkpee
            case Trigger.rk_mm_os:
                return Component.bpkpmm
            case Trigger.rkst_ee_os:
                return Component.bdkstkpiee
            case Trigger.rkst_mm_os:
                return Component.bdkstkpimm
            case _:
                raise ValueError(f'No rare signal component for: {self}')
    # -----------
    @property
    def misid_version(self) -> 'Trigger':
        '''
        MisID version of this trigger, if it exists
        '''
        match self:
            case Trigger.rk_ee_os:
                return Trigger.rk_ee_misid
            case Trigger.rkst_ee_os:
                return Trigger.rkst_ee_misid
            case _:
                raise ValueError(f'Cannot find misid version for: {self}')
    # -----------
    @property
    def pid_version(self) -> 'Trigger':
        '''
        MisID version of this trigger, if it exists
        '''
        match self:
            case Trigger.rk_ee_nopid:
                return Trigger.rk_ee_os
            case Trigger.rkst_ee_nopid:
                return Trigger.rkst_ee_os
            case Trigger.rk_mm_nopid:
                return Trigger.rk_mm_os
            case Trigger.rkst_mm_nopid:
                return Trigger.rkst_mm_os
            case _:
                raise ValueError(f'Version with PID not defined for: {self}')
    # -----------
    def get_signal_component(
        self, 
        qsq : Qsq) -> Component:
        '''
        Parameters
        -------------
        qsq : q2 bin

        Returns
        -------------
        Signal component for given q2 bin 
        '''
        # ----------------
        if qsq == Qsq.jpsi and self == Trigger.rk_ee_os:
            return Component.bpkpjpsiee

        if qsq == Qsq.jpsi and self == Trigger.rk_mm_os:
            return Component.bpkpjpsimm

        if qsq == Qsq.psi2 and self == Trigger.rk_ee_os:
            return Component.bpkppsi2ee

        if qsq == Qsq.psi2 and self == Trigger.rk_mm_os:
            return Component.bpkppsi2mm

        if self == Trigger.rk_ee_os:
            return Component.bpkpee

        if self == Trigger.rk_mm_os:
            return Component.bpkpmm
        # ----------------
        if qsq == Qsq.jpsi and self == Trigger.rkst_ee_os:
            return Component.bdkstkpijpsiee

        if qsq == Qsq.jpsi and self == Trigger.rkst_mm_os:
            return Component.bdkstkpijpsimm

        if qsq == Qsq.psi2 and self == Trigger.rkst_ee_os:
            return Component.bdkstkpipsi2ee

        if qsq == Qsq.psi2 and self == Trigger.rkst_mm_os:
            return Component.bdkstkpipsi2mm

        if self == Trigger.rkst_ee_os:
            return Component.bdkstkpiee

        if self == Trigger.rkst_mm_os:
            return Component.bdkstkpimm
        # ----------------

        raise ValueError(f'Cannot get signal component for: {qsq}/{self}')
    # -----------
    @property
    def subtriggers(self) -> list['Trigger']:
        '''
        List of triggers into which this trigger can be
        decomposed, e.g. nopid = misID + signal region

        If not decomposable, return list with only this trigger 
        '''
        match self:
            case Trigger.rk_ee_nopid:
                return [Trigger.rk_ee_os  , Trigger.rk_ee_misid  ]
            case Trigger.rkst_ee_nopid:
                return [Trigger.rkst_ee_os, Trigger.rkst_ee_misid]
            case _:
                return [self]
    # -----------
    @property
    def has_pid(self) -> bool:
        '''
        False for triggers associated to PID removed samples
        '''
        return 'nopid' not in self.name
    # -----------
    def __str__(self) -> str:
        match self:
            case Trigger.rk_ee_os:
                return 'Hlt2RD_BuToKpEE_MVA'
            case Trigger.rk_me_os:
                return 'Hlt2RD_BuToKpMuE_MVA'
            case Trigger.rk_ee_ss:
                return 'Hlt2RD_BuToKpEE_SameSign_MVA'
            case Trigger.rk_ee_nopid:
                return 'Hlt2RD_BuToKpEE_MVA_noPID'
            case Trigger.rk_ee_cal:
                return 'Hlt2RD_BuToKpEE_MVA_cal'
            case Trigger.rk_ee_misid:
                return 'Hlt2RD_BuToKpEE_MVA_misid'
            case Trigger.rk_mm_os:
                return 'Hlt2RD_BuToKpMuMu_MVA'
            case Trigger.rk_mm_nopid:
                return 'Hlt2RD_BuToKpMuMu_MVA_noPID'
            case Trigger.rk_mm_ss:
                return 'Hlt2RD_BuToKpMuMu_SameSign_MVA'
            case Trigger.rkst_ee_os:
                return 'Hlt2RD_B0ToKpPimEE_MVA'
            case Trigger.rkst_me_os:
                return 'Hlt2RD_B0ToKpPimMuE_MVA'
            case Trigger.rkst_ee_ss:
                return 'Hlt2RD_B0ToKpPimEE_SameSign_MVA'
            case Trigger.rkst_ee_nopid:
                return 'Hlt2RD_B0ToKpPimEE_MVA_noPID'
            case Trigger.rkst_ee_cal:
                return 'Hlt2RD_B0ToKpPimEE_MVA_cal'
            case Trigger.rkst_ee_misid:
                return 'Hlt2RD_B0ToKpPimEE_MVA_misid'
            case Trigger.rkst_mm_os:
                return 'Hlt2RD_B0ToKpPimMuMu_MVA'
            case Trigger.rkst_mm_nopid:
                return 'Hlt2RD_B0ToKpPimMuMu_MVA_noPID'
            case Trigger.rkst_mm_ss:
                return 'Hlt2RD_B0ToKpPimMuMu_SameSign_MVA'
    # -----------
    @classmethod
    def from_name(cls, name: str) -> 'Trigger':
        '''
        Parameters
        --------------
        name: Trigger name, i.e. Hlt2RD_BuToKpEE_MVA

        Returns
        --------------
        Corresponding trigger object
        '''
        match name:
            case 'Hlt2RD_BuToKpEE_MVA':
                return cls.rk_ee_os
            case 'Hlt2RD_BuToKpMuE_MVA':
                return cls.rk_me_os
            case 'Hlt2RD_BuToKpEE_SameSign_MVA':
                return cls.rk_ee_ss
            case 'Hlt2RD_BuToKpEE_MVA_noPID':
                return cls.rk_ee_nopid
            case 'Hlt2RD_BuToKpEE_MVA_cal':
                return cls.rk_ee_cal
            case 'Hlt2RD_BuToKpEE_MVA_misid':
                return cls.rk_ee_misid
            case 'Hlt2RD_BuToKpMuMu_MVA':
                return cls.rk_mm_os
            case 'Hlt2RD_BuToKpMuMu_MVA_noPID':
                return cls.rk_mm_nopid
            case 'Hlt2RD_BuToKpMuMu_SameSign_MVA':
                return cls.rk_mm_ss
            case 'Hlt2RD_B0ToKpPimEE_MVA':
                return cls.rkst_ee_os
            case 'Hlt2RD_B0ToKpPimMuE_MVA':
                return cls.rkst_me_os
            case 'Hlt2RD_B0ToKpPimEE_SameSign_MVA':
                return cls.rkst_ee_ss
            case 'Hlt2RD_B0ToKpPimEE_MVA_noPID':
                return cls.rkst_ee_nopid
            case 'Hlt2RD_B0ToKpPimEE_MVA_cal':
                return cls.rkst_ee_cal
            case 'Hlt2RD_B0ToKpPimEE_MVA_misid':
                return cls.rkst_ee_misid
            case 'Hlt2RD_B0ToKpPimMuMu_MVA':
                return cls.rkst_mm_os
            case 'Hlt2RD_B0ToKpPimMuMu_MVA_noPID':
                return cls.rkst_mm_nopid
            case 'Hlt2RD_B0ToKpPimMuMu_SameSign_MVA':
                return cls.rkst_mm_ss
            case _:
                raise ValueError(f'Unknown trigger name: {name!r}')
    # -----------
    @property
    def is_electron(self) -> bool:
        return self.channel == Channel.ee
    # -----------
    @property
    def is_muon(self) -> bool:
        return self.channel == Channel.mm
    # -----------
    @property
    def channel(self) -> Channel:
        '''
        Either 'muon' or 'electron'
        '''
        if 'ee' in self.name:
            return Channel.ee
    
        if 'mm' in self.name:
            return Channel.mm
    
        raise ValueError(f'Cannot determine channel for trigger: {self}')
    # -----------
    @property
    def is_ss(self) -> bool:
        '''
        True if it is a same sign trigger
        '''
        return 'SameSign' in str(self)
    # -----------
    @property
    def is_main(self) -> bool:
        '''
        True if trigger is used for actual measurement
        '''
        ee_trig = [Trigger.rk_ee_os, Trigger.rkst_ee_os]
        mm_trig = [Trigger.rk_mm_os, Trigger.rkst_mm_os]

        return self in ee_trig + mm_trig
    # -----------
    @property
    def project(self) -> Project:
        '''
        Returns
        -----------------
        Project for which this trigger is meant to be used, e.g. rk, rkst etc
        '''
        match self:
            # --------------
            # rk
            # --------------
            case Trigger.rk_ee_os:
                return Project.rk
            case Trigger.rk_me_os:
                return Project.rk
            case Trigger.rk_ee_ss:
                return Project.rk
            case Trigger.rk_ee_cal:
                return Project.rk
            case Trigger.rk_ee_misid:
                return Project.rk
            case Trigger.rk_ee_nopid:
                return Project.rk_no_pid
            # --------------
            case Trigger.rk_mm_os:
                return Project.rk
            case Trigger.rk_mm_ss:
                return Project.rk
            case Trigger.rk_mm_nopid:
                return Project.rk_no_pid
            # --------------
            # rkst
            # --------------
            case Trigger.rkst_ee_os:
                return Project.rkst
            case Trigger.rkst_me_os:
                return Project.rkst
            case Trigger.rkst_ee_ss:
                return Project.rkst
            case Trigger.rkst_ee_cal:
                return Project.rkst
            case Trigger.rkst_ee_misid:
                return Project.rkst
            case Trigger.rkst_ee_nopid:
                return Project.rkst_no_pid
            # --------------
            case Trigger.rkst_mm_os:
                return Project.rkst
            case Trigger.rkst_mm_ss:
                return Project.rkst
            case Trigger.rkst_mm_nopid:
                return Project.rkst_no_pid

