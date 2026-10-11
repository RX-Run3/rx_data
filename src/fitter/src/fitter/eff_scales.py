'''
Module holding EffScales class
'''

from gvar            import GVar, gvar
from pathlib         import Path
from rx_efficiencies import EfficiencyCalculator
from rx_common       import Trigger
from rx_common       import Component, Channel
from rx_common       import Project, Brem, Qsq
from rx_selection    import selection as sel
from dmu             import LogStore

log=LogStore.add_logger('fitter:eff_scales')
# -------------------------
class EffScales:
    '''
    Class meant to calculate ratios of efficiencies between signal regions
    Used to calculate scale factor between rkst signal yield and background yield
    '''
    # -------------------------
    def __init__(
        self,
        out_dir: Path,
        channel: Channel,
        source : Project,
        target : Project,
        sample : Component,
        brem   : Brem,
        q2bin  : Qsq):
        '''
        Parameters
        ---------------
        channel      : E.g. electron or muon
        out_dir      : Directory where outputs will be saved
        sample       : Component associated to efficiency needed
        source/target: Trigger associated to the signal region where the yield
                       will be measured/applied
        brem/q2bin   : Brem category and q2bin associated to regions
        '''
        self.__out_dir= out_dir
        self.__channel= channel
        self.__source = source
        self.__target = target
        self.__sample = sample
        self.__brem   = brem
        self.__q2bin  = q2bin
    # -------------------------
    def _get_ef(self, project : Project) -> GVar:
        '''
        Parameters
        --------------
        project: Trigger to which efficiencies are associated

        Returns
        --------------
        Gaussian random variable representing efficiency
        '''
        log.debug(f'Calculating efficiencies for {self.__sample}')

        trigger = Trigger.get_main_trigger(
            channel = self.__channel, 
            project = project)

        with sel.update_selection(d_sel = self.__brem.region.selection):
            obj = EfficiencyCalculator(
                out_dir= self.__out_dir,
                q2bin  = self.__q2bin, 
                sample = self.__sample, 
                trigger= trigger)
            val, err = obj.get_efficiency()

        log.debug(f'Efficiency: {val}')

        return gvar(val, err) 
    # -------------------------
    def get_value(self) -> tuple[float,float]:
        '''
        Returns
        -----------
        Tuple with value and error of scale factor
        '''
        eff_src = self._get_ef(project = self.__source)
        eff_tgt = self._get_ef(project = self.__target)
        scale   = eff_tgt / eff_src

        log.debug(f'Source efficiency: {eff_src}')
        log.debug(f'Target efficiency: {eff_tgt}')

        return scale.mean, scale.sdev
# -------------------------
