'''
Module holding DataPreprocessor class
'''
import numpy
import pandas   as pnd

from pathlib         import Path
from ROOT            import RDF # type: ignore
from typing          import Final

from dmu             import LogStore
from dmu.workflow    import Cache
from dmu.stats       import utilities  as sut
from dmu.generic     import utilities  as gut
from dmu.rdataframe  import utilities  as rut
from dmu.pdataframe  import utilities  as put

from zfit            import Space      as zobs
from zfit.data       import Data

from rx_data         import RDFGetter
from rx_common       import Component, Qsq, Trigger, Correction, Cuts
from rx_selection    import selection  as sel
from rx_misid        import SampleSplitter
from rx_misid        import SampleWeighter
from rx_misid        import MisIDSampleWeights

log=LogStore.add_logger('fitter:data_preprocessor')

_WEIGHT_BRANCH : Final[str] = 'weight'
# ------------------------
# TODO: Shold this class take a dictionary of cuts? 
# Should this be made into a context manager?
class DataPreprocessor(Cache):
    '''
    Class in charge of providing datasets for fitting by:

    - Loading ROOT files through RDFGetter
    - Applying selection
    - Transforming data into format that zfit can use
    '''
    # ------------------------
    def __init__( # noqa: PLR0917
        self,
        name      : str,
        obs       : zobs,
        sample    : Component,
        trigger   : Trigger,
        q2bin     : Qsq,
        wgt_cfg   : dict[Correction,MisIDSampleWeights] | None,
        is_sig    : bool                  = True,
        selection : dict[Cuts,str] | None = None):
        '''
        Parameters
        --------------------
        name       : Optional name of dataset, e.g. fit category brem_x12
        obs        : zfit observable
        sample     : e.g. DATA_24_MagUp...
        trigger    : e.g. Hlt2RD...
        q2bin      : e.g. central
        max_entries: If used (default None), limit number of entries to this value
        is_sig     : If true (default) it will pick PID weights for signal region.
                 Otherwise it will use misID control region weights.
        selection  : Selection defining this component category, represented by dictionary where the key are labels
                     and the values are the expressions of the cut. These cuts will update current (not default!!!) selection0
        wgt_cfg    : Dictionary with:
            key: Representing kind of weight, e.g. pid
            value: Actual configuration for kind of weight, in a pydantic model
        '''
        selection = dict() if selection is None else selection

        self._name   = name
        self._obs    = obs
        self._sample = sample
        self._trigger= trigger
        self._q2bin  = q2bin
        self._wgt_cfg= wgt_cfg

        # Caching will remove all files
        # Need to keep around selection
        # To save it at the end
        rdf, cuts    = self._get_rdf(selection = selection)
        self._is_sig = is_sig
        self._rdf    = rdf 
        self._cuts   = cuts

        super().__init__(
            out_path = Path(self._sample) / 'dataset' / self._name,
            obs_name = sut.name_from_obs(obs=obs),
            obs_range= sut.range_from_obs(obs=obs),
            d_sel    = cuts,
            is_sig   = is_sig,
            wgt_cfg  = '' if self._wgt_cfg is None else {key : val.model_dump() for key, val in self._wgt_cfg.items()}, 
            rdf_uid  = rdf.uid)
    # ------------------------
    def _get_rdf(
        self, 
        selection : dict[Cuts,str]) -> tuple[RDF.RNode, dict[Cuts,str]]:
        '''
        Parameters
        -------------------
        selection: Selection to be added on top, used for categories.

        Returns
        -------------------
        Tuple with:
           - ROOT dataframe after selection and with Unique identifier attached as uid
           - Dictionary storing selection
        '''
        log.debug(f'Retrieving dataframe for {self._sample}/{self._trigger}')
        gtr = RDFGetter(
            sample  =self._sample,
            trigger =self._trigger)

        rdf_raw = gtr.get_rdf(per_file=False)
        uid     = gtr.get_uid()

        log.debug(f'Applying selection to {self._sample}/{self._trigger}')

        if Cache._cache_root is None:
            raise ValueError('Cache root directory not defined')

        # NOTE: Update selection such that category selection
        # is applied on top of potentially non-default selection
        # Current selection might contain different cuts,
        # e.g. special BDT cut or special brem choice
        with sel.update_selection(d_sel=selection):
            rdf_sel = sel.apply_full_selection(
                rdf     = rdf_raw,
                uid     = uid,
                q2bin   = self._q2bin,
                trigger = self._trigger,
                process = self._sample,
                out_path= 0) # keep this lazy, do not execute and save selection

            cuts = sel.selection(
                process = self._sample, 
                trigger = self._trigger, 
                q2bin   = self._q2bin)

        log.debug('Applied selection')

        return rdf_sel, cuts
    # ------------------------
    def _get_report(self) -> pnd.DataFrame:
        '''
        This will trigger graph execution

        Returns
        --------------
        Pandas dataframe with cutflow
        '''
        rep = self._rdf.Report()
        df  = rut.rdf_report_to_df(rep=rep)

        rep.Print()
        for name, val in self._cuts.items():
            log.info(f'{name:<15}{val}')

        return df
    # ------------------------
    def _add_extra_weights(self, wgt : numpy.ndarray) -> numpy.ndarray:
        '''
        Parameters
        -------------
        wgt: Array of weights already held in ROOT dataframe

        Returns
        -------------
        Optionally augmented weights
        '''
        if self._wgt_cfg is None:
            log.debug('No weight configuration found, using only default weights')
            return wgt

        for correction, cfg in self._wgt_cfg.items():
            new_wgt = self._get_extra_weight(kind=correction, cfg=cfg)
            if new_wgt.shape != wgt.shape:
                raise ValueError(
                    f'''Shapes of original array and correction {correction} weights differ:
                        {new_wgt.shape} != {wgt.shape}''')

            wgt = wgt * new_wgt

        return wgt
    # ----------------------
    def _get_extra_weight(
        self, 
        kind : Correction, 
        cfg  : MisIDSampleWeights) -> numpy.ndarray:
        '''
        Parameters
        -------------
        kind: E.g. PID, Dalitz
        cfg : Configuration needed to extract weights

        Returns
        -------------
        Array of weights
        '''
        match kind:
            case Correction.pid:
                log.debug('Adding PID weights')
                return self._get_pid_weights(cfg=cfg)
            case _:
                raise ValueError(f'Invalid correction {kind}')
    # ----------------------
    def _get_pid_weights(self, cfg : MisIDSampleWeights) -> numpy.ndarray:
        '''
        Parameters
        -------------
        cfg : Dictionary containing configuration for PID, i.e. it should have keys
              `splitting` and `weights` as used in the rx_misid project

        Returns
        -------------
        Array with PID weights
        '''
        log.info(f'Splitting sample: {self._sample}/{self._q2bin}')
        spl   = SampleSplitter(
            rdf     = self._rdf, 
            out_dir = self._out_path,
            cfg     = cfg.splitting)
        df    = spl.get_sample()

        log.info(f'Getting PID weights for: {self._sample}/{self._q2bin}')
        wgt   = SampleWeighter(
            df    = df,
            cfg   = cfg,
            sample= self._sample,
            is_sig= self._is_sig)
        df  = wgt.get_weighted_data()

        return df['pid_weights'].to_numpy()
    # ------------------------
    def _get_array(self) -> tuple[numpy.ndarray,numpy.ndarray]:
        '''
        Return a tuple of numpy arrays with the observable and weight
        for the sample requested, this array is fully selected
        '''
        log.debug(f'Extracting data through RDFGetter for sample {self._sample}')

        rdf         = self._rdf
        branch_name = self._obs.label
        log.debug(f'Retrieving masses/weights from: {branch_name}/{_WEIGHT_BRANCH}')
        arr  = rdf.AsNumpy([branch_name])[branch_name]
        wgt  = rdf.AsNumpy([_WEIGHT_BRANCH])[_WEIGHT_BRANCH]
        wgt  = wgt.astype(float)
        wgt  = self._add_extra_weights(wgt=wgt)

        nevt = len(arr)
        log.debug(f'Found {nevt} entries')

        return arr, wgt
    # ------------------------
    @property
    def rdf_uid(self) -> str:
        '''
        Unique identifier of ROOT dataframe after selection
        '''
        uid = getattr(self._rdf, 'uid', None)

        if not isinstance(uid, str):
            raise ValueError(f'Dataframe UID expected, got: {uid}')

        return uid
    # ------------------------
    def _data_from_numpy(
        self,
        arr_value : numpy.ndarray,
        arr_weight: numpy.ndarray) -> Data:
        '''
        We should not use weights if they are all 1s due to problems in zfit

        Parameters
        ------------
        arr_value : Array with values to be fitted
        arr_weight: Array with weights

        Returns
        ------------
        zfit data.
        '''

        arr_is_close = numpy.isclose(arr_weight, 1.0, rtol=1e-5)

        if numpy.all(arr_is_close):
            log.debug('Not using weights for dataset where all weights are 1')
            wgt = None
        else:
            log.debug('Using weights in dataset')
            wgt = arr_weight

        data = Data.from_numpy(obs=self._obs, array=arr_value, weights=wgt)
        if not isinstance(data, Data):
            raise TypeError('Return type of unbinned data is not Data')

        return data
    # ------------------------
    def get_data(self) -> Data:
        '''
        Returns
        ---------------------
        zfit data, should be ready to be used in fit
        '''
        hash_dir = self._get_dir(kind = 'hash', make = False)
        log.debug(f'Looking for: {hash_dir}/data.npz')
        data_path = self._out_path / 'data.npz'
        if self._copy_from_cache():
            log.info(f'Data found cached, loading: {data_path}')
            with numpy.load(data_path) as ifile:
                arr : numpy.ndarray = ifile['values' ]
                wgt : numpy.ndarray = ifile['weights']

            data    = self._data_from_numpy(arr_value=arr, arr_weight=wgt)
            return data

        log.info('Data not found cached, rebuilding dataset')
        arr, wgt  = self._get_array()
        data      = self._data_from_numpy(arr_value=arr, arr_weight=wgt)
        cuts_path = data_path.with_suffix('.yaml')
        gut.dump_json(data=self._cuts , path=cuts_path)

        ctfl_path = cuts_path.with_suffix('.md')
        df_ctf    = self._get_report()

        put.to_markdown(df=df_ctf, path=ctfl_path)

        numpy.savez_compressed(data_path, values=arr, weights=wgt)
        self._cache()

        return data
# ------------------------
