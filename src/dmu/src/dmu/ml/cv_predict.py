'''
Module holding CVPredict class
'''
import pandas           as pnd
import numpy
import tqdm
import dmu.ml.utilities as ut

from ROOT.RDF              import RNode
from dmu.ml.cv_classifier  import CVClassifier
from dmu.logging.log_store import LogStore
from dmu.rdataframe        import utilities as rut

log = LogStore.add_logger('dmu:ml:cv_predict')
# ---------------------------------------
class CVPredict:
    '''
    Class used to get classification probabilities from ROOT
    dataframe and a set of models. The models were trained with CVClassifier
    '''
    def __init__(
        self,
        rdf    : RNode,
        models : list[CVClassifier]):
        '''
        Will take a list of CVClassifier models and a ROOT dataframe

        rdf   : ROOT dataframe where features will be extracted
        models: List of models, one per fold
        '''
        self._l_model   = models
        self._rdf       = rdf
        self._nrows     : int
        self._l_column  : list[str]
        self._d_nan_rep : dict[str,str]

        # Value of score used when no score has been assigned
        self._dummy_score = -1.0

        # name of column in ROOT dataframe where 1s will prevent prediction
        self._skip_index_column = 'skip_mva_prediction'

        # name of attribute of features dataframe where array of indices to skip are stored
        self._index_skip  = 'skip_mva_prediction'
    # --------------------------------------------
    def _initialize(self):
        self._rdf       = self._remove_periods(self._rdf)
        self._rdf       = self._define_columns(self._rdf)
        self._d_nan_rep = self._get_nan_replacements()
        self._l_column  = self._get_column_names()
        self._nrows     = self._rdf.Count().GetValue()
    # ----------------------
    def _get_column_names(self) -> list[str]:
        '''
        Returns
        -------------
        List of columns sorted and with friend tree preffixes removed, i.e. hop.hop_mass -> hop_mass
        '''
        l_name = []
        for name in rut.columns_from_rdf(rdf=self._rdf):
            if '.' not in name:
                l_name.append(name)
                continue

            if name.count('.') > 1:
                raise ValueError(f'Invalid column name {name}')

            notree_name = name.split('.')[-1]

            l_name.append(notree_name)

        return sorted(l_name)
    # ----------------------------------
    def _remove_periods(self, rdf : RNode) -> RNode:
        '''
        This will redefine all columns associated to friend trees as:

        friend_preffix.branch_name -> friend_preffix_branch_name
        '''
        l_col = rut.columns_from_rdf(rdf=rdf)
        l_col = [ col for col in l_col if '.' in col  ]

        if len(l_col) == 0:
            return rdf

        log.debug(60 * '-')
        log.debug('Renaming dotted columns')
        log.debug(60 * '-')
        for col in l_col:
            new = col.replace('.', '_')
            log.debug(f'{col:<50}{"->":10}{new:<20}')
            rdf = rdf.Define(new, col)

        return rdf
    # --------------------------------------------
    def _get_definitions(self) -> dict[str,str]:
        '''
        This method will search in the configuration the definitions used
        on the dataframe before the dataframe was used to train the model.

        Returns
        -----------
        dictionary with definitions, generic, signal specific, both or none
        (i.e. empty dictionary) depending on how model was trained
        '''
        cfg   = self._l_model[0].cfg
        d_def = {}
        if 'define' in cfg['dataset']:
            d_def_gen = cfg['dataset']['define'] # get generic definitions
            d_def.update(d_def_gen)

        sig_name = 'sig'
        try:
            # Get sample specific definitions. This will be taken from the signal section
            # because predicted scores should come from features defined as for the signal.
            d_def_sam = cfg['dataset']['samples'][sig_name]['definitions']
        except KeyError:
            log.debug(f'No sample specific definitions were found in: {sig_name}')
            return d_def

        log.info('Adding sample dependent definitions')
        d_def.update(d_def_sam)

        return d_def
    # --------------------------------------------
    def _define_columns(self, rdf : RNode) -> RNode:
        d_def = self._get_definitions()
        if len(d_def) == 0:
            log.info('No definitions found')
            return self._rdf

        dexc = None
        log.debug(60 * '-')
        log.info('Defining columns in RDF before evaluating classifier')
        log.debug(60 * '-')
        for name, expr in d_def.items():
            expression = expr.replace('.', '_')

            log.debug(f'{name:<20}{"<---":20}{expression:<100}')
            try:
                rdf = rdf.Define(name, expression)
            except TypeError as exc:
                log.error(f'Cannot define {name}={expression}')
                dexc = exc

        if dexc is not None:
            raise TypeError('Could not define at least one column') from dexc

        return rdf
    # --------------------------------------------
    def _get_nan_replacements(self) -> dict[str,str]:
        cfg = self._l_model[0].cfg

        if 'nan' not in cfg['dataset']:
            log.debug('No define section found in config, will not define extra columns')
            return {}

        return cfg['dataset']['nan']
    # --------------------------------------------
    def _replace_nans(self, df_ft : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Funtion replaces nans in user specified columns with user specified values
        These NaNs are expected
        '''
        if len(self._d_nan_rep) == 0:
            log.debug('Not doing any NaN replacement')
            return df_ft

        log.info(60 * '-')
        log.info('Doing NaN replacements')
        log.info(60 * '-')
        for var, val in self._d_nan_rep.items():
            log.info(f'{var:<20}{"--->":20}{val:<20.3f}')
            df_ft[var] = df_ft[var].fillna(val)

        return df_ft
    # --------------------------------------------
    def _df_from_rdf(self, features : list[str]) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        features: List of feature names

        Returns
        -------------
        Pandas dataframe with features
        '''
        l_missing_feature = []
        for feature in features:
            if feature not in self._l_column:
                log.error(f' Missing {feature} feature')
                l_missing_feature.append(feature)

        if l_missing_feature:
            for column in self._l_column:
                log.info(column)
            raise ValueError('At least one column is missing')

        data = self._rdf.AsNumpy(features)
        df   = pnd.DataFrame(data)

        return df
    # --------------------------------------------
    def _get_df(self) -> pnd.DataFrame:
        '''
        Will make ROOT rdf into dataframe and return it
        '''
        model = self._l_model[0]
        l_ft  = model.features
        df_ft = self._df_from_rdf(features=l_ft)
        df_ft = self._replace_nans(df_ft=df_ft)
        df_ft = self._tag_skipped(df_ft=df_ft)
        df_ft = ut.tag_nans(
            df      = df_ft,
            indexes = self._index_skip)

        nfeat = len(l_ft)
        log.info(f'Found {nfeat} features')
        for name in l_ft:
            log.debug(name)

        return df_ft
    # --------------------------------------------
    def _tag_skipped(self, df_ft : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Will drop rows with features where column with name _skip_name (currently "_skip_mva_prediction") has values of 1
        '''
        if self._skip_index_column not in self._l_column:
            log.debug(f'Not dropping any rows through: {self._skip_index_column}')
            return df_ft

        log.info(f'Dropping rows through: {self._skip_index_column}')
        arr_drop                = self._rdf.AsNumpy([self._skip_index_column])[self._skip_index_column]

        if self._index_skip in df_ft.attrs:
            raise ValueError(f'Feature dataframe already contains attribute: {self._index_skip}')

        df_ft.attrs[self._index_skip] = numpy.where(arr_drop == 1)[0]

        return df_ft
    # --------------------------------------------
    def _non_overlapping_hashes(self, model, df_ft):
        '''
        Will return True if hashes of model and data do not overlap
        '''

        s_mod_hash = model.hashes
        s_dff_hash = ut.get_hashes(df_ft, rvalue = 'set')

        s_int = s_mod_hash.intersection(s_dff_hash)
        if len(s_int) == 0:
            return True

        return False
    # --------------------------------------------
    def _predict_with_overlap(self, df_ft : pnd.DataFrame) -> numpy.ndarray:
        '''
        Takes pandas dataframe with features

        Will return numpy array of prediction probabilities when there is an overlap
        of data and model hashes
        '''
        df_ft      = ut.index_with_hashes(df_ft)
        d_prob     = {}
        ntotal     = len(df_ft)
        log.debug(30 * '-')
        log.info(f'Total size: {ntotal}')
        log.debug(30 * '-')
        for model in tqdm.tqdm(self._l_model, ascii=' -'):
            d_prob_tmp = self._evaluate_model(model, df_ft)
            d_prob.update(d_prob_tmp)

        ndata  = len(df_ft)
        nprob  = len(d_prob)
        if ndata != nprob:
            log.warning(f'Dataset size ({ndata}) and probabilities size ({nprob}) differ, likely there are repeated entries')

        l_prob = [ d_prob[hsh] for hsh in df_ft.index ]

        return numpy.array(l_prob)
    # --------------------------------------------
    def _evaluate_model(
        self,
        model : CVClassifier,
        df_ft : pnd.DataFrame) -> dict[str, float]:
        '''
        Parameters:
        ------------------------
        model: Model used to predict probability for samples not involved in the model training
        df_ft: Dataframe with features, whose probabilities have to be predicted

        Returns
        ------------------------
        Dictionary with:

        Key  : Hash representing the features
        Value: Probability
        '''
        s_dat_hash : set[str] = set(df_ft.index)
        s_mod_hash : set[str] = model.hashes

        s_dif_hash = s_dat_hash - s_mod_hash
        if not s_dif_hash:
            log.warning(f'All {len(s_dat_hash)} were used to train fold, skipping prediction')
            return dict()

        ndif = len(s_dif_hash)
        ndat = len(s_dat_hash)
        nmod = len(s_mod_hash)
        log.debug(f'{ndif:<10}{"=":5}{ndat:<10}{"-":5}{nmod:<10}')

        df_ft_group= df_ft.loc[df_ft.index.isin(s_dif_hash)]

        l_prob = model.predict_proba(df_ft_group)
        l_hash = list(df_ft_group.index)
        nfeat  = len(df_ft_group)
        nprob  = len(l_prob)

        if nfeat != nprob:
            raise ValueError(f'Number of features and probabilities do not agree: {nfeat} != {nprob}')

        d_prob = dict(zip(l_hash, l_prob, strict=True))

        return d_prob
    # --------------------------------------------
    def _predict_signal_probabilities(
        self,
        model : CVClassifier,
        df_ft : pnd.DataFrame) -> numpy.ndarray:
        '''
        Takes model and features dataframe, returns array of signal probabilities
        '''
        nentries = len(df_ft)
        if nentries == 0:
            raise ValueError('Found empty dataset')
        else:
            log.debug(f'Will run prediction with {nentries} entries')

        if self._non_overlapping_hashes(model, df_ft):
            log.debug('No intersecting hashes found between model and data')
            arr_prb = model.predict_proba(df_ft)
        else:
            log.info('Intersecting hashes found between model and data')
            arr_prb = self._predict_with_overlap(df_ft)

        arr_sig_prb = arr_prb.T[1]

        return arr_sig_prb
    # --------------------------------------------
    def predict(self) -> numpy.ndarray:
        '''
        Will return array of prediction probabilities for the signal category
        '''
        self._initialize()

        df_ft = self._get_df()
        model = self._l_model[0]

        arr_keep = None
        arr_skip = None
        if self._index_skip in df_ft.attrs:
            log.debug(f'Filtering dataframe by index: {self._index_skip}')
            ninit    = len(df_ft)
            arr_skip = df_ft.attrs[self._index_skip]
            df_ft    = df_ft.drop(arr_skip)
            arr_keep = df_ft.index.to_numpy()
            nfnal    = len(df_ft)

            if nfnal == 0:
                log.warning(f'Index skipping produced empty dataset {ninit} -> {nfnal} returning dummy scores: {self._dummy_score}')
                return numpy.array(ninit * [self._dummy_score])
            else:
                log.info(f'Index skipping: {ninit} -> {nfnal}')
        else:
            log.debug('Not filtering dataframe by index')

        arr_sig_prb  = self._predict_signal_probabilities(
            model = model,
            df_ft = df_ft)

        if arr_skip is None:
            return arr_sig_prb

        arr_all_sig_prb           = numpy.full(self._nrows, self._dummy_score)
        arr_all_sig_prb[arr_keep] = arr_sig_prb

        return arr_all_sig_prb
# ---------------------------------------
