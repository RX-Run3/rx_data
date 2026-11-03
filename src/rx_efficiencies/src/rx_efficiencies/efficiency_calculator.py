'''
Module containing EfficiencyCalculator class
'''
import math
import pandas            as pnd

from typing             import Final
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
_YEAR : Final[str] = '2024'
_MCDT : Final[str] = 'MCDecayTree'
_RCDT : Final[str] = 'DecayTree'
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
        trigger : HLT2 trigger associated to sample
        sample  : MC sample for which the efficiency is calculated
        '''
        self._q2bin   = q2bin
        self._trigger = trigger
        self._sample  = sample

        super().__init__(
            out_path = out_dir / 'efficiencies' / f'{sample}_{q2bin}_{trigger.value}',
            d_sel    = self._get_selection_hash(),
            q2bin    = self._q2bin,
            trigger  = self._trigger,
            sample   = sample)
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
    def _get_geo_eff(self) -> float:
        '''
        Returns geometric acceptance
        '''
        obj = AcceptanceReader(
            sample = self._sample,
            year   = _YEAR,
            project= self._trigger.project)

        acc = obj.read()

        if acc <= 0:
            raise ValueError(f'Invalid geometric acceptance: {acc:.3f}')

        return acc
    #------------------------------------------
    def _get_yields(self) -> tuple[int,int]:
        sel_yld = self._get_sel_yld()
        gen_yld = self._get_gen_yld()
        geo_acc = self._get_geo_eff()
        tot_yld = int(gen_yld / geo_acc)

        return sel_yld, tot_yld
    #------------------------------------------
    def _get_sel_yld(self) -> int:
        log.info('Calculating selected yield')

        rdf = self._get_rdf(tree_name=_RCDT)
        rdf = sel.apply_full_selection(
            q2bin   = self._q2bin,
            trigger = self._trigger,
            process = self._sample,
            out_path= self._out_path / self._sample,
            rdf     = rdf)

        nsel = rdf.Count().GetValue()

        return nsel
    #------------------------------------------
    def _get_rdf(self, tree_name : str) -> RDF.RNode:
        gtr = RDFGetter(
            sample  = self._sample,
            trigger = self._trigger,
            tree    = tree_name)
        rdf = gtr.get_rdf(per_file=False)

        return rdf
    #------------------------------------------
    def _get_gen_yld(self) -> int:
        rdf      = self._get_rdf(tree_name=_MCDT)
        nentries = rdf.Count().GetValue()

        return nentries
    #------------------------------------------
    def _get_stats(self) -> pnd.DataFrame:
        '''
        Returns pandas dataframe with `Passed` and `Total` yields for a given `Process`
        '''
        d_data   = {'Sample' : [], 'Passed' : [], 'Total' : [], 'Eff' : []}
        log.info(f'Calculating yields for sample: {self._sample}')
        pas, tot = self._get_yields()

        d_data['Sample' ].append(self._sample)
        d_data['Passed' ].append(pas)
        d_data['Total'  ].append(tot)
        d_data['Eff'    ].append(pas / tot)

        df = pnd.DataFrame(d_data)

        return df
    #------------------------------------------
    def _efficiency_from_yields(
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
            log.error(
            f'''
            {df_org}

            --->

            {df}
            ''')
            raise ValueError(f'After specifying process {self._sample.name} dataframe does not have one and only one row')

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
        as_yields: Flag controlling return value format

        Returns
        -------------
        with as_yields:

        True : Tuple with passed and failed yields
        False: Tuple with efficiency and error associated
        '''
        data_path = self._out_path / 'yields.json'
        if self._copy_from_cache():
            log.info(f'Found yields cached, loading: {data_path}')
            df = pnd.read_json(path_or_buf=data_path)

            return self._efficiency_from_yields(df=df, as_yields=as_yields)

        log.info(f'Recalculating dataframe with yields for {self._sample.name}')
        df = self._get_stats()
        df.to_json(path_or_buf=data_path, indent=2)

        self._cache()
        return self._efficiency_from_yields(df=df, as_yields=as_yields)
#------------------------------------------
