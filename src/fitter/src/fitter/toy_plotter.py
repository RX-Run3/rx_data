# pyrefly: ignore-errors[unknown-variable-type, unknown-argument-type]
'''
Module holding ToyPlotter class
'''
import os
import copy
import numpy
import omegaconf
import pandas            as pnd
import seaborn           as sns
import matplotlib.pyplot as plt

from dmu          import LogStore
from typing       import Final, Any
from pathlib      import Path
from scipy.stats  import norm
from ROOT         import RDF
from omegaconf    import DictConfig, OmegaConf
from dmu.plotting import Plotter1D

log=LogStore.add_logger('fitter:toy_plotter')
_TOY_INDEX : Final[str] = 'Toy' # Name of column identifying different fits

# TODO: Remove omegaconf and use pydantic for proper typing
# ----------------------
class MissingVariableConfiguration(Exception):
    '''
    This exception will be risen if a variable is needed that
    does not have a configuration associated
    '''
    def __init__(self, message : str) -> None:
        super().__init__(message)
        self.message = message
# ----------------------
class ToyPlotter:
    '''
    Class in charge of:

    - Picking up pandas dataframe with fit results
    - Plotting
        - Pulls
        - Distributions of variables
        - Errors of fitted variables
        - Correlation matrix
    '''
    # ----------------------
    def __init__(self, df : pnd.DataFrame, cfg : DictConfig):
        '''
        Parameters
        -------------
        cfg    : Configuration specifying how to plot
        df     : Pandas dataframe with information from toy fits
        Columns:

        Parameter, Value, Error, Gen, Toy, GOF, Valid
        '''
        self._validate_input(df = df)

        # WARNING: Update this when a new toy-wise quantity added
        # These columns have the same values for all the fitting parameters
        # belonging to a given fit
        self._toywise_columns = ['GOF', 'Valid', 'Hash']

        self._l_par = df['Parameter'].unique().tolist()
        self._df    = self._preprocess_df(df=df)
        self._d_tex = self._get_latex_names(cfg=cfg)
        self._d_gen = self._get_gen_values(df=df)

        cfg = self._add_pull_config(cfg=cfg)
        cfg = self._add_gen_config(cfg=cfg)

        self._ana_dir      = Path(os.environ['ANADIR'])
        cfg.saving.plt_dir = self._ana_dir / cfg.saving.plt_dir
        self._cfg   = cfg
    # ----------------------
    def _validate_input(self, df : pnd.DataFrame) -> None:
        '''
        Parameters
        -------------
        df : DataFrame with fitting parameters
        '''
        if len(df) == 0:
            raise ValueError('Empty dataframe')

        for _, df_par in df.groupby('Parameter'):
            if df_par['Toy'].duplicated().any():
                raise ValueError('DataFrame has duplicated values in Toy column')
    # ----------------------
    def _get_latex_names(
        self,
        cfg: DictConfig) -> dict[str,str]:
        '''
        Parameters
        -------------
        cfg: Dictionary with configuration

        Returns
        -------------
        Dictionary mapping parameter names with their latex version
        '''
        d_latex    = {}
        for par_name in self._l_par:
            try:
                latex_name = cfg.plots[f'{par_name}_val'].labels[0]
            except omegaconf.errors.ConfigKeyError as exc:
                self._print_params()
                raise MissingVariableConfiguration(f'Failed to find configuration for {par_name}') from exc

            d_latex[par_name] = latex_name

        return d_latex
    # ----------------------
    def _get_gen_values(self, df : pnd.DataFrame) -> dict[str,float]:
        '''
        Parameters
        -------------
        df: DataFrame with parameter information

        Returns
        -------------
        Dictionary mapping parameter name to generated value (used to make toys)
        '''
        fail = False
        d_gen= {}

        for key, df_par in df.groupby('Parameter'):
            par_name = str(key)
            gen_vals = df_par['Gen'].unique().tolist()
            ngen     = len(gen_vals)

            if ngen != 1:
                fail = True
                for val in gen_vals:
                    log.info(f'{val:.4e}')
                log.error(f'Found {ngen} Gen values for: {par_name}')
                log.info(df_par['Gen'].value_counts())
                log.info(20 * '-')
                continue

            gen_val : float = gen_vals[0]
            d_gen[par_name] = gen_val

        if fail:
            raise ValueError('Multiple generating values')

        return d_gen
    # ----------------------
    def _add_gen_config(self, cfg : DictConfig) -> DictConfig:
        '''
        Parameters
        -------------
        cfg : Config file pased to initializer

        Returns
        -------------
        Config file with `vline` sections added to `_val` plots
        and with the generation value
        '''
        cfg_gen = cfg.generated

        for par_name in self._d_tex:
            cfg_gen_par          = copy.deepcopy(cfg_gen)
            cfg_gen_par.x        = self._d_gen[par_name]
            cfg_gen_par['label'] = f'{cfg_gen_par.label}={cfg_gen_par.x:.2f}'

            cfg.plots[f'{par_name}_val']['vline'] = cfg_gen_par

        return cfg
    # ----------------------
    def _add_pull_config(self, cfg : DictConfig) -> DictConfig:
        '''
        Parameters
        -------------
        cfg : Plotting configuration dictionary

        Returns
        -------------
        Same dictionary as input with the configuration for the pull plots
        added to the `plots` field.
        '''
        for par_name, latex_name in self._d_tex.items():
            cfg_pul = cfg.pulls
            xlabel  = cfg_pul.labels[0]
            xlabel  = xlabel.replace('VAR', latex_name)

            cfg_pul = copy.deepcopy(cfg_pul)
            cfg_pul.labels[0] = xlabel

            cfg.plots[f'{par_name}_pul'] = cfg_pul

        return cfg
    # ----------------------
    def _preprocess_df(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df: Pandas dataframe with rows as parameters and columns as fit information

        Returns
        -------------
        Dataframe with columns corresponding to parameters, e.g:

        a_val  a_err  a_gen  ...

        each row corresponds to a fit
        '''
        df   = df.sort_values(by = 'Parameter').reset_index(drop = True)
        l_df = []
        for key, df_par in df.groupby('Parameter'):
            name   = str(key)
            df_ref = self._reformat_df(df=df_par, name=name)
            df_ref = df_ref.set_index(_TOY_INDEX, drop=True)
            l_df.append(df_ref)

        # Extract toy-wise columns from any of the dataframes
        d_toy_col : dict[str,pnd.Series] = {}
        for column in self._toywise_columns:
            df                = l_df[-1]
            d_toy_col[column] = df[column]

        # Remove toy-wise columns from all dataframes
        l_df_strip : list[pnd.DataFrame] = [
            df.drop(columns=self._toywise_columns) for df in l_df ]

        # Concatenate horizontally
        df = pnd.concat(
            objs         = l_df_strip,
            axis         = 1,
            ignore_index = False)

        # Add back toy wise columns, once
        for name, series in d_toy_col.items():
            df[name] = series

        return df
    # ----------------------
    def _get_rdf(self) -> RDF.RNode:
        '''
        Returns
        -------------
        ROOT dataframe meant to be passed to Plotter1d
        '''
        data : dict[str,numpy.ndarray] = {}
        for name in self._df.columns:
            values = self._df[name]
            try:
                array  : numpy.ndarray = numpy.asarray(values, dtype=float)
            except Exception as exc:
                raise ValueError(f'Cannot convert column \"{name}\" into array of floats') from exc

            log.debug(f'Column {name}, shape {array.shape}')
            data[name] = array

        rdf = RDF.FromNumpy(data)

        return rdf
    # ----------------------
    def _reformat_df(
        self,
        df   : pnd.DataFrame,
        name : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df  : Pandas dataframe with quanities (Value, Error, ...) as columns and parameters in rows
        name: Name of parameter associated to this dataframe

        Returns
        -------------
        - Add pull and uncertainty columns
        - Rename columns using {name}_xxx
        '''
        df['Pull'] = (df['Value'] - df['Gen']) / df['Error']
        df['Unc' ] = 100 * df['Error'] / df['Value'].abs()

        d_name     = {
            'Gen'   : f'{name}_gen',
            'Pull'  : f'{name}_pul',
            'Unc'   : f'{name}_unc',
            'Value' : f'{name}_val',
            'Error' : f'{name}_err'}

        df = df.rename(columns=d_name)
        # No need of name, it is in the other columns already
        df = df.drop(columns='Parameter')

        return df
    # ----------------------
    def _print_params(self):
        '''
        Prints columns available in input dataframe
        '''
        l_parameter = sorted(self._l_par)

        log.info('Parameters found:')
        for name in l_parameter:
            log.info(name)
    # ----------------------
    def _plot_correlation_matrix(
        self,
        rdf      : RDF.RNode,
        plt_path : Path) -> None:
        '''
        - Formats the config for the correlation matrix plotting
        - Calculates correlation matrix from input data
        - Plots the correlations through MatrixPlotter

        Parameters
        -----------------
        rdf     : ROOT dataframe
        plt_path: Path to output plot
        '''
        cfg_cor = self._cfg.correlation
        cfg_cor = copy.deepcopy(cfg_cor)
        xrot    = cfg_cor.rotation.x
        size    = cfg_cor.size
        title   = cfg_cor.title
        del cfg_cor['size']
        del cfg_cor['title']
        del cfg_cor['rotation']

        d_tex = { f'{key}_val' : val for key, val in self._d_tex.items() }
        data  = rdf.AsNumpy(list(d_tex))
        df    = pnd.DataFrame(data)
        df    = df.rename(columns=d_tex)
        corr  = df.corr()
        mask  = numpy.triu(numpy.ones_like(corr, dtype=bool), k=1)

        plt.figure(figsize=size)
        sns.heatmap(corr, mask=mask, **cfg_cor)
        plt.title(title)
        plt.xticks(rotation=xrot)
        plt.savefig(plt_path)
        plt.close()
    # ----------------------
    def _get_toys_summary(self) -> DictConfig:
        '''
        Returns
        -------------
        Dictionary with key-value pairs summarizing fits
        '''
        log.debug('Getting toys summary')

        cfg     = self._cfg.summary
        summary : dict[str, Any] = {}

        for col_name in cfg.median:
            val=self._df[col_name].median()
            summary[f'median_{col_name}'] = float(val)

        for col_name in cfg.mean:
            val=self._df[col_name].mean()
            summary[f'mean_{col_name}'] = float(val)

        for col_name in cfg.pulls:
            d_par = self._get_pull_fit_pars(name=col_name)
            summary[col_name] = d_par

        return OmegaConf.create(summary)
    # ----------------------
    def _get_pull_fit_pars(self, name : str) -> dict[str,float]:
        '''
        Parameters
        -------------
        name: Name of column with pulls, e.g. a_pull

        Returns
        -------------
        Dictionary with keys as parameter names and values as fitted values
        '''
        log.debug(f'Getting pull parameters for {name}')

        df = self._df
        df = df[(df[name] > -4) & (df[name] < +4)]
        arr= df[name].to_numpy()

        mu, sg = norm.fit(arr)

        return {'mu' : float(mu), 'sg' : float(sg)}
    # ----------------------
    def plot(self) -> DictConfig:
        '''
        Returns
        -------------
        Dictionary with summary information for current toy
        '''
        rdf = self._get_rdf()

        try:
            ptr = Plotter1D(d_rdf={'Toys' : rdf}, cfg=self._cfg)
            ptr.run()
        except ValueError as exc:
            self._print_params()
            raise MissingVariableConfiguration('Cannot plot variable, one of the variables was likely missing') from exc

        plt_path = Path(f'{self._cfg.saving.plt_dir}/correlations.png')
        plt_path.parent.mkdir(parents = True, exist_ok = True)

        self._plot_correlation_matrix(rdf=rdf, plt_path=plt_path)
        cfg_sum = self._get_toys_summary()

        return cfg_sum
# ----------------------
