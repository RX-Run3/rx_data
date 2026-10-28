'''
Module containing EfficiencyCalculator class
'''
import os
import math
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib            import Path
from ROOT               import RDF
from dmu                import LogStore
from dmu.workflow       import Cache
from dmu.generic        import hashing

from rx_common          import Component, Qsq, Trigger
from rx_data            import RDFGetter
from rx_selection       import selection as sel
from .acceptance_reader import AcceptanceReader

log=LogStore.add_logger('rx_efficiencies:efficiency_calculator')
#------------------------------------------
class EfficiencyCalculator(Cache):
    '''
    Class used to calculate efficiencies for:

    - Full nominal selection
    - Full selection defined as the product of the acceptance, selection and reconstruction efficiencies
    '''
    #------------------------------------------
    def __init__(
        self, 
        out_dir : Path,
        q2bin   : Qsq, 
        trigger : Trigger,
        sample  : Component):
        '''
        Parameters
        -----------------
        out_dir : Full path to directory where outputs will go
        q2bin   : Either low, central or high
        trigger : By default
        sample  : MC sample for which the efficiency is calculated
                  If None, will calculate it for all samples from rx_common::types.Sample 
        '''
        self._q2bin   = q2bin
        self._year    = '2024'
        self._trigger = trigger 
        self._d_sel   = {'Sample' : [], 'Decay' : [], 'Value' : [], 'Error' : []}
        self._sample  = sample 

        plt.style.use(mplhep.style.LHCb2)

        super().__init__(
            out_path = out_dir / 'efficiencies' / f'{sample}_{q2bin}_{trigger.value}',
            d_sel    = self._get_selection_hash(),
            q2bin    = self._q2bin,
            trigger  = self._trigger,
            sample   = sample)

        self._initialized=False
    #------------------------------------------
    def _get_selection_hash(self) -> str:
        '''
        Returns
        ------------
        Hash associated to selection for all the processes used, trigger and q2bin
        '''
        d_sel = sel.selection(q2bin=self._q2bin, trigger=self._trigger, process=self._sample)
        hsh   = hashing.hash_object(d_sel)

        return hsh
    #------------------------------------------
    @property
    def out_dir(self) -> str|None:
        '''
        Returns path to directory where validation plots should go
        '''
        if not hasattr(self, '_out_dir'):
            return None

        return self._out_dir

    @out_dir.setter
    def out_dir(self, value : str):
        try:
            os.makedirs(value, exist_ok=True)
        except:
            log.error(f'Cannot make: {value}')
            raise

        self._out_dir = value
    #------------------------------------------
    def _get_geo_eff(self, sample : Component) -> float:
        '''
        Takes sample and returns geometric acceptance
        '''
        obj = AcceptanceReader(
            sample =sample, 
            year   =self._year, 
            project=self._trigger.project)

        acc = obj.read()

        return acc
    #------------------------------------------
    def _add_sel_eff(
            self,
            passed : int,
            total  : int,
            sample : Component) -> None:
        eff = passed / total
        err = math.sqrt(eff * (1 - eff) / total)

        self._d_sel['Sample'].append(sample)
        self._d_sel['Decay' ].append(sample.latex)
        self._d_sel['Value' ].append(eff)
        self._d_sel['Error' ].append(err)
    #------------------------------------------
    def _get_yields(self, sample : Component) -> tuple[int,int]:
        sel_yld = self._get_sel_yld(sample)
        gen_yld = self._get_gen_yld(sample)
        geo_acc = self._get_geo_eff(sample)
        tot_yld = int(gen_yld / geo_acc)

        self._add_sel_eff(passed=sel_yld, total=gen_yld, sample=sample)

        return sel_yld, tot_yld
    #------------------------------------------
    def _get_sel_yld(self, sample : Component) -> int:
        log.info('Calculating selected yield')

        rdf = self._get_rdf(sample=sample, tree_name='DecayTree')
        rdf = sel.apply_full_selection(
            q2bin   = self._q2bin,
            trigger = self._trigger,
            process = sample,
            out_path= self._out_path / sample,
            rdf     = rdf)

        nsel = rdf.Count().GetValue()

        return nsel
    #------------------------------------------
    def _get_rdf(self, sample : Component, tree_name : str) -> RDF.RNode:
        gtr = RDFGetter(
            sample  = sample, 
            trigger = self._trigger, 
            tree    = tree_name)
        rdf = gtr.get_rdf(per_file=False)

        return rdf
    #------------------------------------------
    def _get_gen_yld(self, sample : Component) -> int:
        rdf      = self._get_rdf(sample=sample, tree_name='MCDecayTree')
        nentries = rdf.Count().GetValue()

        return nentries
    #------------------------------------------
    def _get_stats(self) -> pnd.DataFrame:
        '''
        Returns pandas dataframe with `Passed` and `Total` yields for a given `Process`
        '''
        d_data   = {'Sample' : [], 'Passed' : [], 'Total' : [], 'Eff' : []}
        log.info(f'Calculating yields for sample: {self._sample}')
        pas, tot = self._get_yields(sample = self._sample)

        d_data['Sample' ].append(self._sample)
        d_data['Passed' ].append(pas)
        d_data['Total'  ].append(tot)
        d_data['Eff'    ].append(pas / tot)

        df = pnd.DataFrame(d_data)

        return df
    #------------------------------------------
    def _efficiency_from_sample(
        self,
        as_yields : bool,
        df        : pnd.DataFrame) -> tuple[float,float]:
        '''
        Parameters
        -----------------
        as_yields : If true will return passed and failed, otherwise, efficiency and error
        df        : Dataframe with yields, passed and failed for each sample

        Returns
        -----------------
        Tuple with:
           Efficiency value
           Error in efficiency
        '''
        df_org = df

        df = df[ df['Sample'] == self._sample ]

        if len(df) != 1:
            log.error('\n' + str(df_org))
            log.error('')
            log.error('--->')
            log.error('')
            log.error(df)
            raise ValueError(f'After specifying process {self._sample.name} dataframe does not have one and only one column')

        pas : float = df['Passed'].iloc[0]
        tot : float = df['Total' ].iloc[0]

        if as_yields:
            return pas, tot - pas

        eff = pas / tot
        err = math.sqrt(eff * (1 - eff) / tot)

        return eff, err
    #------------------------------------------
    def get_efficiency(self, as_yields : bool = False) -> tuple[float,float]:
        '''
        Parameters
        -------------
        as_yields: If true, it will return passed and failed yields. 
        Otherwise efficiency and error

        Returns
        -------------
        Tuple with effiency and error associated
        '''
        data_path = f'{self._out_path}/yields.json'
        if self._copy_from_cache():
            log.info(f'Found yields cached, loading: {data_path}')
            df = pnd.read_json(path_or_buf=data_path)

            return self._efficiency_from_sample(df=df, as_yields=as_yields)

        log.info(f'Recalculating dataframe with yields for {self._sample.name}')
        df = self._get_stats()
        df.to_json(path_or_buf=data_path, indent=2)

        self._cache()
        return self._efficiency_from_sample(df=df, as_yields=as_yields)
#------------------------------------------
