'''
Module with TrainMva class
'''

import os
import copy
import math

from contextlib import contextmanager
from typing     import Final, Union
from functools  import partial

import tqdm
import joblib
import optuna
import pandas as pnd
import numpy
import matplotlib.pyplot as plt

from sklearn.metrics         import roc_curve, auc
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.ensemble        import GradientBoostingClassifier

from ROOT import RDF

import dmu.ml.utilities         as ut
import dmu.pdataframe.utilities as put
import dmu.plotting.utilities   as plu
import dmu.generic.utilities    as gut
import dmu.rdataframe.utilities as rut

from dmu.ml.cv_diagnostics   import CVDiagnostics
from dmu.ml.cv_classifier    import CVClassifier as cls
from dmu.plotting.plotter_1d import Plotter1D    as Plotter
from dmu.plotting.matrix     import MatrixPlotter
from dmu.logging.log_store   import LogStore, LogLevels

NPA = numpy.ndarray
log = LogStore.add_logger('dmu:ml:train_mva')

_OPTUNA_STARTUP_TRIALS : Final[int] = 10
_OPTUNA_WARMUP_STEPS   : Final[int] = 5
# ---------------------------------------------
class NoFeatureInfo(Exception):
    '''
    Used when information about a feature is missing in the config file
    '''
    def __init__(self, message : str):
        super().__init__(message)
