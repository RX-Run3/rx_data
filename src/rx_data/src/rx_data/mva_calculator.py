'''
This module contains the MVACalculator class
'''

import os
import re
import glob
from typing import overload, Literal

import joblib
import numpy
import pandas as pnd

from ROOT                  import RDF
from dmu.ml.cv_predict     import CVClassifier, CVPredict
from dmu.logging.log_store import LogStore
from dmu.generic           import version_management as vman
from rx_selection          import selection          as sel
from rx_common             import Component, Cuts, Qsq, Trigger

log = LogStore.add_logger('rx_data:mva_calculator')
#---------------------------------
class MVACalculator:
    '''
    This class is meant to plug the ROOT dataframe with data and MC
    with the classifiers and produce friend trees in the form of a dataframe
    '''
    # ----------------------
    def __init__(
        self,
        rdf     : RDF.RNode,
        sample  : Component,
        trigger : Trigger,
        version : str  = 'latest',
        nfold   : int  = 10,
        dry_run : bool = False) -> None:
        '''
        Parameters
        -------------
        rdf    : Dataframe with main sample
        version: Version of classifier, by default latest
        sample : E.g. DATA_24... # Needed to get q2 selection
        trigger: HLT2 triger     # to switch models
        nfold  : Number of expected folds, 10 by default. Used to validate inputs
        dry_run: If true, will not evaluate models, but stop early and assign 1s
        '''
        rdf = rdf.Define('index', 'rdfentry_')

        self._rdf         = rdf
        self._sample      = sample
        self._trigger     = trigger
        self._max_path    = 700
        self._nfold       = nfold
        self._ana_dir     = os.environ['ANADIR']
        # TODO: Update this.
        # Jpsi and Psi2 should use central MVA
        # Above high data should use high MVA
        self._default_q2  = Qsq.central # Any entry not in [low, central, high] bins will go to this bin for prediction
        self._version     = version
        self._project     = trigger.project
        self._l_model     : list[CVClassifier]
        self._dry_run     = dry_run
    #---------------------------------
    def _get_q2_selection(self, q2bin : Qsq) -> str:
        '''
        Parameters
        ---------------
        q2bin: E.g. central, needed to retrieve selection used to switch classifiers

        Returns
        ---------------
        string defining q2 selection
        '''
        d_sel = sel.selection(
            trigger    = self._trigger,
            q2bin      = q2bin,
            skip_truth = True,
            process    = self._sample)

        q2_cut = d_sel[Cuts.q2]

        return q2_cut
    #---------------------------------
    def _apply_q2_cut(
        self,
        rdf   : RDF.RNode,
        q2bin : Qsq) -> RDF.RNode:
        '''
        Parameters
        --------------
        rdf  : ROOT dataframe with contents of main tree
        q2bin: E.g. central

        Returns
        --------------
        Dataframe after q2 selection
        '''
        if q2bin == Qsq.none:
            low     = self._get_q2_selection(q2bin=Qsq.low)
            central = self._get_q2_selection(q2bin=Qsq.central)
            high    = self._get_q2_selection(q2bin=Qsq.high)
            q2_cut  = f'!({low}) && !({central}) && !({high})'
        else:
            q2_cut  = self._get_q2_selection(q2bin=q2bin)

        log.debug(f'{q2bin:<10}{q2_cut}')
        rdf = rdf.Filter(q2_cut, 'q2')

        nentries = rdf.Count().GetValue()

        if nentries == 0:
            log.warning(f'Found {nentries} entries for {q2bin} bin')
        else:
            log.debug(f'Found {nentries} entries for {q2bin} bin')

        return rdf
    # ----------------------------------------
    def _q2_scores(
        self,
        d_path : dict[str,str],
        q2bin  : Qsq) -> numpy.ndarray:
        '''
        Parameters
        -----------
        d_path: Dictionary mapping q2bin to path to models
        q2bin : q2 bin

        Returns
        -----------
        2D Array with indexes and MVA scores
        '''
        rdf     = self._apply_q2_cut(rdf=self._rdf, q2bin=q2bin)
        nentries= rdf.Count().GetValue()
        if nentries == 0:
            log.warning(f'No entries found for q2 bin: {q2bin}')
            return numpy.column_stack(([], []))

        # The dataframe has the correct cut applied
        # From here onwards, if the q2bin is non-rare (rest)
        # Will use default_q2 model
        if q2bin == Qsq.none:
            q2bin = self._default_q2

        path   = d_path[q2bin]
        l_pkl  = glob.glob(f'{path}/*.pkl')

        npkl   = len(l_pkl)
        if npkl == 0:
            raise ValueError(f'No pickle files found in {path}')

        log.info(f'Using {npkl} pickle files from: {path}')
        l_model = [ joblib.load(pkl_path) for pkl_path in l_pkl ]

        cvp     = CVPredict(models=l_model, rdf=rdf)
        if self._dry_run:
            log.warning(f'Using {nentries} ones for dry run MVA scores')
            arr_prb = numpy.ones(nentries)
        else:
            try:
                arr_prb = cvp.predict()
            except ValueError as exc:
                rdf.Display().Print()
                raise ValueError(f'Prediction failed for {q2bin} bin with {nentries} entries') from exc

        arr_ind = rdf.AsNumpy(['index'])['index']
        arr_res = numpy.column_stack((arr_ind, arr_prb))

        log.debug(f'Shape: {arr_res.shape}')

        return arr_res
    # ----------------------------------------
    def _get_scores(
        self,
        d_path : dict[str,str]) -> numpy.ndarray:
        '''
        Parameters
        ------------------
        d_path: Dictionary mapping q2bin to path to models

        Returns
        ------------------
        Array of signal probabilities
        '''
        arr_low     = self._q2_scores(d_path=d_path, q2bin=Qsq.low    )
        arr_central = self._q2_scores(d_path=d_path, q2bin=Qsq.central)
        arr_high    = self._q2_scores(d_path=d_path, q2bin=Qsq.high   )
        arr_rest    = self._q2_scores(d_path=d_path, q2bin=Qsq.none   )
        arr_all     = numpy.concatenate((arr_low, arr_central, arr_high, arr_rest))

        arr_ind = arr_all.T[0]
        arr_val = arr_all.T[1]

        nentries     = self._rdf.Count().GetValue()
        arr_obtained = numpy.sort(arr_ind)
        arr_expected = numpy.arange(nentries + 1)
        if  numpy.array_equal(arr_obtained, arr_expected):
            raise ValueError('Array of indexes has the wrong values')

        arr_ord = numpy.argsort(arr_ind)
        arr_mva = arr_val[arr_ord]

        return arr_mva
    # ----------------------
    def _get_latest_version(self, q2bin : str, kind : str) -> str:
        '''
        Parameters
        -------------
        q2bin: E.g. central
        kind : E.g. cmb, prc

        Returns
        -------------
        Path to directory with latest version
        '''
        root_path    = f'{self._ana_dir}/mva/{self._project}/{kind}'
        latest_path  = vman.get_last_version(dir_path=root_path, version_only=False)
        version_name = os.path.basename(latest_path)
        if not re.match(r'^v\d+(\.\d+)?$', version_name):
            raise ValueError(f'Version {version_name} is invalid')

        log.debug('Picking up latest version')
        path = f'{latest_path}/{q2bin}'

        return path
    # ----------------------
    def _get_mva_dir(self, q2bin : str, kind : str) -> str:
        '''
        Parameters
        -------------
        q2bin: E.g. central
        kind : Kind of classifier, e.g. cmb, prc

        Returns
        -------------
        Path to directory with classifier models
        '''
        if self._version != 'latest':
            log.warning(f'Picking up version {self._version} instead of latest')
            path = f'{self._ana_dir}/mva/{self._project}/{kind}/{self._version}/{q2bin}'
        else:
            path = self._get_latest_version(q2bin=q2bin, kind=kind)

        log.debug(f'For {q2bin}/{kind}, using models from: {path}')

        fail = False
        for ifold in range(self._nfold):
            model_path = f'{path}/model_{ifold:03}.pkl'
            if not os.path.isfile(model_path):
                log.error(f'Missing: {model_path}')
                fail = True

        if fail:
            raise FileNotFoundError('At least one model is missing')

        return path
    # ----------------------
    def _get_mva_dirs(self) -> dict:
        '''
        Returns
        -----------
        Dictionary with paths to directories with classifier models
        '''
        l_q2bin    = ['low', 'central', 'high']
        d_path_cmb = { q2bin : self._get_mva_dir(q2bin=q2bin, kind='cmb') for q2bin in l_q2bin }
        d_path_prc = { q2bin : self._get_mva_dir(q2bin=q2bin, kind='prc') for q2bin in l_q2bin }

        return {'cmb' : d_path_cmb, 'prc' : d_path_prc}
    # ----------------------------------------
    @overload
    def get_rdf(self, kind: Literal["root"  ]) -> RDF.RNode: ...
    @overload
    def get_rdf(self, kind: Literal["pandas"]) -> pnd.DataFrame: ...
    def get_rdf(self, kind) -> RDF.RNode|pnd.DataFrame:
        '''
        Parameters
        ----------------
        kind : Either 'root' or 'pandas'

        Returns
        ----------------
        Either a ROOT or a pandas dataframe
        '''
        if kind not in ['root', 'pandas']:
            raise NotImplementedError(f'Invalid format {kind}')

        d_mva_kind  = self._get_mva_dirs()
        d_mva_score = {}
        for name, d_path in d_mva_kind.items():
            log.info(f'Calculating {name} scores')
            arr_score = self._get_scores(d_path=d_path)
            d_mva_score[f'mva_{name}'] = arr_score

        log.info('Retrieving run number and event number columns')
        d_data = self._rdf.AsNumpy(['RUNNUMBER', 'EVENTNUMBER'])

        log.info('Adding classifier columns')
        d_data.update(d_mva_score)

        log.info('Building dataframe from Numpy')
        if kind == 'root':
            df = RDF.FromNumpy(d_data)
        elif kind == 'pandas':
            df = pnd.DataFrame(d_data)
        else:
            raise NotImplementedError(f'Invalid format {kind}')

        return df
#---------------------------------