# ---------------------------------------------
class TrainMva:
    '''
    Interface to scikit learn used to train classifier
    '''
    # TODO:
    # - Hyperparameter optimization methods should go into their own class
    # - Data preprocessing methods might need their own class
    # ---------------------------------------------
    def __init__(
        self,
        bkg : RDF.RNode,
        sig : RDF.RNode,
        cfg : dict):
        '''
        bkg (ROOT dataframe): Holds real data
        sig (ROOT dataframe): Holds simulation
        cfg (dict)          : Dictionary storing configuration for training
        '''
        self._cfg       = cfg
        self._auc       = math.nan # This is where the Area Under the ROC curve for the full sample will be saved
        self._l_ft_name = self._cfg['training']['features']
        self._pbar : tqdm.tqdm | None = None # Will be set if optimizing hyperparameters

        self._rdf_sig_org = sig
        self._rdf_bkg_org = bkg

        rdf_bkg = self._preprocess_rdf(rdf=bkg, kind='bkg')
        rdf_sig = self._preprocess_rdf(rdf=sig, kind='sig')

        df_ft_sig, l_lab_sig = self._get_sample_inputs(rdf = rdf_sig, label = 1)
        df_ft_bkg, l_lab_bkg = self._get_sample_inputs(rdf = rdf_bkg, label = 0)

        self._df_ft = pnd.concat([df_ft_sig, df_ft_bkg], axis=0)
        self._l_lab = numpy.array(l_lab_sig + l_lab_bkg)

        self._rdf_bkg = self._get_rdf(rdf = rdf_bkg, df_feat=df_ft_bkg)
        self._rdf_sig = self._get_rdf(rdf = rdf_sig, df_feat=df_ft_sig)

        self._rdm_state = 42 # Random state for training classifier
        self._nworkers  =  1 # Used to set number of workers for ANY process. Can be overriden with `use` context manager

        optuna.logging.set_verbosity(optuna.logging.WARNING)
    # ---------------------------------------------
    def _get_extra_columns(self, rdf : RDF.RNode, df : pnd.DataFrame) -> list[str]:
        d_plot = self._cfg['plotting']['features']['plots']
        l_expr = list(d_plot)
        l_rdf  = [ name for name in rdf.GetColumnNames() ]

        l_extr = []
        for expr in l_expr:
            if expr not in l_rdf:
                continue

            if expr in df.columns:
                continue

            l_extr.append(expr)

        return l_extr
    # ---------------------------------------------
    def _get_rdf(self, rdf : RDF.RNode, df_feat : pnd.DataFrame) -> RDF.RNode:
        '''
        Takes original ROOT dataframe and pre-processed features dataframe
        Adds missing branches to latter and returns expanded ROOT dataframe
        Need to make plots
        '''

        l_extr_col = self._get_extra_columns(rdf, df_feat)
        if not l_extr_col:
            log.debug('Not adding extra columns')
            return self._rdf_from_df(df=df_feat)

        if len(l_extr_col) > LogLevels.info:
            for name in l_extr_col:
                log.debug(name)
            raise ValueError('Found more than 20 extra columns')

        d_data = rdf.AsNumpy(l_extr_col)
        log.debug(f'Adding extra-nonfeature columns: {l_extr_col}')
        df_extr = pnd.DataFrame(d_data)

        nmain = len(df_feat.columns)
        nextr = len(df_extr.columns)

        log.debug(f'Main  DF size: {nmain}')
        log.debug(f'Extra DF size: {nextr}')

        df_all = pnd.concat([df_feat, df_extr], axis=1)

        return self._rdf_from_df(df=df_all)
    # ----------------------
    def _rdf_from_df(self, df : pnd.DataFrame) -> RDF.RNode:
        '''
        Parameters
        -------------
        df: Pandas dataframe

        Returns
        -------------
        Corresponding ROOT dataframe
        '''

        data = { name : self._array_from_df(df=df, col_name=name)  for name in df.columns }
        rdf  = RDF.FromNumpy(data)

        return rdf
    # ----------------------
    def _array_from_df(self, df : pnd.DataFrame, col_name : str) -> numpy.ndarray:
        '''
        Parameters
        -------------
        df: Dataframe
        col_name: Name of column requested

        Returns
        -------------
        Numpy array with column contents
        '''
        if col_name not in df.columns:
            raise ValueError(f'Invalid column {col_name} not found in {df.columns}')

        arr_val = df[col_name].to_numpy()

        try:
            arr_val = arr_val.astype(float)
        except Exception as exc:
            log.error(arr_val[:10])
            raise ValueError(f'Cannot cast as float column {col_name}') from exc

        return arr_val
    # ---------------------------------------------
    def _pre_process_nans(self, df : pnd.DataFrame) -> pnd.DataFrame:
        if 'dataset' not in self._cfg:
            return df

        if 'nan' not in self._cfg['dataset']:
            log.debug('dataset/nan section not found, not pre-processing NaNs')
            return df

        d_name_val = self._cfg['dataset']['nan']
        log.info(70 * '-')
        log.info('Doing NaN replacements')
        log.info(70 * '-')
        for var, val in d_name_val.items():
            nna = df[var].isna().sum()

            log.info(f'{var:<20}{"--->":20}{val:<20.3f}{nna}')
            df[var] = df[var].fillna(val)
        log.info(70 * '-')

        return df
    #---------------------------------
    def _add_sample_columns(
            self,
            rdf  : RDF.RNode,
            kind : str) -> RDF.RNode:
        '''
        This will apply sample specific column definitions
        to the dataframe
        '''
        try:
            d_def = self._cfg['dataset']['samples'][kind]['definitions']
        except KeyError:
            log.debug(f'Not found sample definitions for {kind}')
            return rdf

        log.info(60 * '-')
        log.info(f'Found sample definitions for {kind}')
        log.info(60 * '-')
        for name, expr in d_def.items():
            log.info(f'{name:<30}{"-->":<10}{expr:<20}')
            rdf = rdf.Define(name, expr)
        log.info(60 * '-')

        return rdf
    # ---------------------------------------------
    def _preprocess_rdf(self, rdf : RDF.RNode, kind : str) -> RDF.RNode:
        rdf = self._add_sample_columns(rdf, kind)

        if 'define' not in self._cfg['dataset']:
            log.debug('No definitions found')
            return rdf

        log.debug(f'Definitions found for {kind}')
        d_def = self._cfg['dataset']['define']
        for name, expr in d_def.items():
            log.debug(f'{name:<20}{expr}')
            try:
                rdf = rdf.Define(name, expr)
            except TypeError as exc:
                l_col = rut.columns_from_rdf(rdf=rdf)
                branch_list = 'found_branches.txt'
                gut.dump_text(lines=l_col, path=branch_list, exists_ok=True)

                raise TypeError(f'Branches found were dumped to {branch_list}') from exc

        return rdf
    # ---------------------------------------------
    def _get_sample_inputs(self, rdf : RDF.RNode, label : int) -> tuple[pnd.DataFrame, list[int]]:
        d_ft = rdf.AsNumpy(self._l_ft_name)
        df   = pnd.DataFrame(d_ft)
        df   = self._pre_process_nans(df)
        df   = ut.cleanup(df)
        l_lab= len(df) * [label]

        return df, l_lab
    # ---------------------------------------------
    def _get_model(self, arr_index : NPA) -> cls:
        model = cls(cfg = self._cfg)
        df_ft = self._df_ft.iloc[arr_index]
        l_lab = self._l_lab[arr_index]

        log.debug(f'Training feature shape: {df_ft.shape}')
        log.debug(f'Training label size: {len(l_lab)}')

        model.fit(df_ft, l_lab)

        return model
    # ---------------------------------------------
    def _get_models(self, load_trained : bool) -> list[cls]:
        '''
        Will create models, train them and return them
        '''
        if load_trained:
            log.warning('Not retraining, but loading trained models')
            return self._load_trained_models()

        nfold = self._cfg['training']['nfold']
        rdmst = self._cfg['training']['rdm_stat']

        kfold = StratifiedKFold(n_splits=nfold, shuffle=True, random_state=rdmst)

        l_model=[]
        ifold=0

        l_arr_lab_ts = []
        l_arr_all_ts = []
        l_arr_sig_ts = []
        l_arr_bkg_ts = []
        for arr_itr, arr_its in kfold.split(self._df_ft, self._l_lab):
            log.debug(20 * '-')
            log.info(f'Training fold: {ifold}')
            log.debug(20 * '-')
            model = self._get_model(arr_itr)
            l_model.append(model)

            arr_sig_tr, arr_bkg_tr, arr_all_tr, arr_lab_tr = self._get_scores(model, arr_itr, on_training_ok= True)
            arr_sig_ts, arr_bkg_ts, arr_all_ts, arr_lab_ts = self._get_scores(model, arr_its, on_training_ok=False)

            self._save_feature_importance(model, ifold)
            self._plot_correlations(arr_itr, ifold)
            self._plot_scores(
                ifold  =     ifold,
                sig_trn=arr_sig_tr,
                sig_tst=arr_sig_ts,
                bkg_trn=arr_bkg_tr,
                bkg_tst=arr_bkg_ts)

            xval_ts, yval_ts, _ = TrainMva.plot_roc(arr_lab_ts, arr_all_ts, kind='Test' , ifold=ifold)
            xval_tr, yval_tr, _ = TrainMva.plot_roc(arr_lab_tr, arr_all_tr, kind='Train', ifold=ifold)
            self._plot_probabilities(xval_tr, yval_tr, arr_all_tr, arr_lab_tr)
            self._save_roc_plot(ifold=ifold)

            self._save_roc_json(xval=xval_ts, yval=yval_ts, kind='Test' , ifold=ifold)
            self._save_roc_json(xval=xval_tr, yval=yval_tr, kind='Train', ifold=ifold)

            ifold+=1

            l_arr_lab_ts.append(arr_lab_ts)
            l_arr_all_ts.append(arr_all_ts)
            l_arr_sig_ts.append(arr_sig_ts)
            l_arr_bkg_ts.append(arr_bkg_ts)

        arr_lab_ts = numpy.concatenate(l_arr_lab_ts)
        arr_all_ts = numpy.concatenate(l_arr_all_ts)
        arr_sig_ts = numpy.concatenate(l_arr_sig_ts)
        arr_bkg_ts = numpy.concatenate(l_arr_bkg_ts)

        xval, yval, self._auc = TrainMva.plot_roc(
            arr_lab_ts,
            arr_all_ts,
            kind ='Test',
            ifold=-1)

        self._plot_probabilities(xval, yval, arr_all_ts, arr_lab_ts)
        self._save_roc_plot(ifold=-1)

        self._plot_scores(ifold=-1, sig_tst=arr_sig_ts, bkg_tst=arr_bkg_ts)
        self._save_roc_json(xval=xval, yval=yval, kind='Full', ifold=-1)

        return l_model
    # ---------------------------------------------
    def _save_roc_json(
            self,
            ifold : int,
            kind  : str,
            xval  : NPA,
            yval  : NPA) -> None:
        fold_str = 'all' if ifold == -1 else f'{ifold:03}'# -1 represents all the testing datasets combined
        val_dir  = self._cfg['saving']['output']

        name     = kind.lower()
        val_dir  = f'{val_dir}/fold_{fold_str}'
        os.makedirs(val_dir, exist_ok=True)
        jsn_path = f'{val_dir}/roc_{name}.json'

        df       = pnd.DataFrame({'x' : xval, 'y' : yval})
        df.to_json(jsn_path, indent=2)
    # ---------------------------------------------
    def _save_roc_plot(self, ifold : int) -> None:
        min_x    = 0
        min_y    = 0
        fold_str = 'all' if ifold == -1 else f'{ifold:03}'

        if 'min' in self._cfg['plotting']['roc']:
            [min_x, min_y] = self._cfg['plotting']['roc']['min']

        max_x = 1
        max_y = 1
        if 'max' in self._cfg['plotting']['roc']:
            [max_x, max_y] = self._cfg['plotting']['roc']['max']

        val_dir  = self._cfg['saving']['output']

        if ifold == 'all':
            plt_dir  = f'{val_dir}/fold_all'
        else:
            plt_dir  = f'{val_dir}/fold_{fold_str}'

        os.makedirs(plt_dir, exist_ok=True)

        plt.xlabel('Signal efficiency')
        plt.ylabel('Background rejection')
        plt.title(f'Fold: {ifold}')
        plt.xlim(min_x, max_x)
        plt.ylim(min_y, max_y)
        plt.grid()
        plt.legend()
        plt.savefig(f'{plt_dir}/roc.png')
        plt.close()
    # ---------------------------------------------
    def _load_trained_models(self) -> list[cls]:
        out_dir    = self._cfg['saving']['output']
        model_path = f'{out_dir}/model.pkl'
        nfold      = self._cfg['training']['nfold']
        failed     = False

        l_model    = []
        for ifold in range(nfold):
            fold_path = model_path.replace('.pkl', f'_{ifold:03}.pkl')

            if not os.path.isfile(fold_path):
                raise FileNotFoundError(f'Missing trained model: {fold_path}')

            log.debug(f'Loading model from: {fold_path}')
            try:
                model = joblib.load(fold_path)
            except ValueError:
                log.error(f'Cannot load {fold_path}')
                failed = True
                continue

            l_model.append(model)

        if failed:
            raise ValueError('Failed to load at least one model')

        return l_model
    # ---------------------------------------------
    def _labels_from_varnames(self, l_var_name : list[str]) -> list[str]:
        try:
            d_plot = self._cfg['plotting']['features']['plots']
        except KeyError as exc:
            raise KeyError('Cannot find plotting/features/plots section in config, using dataframe names') from exc

        l_label = []
        for var_name in l_var_name:
            if var_name not in d_plot:
                raise NoFeatureInfo(f'No plot found for feature {var_name}, cannot extract label')

            d_setting = d_plot[var_name]
            if 'labels' not in d_setting:
                raise NoFeatureInfo(f'No no labels present for plot of feature {var_name}, cannot extract label')

            [xlab, _ ]= d_setting['labels']

            l_label.append(xlab)

        return l_label
    # ---------------------------------------------
    def _save_feature_importance(self, model : cls, ifold : int) -> None:
        l_var_name           = self._df_ft.columns.tolist()

        d_data               = {}
        d_data['Variable'  ] = self._labels_from_varnames(l_var_name)
        d_data['Importance'] = 100 * model.feature_importances_

        val_dir  = self._cfg['saving']['output']
        val_dir  = f'{val_dir}/fold_{ifold:03}'
        os.makedirs(val_dir, exist_ok=True)

        df = pnd.DataFrame(d_data)
        df = df.sort_values(by='Importance', ascending=False)

        table_path = f'{val_dir}/importance.tex'
        d_form = {'Variable' : '{}', 'Importance' : '{:.1f}'}
        put.df_to_tex(df, table_path, d_format = d_form)
    # ---------------------------------------------
    def _get_scores(self, model : cls, arr_index : NPA, on_training_ok : bool) -> tuple[NPA, NPA, NPA, NPA]:
        '''
        Returns a tuple of four arrays

        arr_sig : Signal probabilities for signal
        arr_bkg : Signal probabilities for background
        arr_all : Signal probabilities for both
        arr_lab : Labels for both
        '''
        nentries = len(arr_index)
        log.debug(f'Getting {nentries} signal probabilities')

        df_ft    = self._df_ft.iloc[arr_index]
        arr_prob = model.predict_proba(df_ft, on_training_ok=on_training_ok)
        arr_lab  = self._l_lab[arr_index]

        l_all    = [ sig_prob for [_, sig_prob] in arr_prob ]
        arr_all  = numpy.array(l_all)

        arr_sig, arr_bkg= self._split_scores(arr_prob=arr_prob, arr_label=arr_lab)

        return arr_sig, arr_bkg, arr_all, arr_lab
    # ---------------------------------------------
    def _split_scores(self, arr_prob : NPA, arr_label : NPA) -> tuple[NPA, NPA]:
        '''
        Will split the testing scores (predictions) based on the training scores

        tst is a list of lists as [p_bkg, p_sig]
        '''

        l_sig = [ prb[1] for prb, lab in zip(arr_prob, arr_label, strict = True) if lab == 1]
        l_bkg = [ prb[1] for prb, lab in zip(arr_prob, arr_label, strict = True) if lab == 0]

        arr_sig = numpy.array(l_sig)
        arr_bkg = numpy.array(l_bkg)

        return arr_sig, arr_bkg
    # ---------------------------------------------
    def _save_model(self, model : cls, ifold : int) -> None:
        '''
        Saves a model, associated to a specific fold
        '''
        out_dir    = self._cfg['saving']['output']
        model_path = f'{out_dir}/model.pkl'

        if os.path.isfile(model_path):
            log.info(f'Model found in {model_path}, not saving')
            return

        dir_name = os.path.dirname(model_path)
        os.makedirs(dir_name, exist_ok=True)

        model_path = model_path.replace('.pkl', f'_{ifold:03}.pkl')

        log.info(f'Saving model to: {model_path}')
        joblib.dump(model, model_path)
    # ---------------------------------------------
    def _get_correlation_cfg(self, df : pnd.DataFrame, ifold : int) -> dict:
        l_var_name = df.columns.tolist()
        l_label    = self._labels_from_varnames(l_var_name)
        cfg = {
                'labels'     : l_label,
                'title'      : f'Fold {ifold}',
                'label_angle': 45,
                'upper'      : True,
                'zrange'     : [-1, +1],
                'size'       : [7, 7],
                'format'     : '{:.3f}',
                'fontsize'   : 12,
                }

        if 'correlation' not in self._cfg['plotting']:
            log.info('Using default correlation plotting configuration')
            return cfg

        log.debug('Updating correlation plotting configuration')
        custom = self._cfg['plotting']['correlation']
        cfg.update(custom)

        return cfg
    # ---------------------------------------------
    def _plot_correlations(self, arr_index : NPA, ifold : int) -> None:
        log.debug('Plotting correlations')

        df_ft = self._df_ft.iloc[arr_index]
        l_lab = self._l_lab[arr_index]

        arr_sig_idx, = numpy.where(l_lab == 1)
        arr_bkg_idx, = numpy.where(l_lab == 0)

        df_ft_sig = df_ft.iloc[arr_sig_idx]
        df_ft_bkg = df_ft.iloc[arr_bkg_idx]

        self._plot_correlation(df_ft=df_ft_sig, ifold=ifold, name='signal'    )
        self._plot_correlation(df_ft=df_ft_bkg, ifold=ifold, name='background')
    # ---------------------------------------------
    def _plot_correlation(
            self,
            df_ft : pnd.DataFrame,
            ifold : int,
            name  : str) -> None:

        log.debug(f'Plotting correlation for {name}/{ifold} fold')

        cfg = self._get_correlation_cfg(df_ft, ifold)
        cov = df_ft.corr()
        mat = cov.to_numpy()

        val_dir  = self._cfg['saving']['output']
        val_dir  = f'{val_dir}/fold_{ifold:03}'
        os.makedirs(val_dir, exist_ok=True)

        obj = MatrixPlotter(mat=mat, cfg=cfg)
        obj.plot()
        plt.savefig(f'{val_dir}/correlation_{name}.png')
        plt.close()
    # ---------------------------------------------
    def _get_nentries(self, arr_val : NPA) -> str:
        size = len(arr_val)
        size = size / 1000.

        return f'{size:.2f}K'
    # ---------------------------------------------
    def _plot_scores(
            self,
            ifold   : int,
            sig_tst : NPA,
            bkg_tst : NPA,
            sig_trn : NPA | None = None,
            bkg_trn : NPA | None = None) -> None:
        '''
        Will plot an array of scores, associated to a given fold
        '''
        fold_str = 'all' if ifold == -1 else f'{ifold:03}'
        log.debug(f'Plotting scores for {ifold} fold')

        val_dir  = self._cfg['saving']['output']
        val_dir  = f'{val_dir}/fold_{fold_str}'
        os.makedirs(val_dir, exist_ok=True)

        plt.hist(sig_tst, histtype='step', bins=50, range=(0,1), color='b', density=True, label='Signal Test: '     + self._get_nentries(sig_tst))
        plt.hist(bkg_tst, histtype='step', bins=50, range=(0,1), color='r', density=True, label='Background Test: ' + self._get_nentries(bkg_tst))

        if sig_trn is not None and bkg_trn is not None:
            plt.hist(sig_trn, alpha = 0.3, bins=50, range=(0,1), color='b', density=True, label='Signal Train: '    + self._get_nentries(sig_trn))
            plt.hist(bkg_trn, alpha = 0.3, bins=50, range=(0,1), color='r', density=True, label='Background Train: '+ self._get_nentries(bkg_trn))

        plt.legend()
        plt.title(f'Fold: {ifold}')
        plt.xlabel('Signal probability')
        plt.ylabel('Normalized')
        plt.savefig(f'{val_dir}/scores.png')
        plt.close()
    # ---------------------------------------------
    def _plot_probabilities(
            self,
            arr_seff: NPA,
            arr_brej: NPA,
            arr_sprb: NPA,
            arr_labl: NPA) -> None:

        roc_cfg = self._cfg['plotting']['roc']
        if 'annotate' not in roc_cfg:
            log.debug('Annotation section in the ROC curve config not found, skipping annotation')
            return

        l_sprb   = [ sprb for sprb, labl in zip(arr_sprb, arr_labl, strict = True) if labl == 1 ]
        arr_sprb = numpy.array(l_sprb)

        plt_cfg = roc_cfg['annotate']
        if 'sig_eff' not in plt_cfg:
            l_seff_target = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        else:
            l_seff_target = plt_cfg['sig_eff']
            del plt_cfg['sig_eff']

        arr_seff_target = numpy.array(l_seff_target)
        arr_quantile    = 1 - arr_seff_target

        l_score = numpy.quantile(arr_sprb, arr_quantile).tolist()
        l_seff  = []
        l_brej  = []

        log.debug(60 * '-')
        log.debug(f'{"SigEff":20}{"BkgRej":20}{"Score":20}')
        log.debug(60 * '-')
        for seff_target, score in zip(arr_seff_target, l_score, strict = True):
            arr_diff = numpy.abs(arr_seff - seff_target)
            ind      = numpy.argmin(arr_diff)

            seff     = arr_seff[ind]
            brej     = arr_brej[ind]

            log.debug(f'{seff:<20.3f}{brej:<20.3f}{score:<20.2f}')

            l_seff.append(seff)
            l_brej.append(brej)

        plu.annotate(l_x=l_seff, l_y=l_brej, l_v=l_score, **plt_cfg)
    # ---------------------------------------------
    def _plot_features(self):
        '''
        Will plot the features, based on the settings in the config
        '''
        out_dir         = self._cfg['saving']['output']
        d_cfg           = self._cfg['plotting']['features']
        d_cfg['saving'] = {'plt_dir' : f'{out_dir}/features'}

        ptr   = Plotter(d_rdf = {'Signal' : self._rdf_sig, 'Background' : self._rdf_bkg}, cfg=d_cfg)
        ptr.run()
    # ---------------------------------------------
    def _save_settings_to_tex(self) -> None:
        self._save_nan_conversion()
        self._save_hyperparameters_to_tex()
    # ---------------------------------------------
    def _save_nan_conversion(self) -> None:
        if 'dataset' not in self._cfg:
            return

        if 'nan' not in self._cfg['dataset']:
            log.debug('NaN section not found, not saving it')
            return

        d_nan = self._cfg['dataset']['nan']
        l_var = list(d_nan)
        l_lab = self._labels_from_varnames(l_var)
        l_val = list(d_nan.values())

        d_tex = {'Variable' : l_lab, 'Replacement' : l_val}
        df    = pnd.DataFrame(d_tex)
        val_dir  = self._cfg['saving']['output']
        os.makedirs(val_dir, exist_ok=True)
        put.df_to_tex(df, f'{val_dir}/nan_replacement.tex')
    # ---------------------------------------------
    def _save_hyperparameters_to_tex(self) -> None:
        if 'hyper' not in self._cfg['training']:
            raise ValueError('Cannot find hyper parameters in configuration')

        def format_value(val : Union[int,float]) -> str:
            if isinstance(val, float):
                return f'\\verb|{val:.3f}|'

            return f'\\verb|{val}|'

        d_hyper = self._cfg['training']['hyper']
        d_form  = { f'\\verb|{key}|' : format_value(val) for key, val in d_hyper.items() }
        d_latex = { 'Hyperparameter' : list(d_form.keys()), 'Value' : list(d_form.values())}

        df = pnd.DataFrame(d_latex)
        val_dir  = self._cfg['saving']['output']
        os.makedirs(val_dir, exist_ok=True)
        put.df_to_tex(df, f'{val_dir}/hyperparameters.tex')
    # ---------------------------------------------
    def _run_diagnostics(self, models : list[cls], rdf : RDF.RNode, name : str) -> None:
        log.info(f'Running diagnostics for sample {name}')
        if 'diagnostics' not in self._cfg:
            log.warning('Diagnostics section not found, not running diagnostics')
            return

        cfg_diag = self._cfg['diagnostics']
        out_dir  = cfg_diag['output']
        plt_dir  = None

        if 'overlay' in cfg_diag['correlations']['target']:
            plt_dir  = cfg_diag['correlations']['target']['overlay']['saving']['plt_dir']

        cfg_diag = copy.deepcopy(cfg_diag)
        cfg_diag['output'] = f'{out_dir}/{name}'
        if plt_dir is not None:
            cfg_diag['correlations']['target']['overlay']['saving']['plt_dir'] = f'{plt_dir}/{name}'

        cvd = CVDiagnostics(models=models, rdf=rdf, cfg=cfg_diag)
        cvd.run()
    # ---------------------------------------------
    # Hyperparameter optimization
    # ---------------------------------------------
    def _objective(self, trial, kfold : StratifiedKFold) -> float:
        ft = self._df_ft
        lab= self._l_lab

        if not issubclass(cls, GradientBoostingClassifier):
            raise NotImplementedError('Hyperparameter optimization only implemented for GradientBoostingClassifier')

        nft = len(ft.columns)

        var_learn_rate  = trial.suggest_float('learning_rate'  , 1e-3, 1e-1, log=True)
        var_max_depth   = trial.suggest_int('max_depth'        ,    2,   15)
        var_max_features= trial.suggest_int('max_features'     ,    2,  nft)
        var_min_split   = trial.suggest_int('min_samples_split',    2,   10)
        var_min_samples = trial.suggest_int('min_samples_leaf' ,    2,   30)
        var_nestimators = trial.suggest_int('n_estimators'     ,   50,  400)

        classifier = GradientBoostingClassifier(
            learning_rate     = var_learn_rate,
            max_depth         = var_max_depth,
            max_features      = var_max_features,
            min_samples_split = var_min_split,
            min_samples_leaf  = var_min_samples,
            n_estimators      = var_nestimators,
            random_state      = self._rdm_state)

        score = cross_val_score(
                classifier,
                ft,
                lab,
                n_jobs=1, # More than this will reach RLIMIT_NPROC in cluster
                cv=kfold)

        accuracy = score.mean()

        return accuracy
    # ---------------------------------------------
    def _optimize_hyperparameters(self, ntrial : int):
        log.info('Running hyperparameter optimization')

        self._pbar = tqdm.tqdm(total=ntrial, desc='Optimizing')
        kfold      = StratifiedKFold(n_splits=5, shuffle=True, random_state=self._rdm_state)
        objective  = partial(self._objective, kfold=kfold)

        pruner= optuna.pruners.MedianPruner(
            n_startup_trials = _OPTUNA_STARTUP_TRIALS, 
            n_warmup_steps   = _OPTUNA_WARMUP_STEPS)

        study = optuna.create_study(
            direction='maximize',
            pruner   = pruner)

        study.optimize(
            objective,
            callbacks = [self._update_progress],
            n_jobs    = self._nworkers,
            n_trials  = ntrial)

        self._print_hyper_opt(study=study)
        self._plot_hyper_opt(study=study)

        log.info('Overriding hyperparameters with optimized values')

        self._cfg['training']['hyper'] = study.best_params
    # ---------------------------------------------
    def _plot_hyper_opt(self, study) -> None:
        out_dir = self._cfg['saving']['output']
        opt_dir = f'{out_dir}/optimization'
        os.makedirs(opt_dir, exist_ok=True)

        trials_df = study.trials_dataframe()

        plt.plot(trials_df['number'], trials_df['value'])
        plt.xlabel('Trial')
        plt.ylabel('Accuracy')
        plt.title('Optimization History')
        plt.grid(True)
        plt.savefig(f'{opt_dir}/history.png')
        plt.close()

        plt.hist(trials_df['value'], bins=20, alpha=0.7)
        plt.xlabel('Accuracy')
        plt.ylabel('Frequency')
        plt.title('Distribution of Trial Results')
        plt.savefig(f'{opt_dir}/accuracy.png')
        plt.close()
    # ---------------------------------------------
    def _update_progress(self, study, _trial):
        if self._pbar is None:
            raise ValueError('No progress bar found')

        self._pbar.set_postfix({'Best': f'{study.best_value:.4f}' if study.best_value else 'N/A'})
        self._pbar.update(1)
    # ---------------------------------------------
    def _print_hyper_opt(self, study) -> None:
        log.info(40 * '-')
        log.info('Optimized hyperparameters:')
        log.info(40 * '-')
        for name, value in study.best_params.items():
            if isinstance(value, float):
                log.info(f'{name:<20}{value:.3f}')
            else:
                log.info(f'{name:<20}{value}')
    # ---------------------------------------------
    # ---------------------------------------------
    def _auc_from_json(self, ifold : int, kind : str) -> float:
        val_dir = self._cfg['saving']['output']
        path    = f'{val_dir}/fold_{ifold:03}/roc_{kind}.json'
        df      = pnd.read_json(path)

        return auc(df['x'], df['y'])
    # ---------------------------------------------
    def _check_overtraining(self) -> None:
        nfold      = self._cfg['training']['nfold']

        df         = pnd.DataFrame(columns=['fold'])
        df['fold' ]= numpy.linspace(0, nfold - 1, nfold, dtype=int)
        df['test' ]= df['fold'].apply(self._auc_from_json, args=('test' ,))
        df['train']= df['fold'].apply(self._auc_from_json, args=('train',))

        ax=None
        ax=df.plot(x='fold', y='test' , color='blue', label='Testing sample' , ax=ax)
        ax=df.plot(x='fold', y='train', color='red' , label='Training sample', ax=ax)
        ax.set_ylim(bottom=0.75, top=1.00)
        ax.set_ylabel('AUC')
        ax.set_xlabel('Fold')

        plt.grid()

        val_dir = self._cfg['saving']['output']
        path    = f'{val_dir}/fold_all/auc_vs_fold.png'
        plt.savefig(path)
        plt.close()
    # ---------------------------------------------
    def run(
        self,
        skip_fit     : bool = False,
        opt_ntrial   : int  =     0,
        load_trained : bool = False) -> float:
        '''
        Will do the training

        skip_fit    : By default false, if True, it will only do the plots of features and save tables
        opt_ntrial  : Number of optimization tries for hyperparameter optimization, by default zero, i.e. no optimization will run
        load_trained: If true, it will load the models instead of training, by default false.

        Returns
        ----------------
        Area under the ROC curve from evaluating the classifiers
        on samples that were not used in their training. Uses the full sample
        '''
        self._plot_features()

        if skip_fit:
            return self._auc

        if opt_ntrial > 0:
            self._optimize_hyperparameters(ntrial=opt_ntrial)

        self._save_settings_to_tex()
        l_mod = self._get_models(load_trained = load_trained)
        if not load_trained:
            for ifold, mod in enumerate(l_mod):
                self._save_model(mod, ifold)

        self._check_overtraining()
        self._run_diagnostics(models = l_mod, rdf = self._rdf_sig_org, name='Signal'    )
        self._run_diagnostics(models = l_mod, rdf = self._rdf_bkg_org, name='Background')

        return self._auc
    # ---------------------------------------------
    @contextmanager
    def use(self, nworkers : int):
        '''
        Context manager used to run with a specific configuration

        nworkers: Use this number of workers for ANY process that can be parallelized.
        '''
        old = self._nworkers

        log.info(f'Using {nworkers} workers to run training')

        self._nworkers = nworkers
        try:
            yield
        finally:
            self._nworkers = old
    # ---------------------------------------------
    @staticmethod
    def plot_roc_from_prob(
            arr_sig_prb : NPA,
            arr_bkg_prb : NPA,
            kind        : str,
            ifold       : int,
            color       : str|None = None) -> tuple[NPA,NPA, float]:
        '''
        Takes arrays of signal and background probabilities
        and plots ROC curve

        Parameters
        --------------------
        arr_bkg/sig_prb : Array with background/signal probabilities
        kind            : String used to label the plot
        ifold           : If no fold makes sense (i.e. this is the full sample), use ifold=-1
        kind            : Used to label the plot
        color           : String with color of curve

        Returns
        --------------------
        Tuple with 3 elements:

        - Array of x coordinates of ROC curve
        - Array of y coordinates of ROC curve
        - Area under the curve
        '''
        arr_sig_lab = numpy.ones_like( arr_sig_prb)
        arr_bkg_lab = numpy.zeros_like(arr_bkg_prb)

        arr_prb     = numpy.concatenate([arr_sig_prb, arr_bkg_prb])
        arr_lab     = numpy.concatenate([arr_sig_lab, arr_bkg_lab])

        res = TrainMva.plot_roc(
                l_lab=arr_lab,
                l_prb=arr_prb,
                color=color,
                kind =kind,
                ifold=ifold)

        return res
    # ---------------------------------------------
    @staticmethod
    def plot_roc(
            l_lab : NPA,
            l_prb : NPA,
            kind  : str,
            ifold : int,
            color : str|None = None) -> tuple[NPA, NPA, float]:
        '''
        Takes the labels and the probabilities and plots ROC
        curve for given fold

        Parameters
        --------------------
        ifold : If no fold makes sense (i.e. this is the full sample), use ifold=-1
        kind  : Used to label the plot

        Returns
        --------------------
        Tuple with 3 elements:

        - Array of x coordinates of ROC curve
        - Array of y coordinates of ROC curve
        - Area under the curve
        '''
        log.debug(f'Plotting ROC curve for {ifold} fold')

        xval, yval, _ = roc_curve(l_lab, l_prb)
        xval          = 1 - xval
        area          = auc(xval, yval)

        if color is None:
            color='red' if kind == 'Train' else 'blue'

        if ifold == -1:
            label=f'Test sample: {area:.3f}'
        else:
            label=f'{kind}: {area:.3f}'

        plt.plot(xval, yval, color=color, label=label)

        return xval, yval, area
# ---------------------------------------------
