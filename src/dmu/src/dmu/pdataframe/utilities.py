'''
Module containing utilities for pandas dataframes
'''
import os
import yaml
import pandas as pnd

from colorama              import Style
from pathlib               import Path
from dmu.logging.log_store import LogStore
from dmu.generic           import typing_utilities   as tut

log=LogStore.add_logger('dmu:pdataframe:utilities')
# -------------------------------------
def query(
    *,
    df          : pnd.DataFrame,
    expr        : str,
    allow_empty : bool = False) -> pnd.DataFrame:
    '''
    Parameters
    -------------------
    df         : Dataframe
    expr       : Selection applied to dataframe
    allow_empty: If resulting dataframe is empty, will raise and show diagnostics

    Returns
    -------------------
    Dataframe after filtering
    '''
    df_new = df.query(expr)
    if not df_new.empty:
        return df_new

    log.error(f'Expression: {expr}')
    log.error(f'Original:\n{df}')
    log.error(f'Filtered:\n{df_new}')
    log.error(f'{df.dtypes}')

    raise ValueError('Empty dataframe found')
# -------------------------------------
def df_to_tex(
    df         : pnd.DataFrame,
    path       : str | Path,
    hide_index : bool                 = True,
    d_format   : dict[str,str] | None = None,
    **kwargs) -> None:
    '''
    Saves pandas dataframe to latex

    Parameters
    -------------
    df              : Dataframe with data
    path     (str)  : Path to latex file
    hide_index      : If true (default), index of dataframe won't appear in table
    d_format (dict) : Dictionary specifying the formattinng of the table, e.g. `{'col1': '{}', 'col2': '{:.3f}', 'col3' : '{:.3f}'}`
    kwargs          : Arguments needed in `to_latex`
    '''
    if path is not None:
        dir_name = os.path.dirname(path)
        os.makedirs(dir_name, exist_ok=True)

    st = df.style
    if hide_index:
        st=st.hide(axis='index')

    if d_format is not None:
        st=st.format(formatter=d_format)

    log.info(f'Saving to: {path}')
    buf = st.to_latex(
        buf            = path,
        hrules         = True,
        **kwargs)

    return buf
# -------------------------------------
def to_yaml(df : pnd.DataFrame, path : Path):
    '''
    Takes a dataframe and the path to a yaml file
    Makes the directory path if not found and saves data in YAML file
    '''
    path.parent.mkdir(parents=True, exist_ok=True)
    data = df.to_dict()

    with open(path, 'w', encoding='utf-8') as ofile:
        yaml.dump(data, ofile, Dumper=yaml.CDumper)
# ----------------------
def to_markdown(df : pnd.DataFrame, path : Path) -> None:
    '''
    Parameters
    -------------
    df  : Pandas dataframe
    path: Path to markdown file
    '''
    path.parent.mkdir(parents=True, exist_ok=True)
    text = df.to_markdown()
    with open(path, 'w', encoding='utf-8') as ofile:
        ofile.write(text)
# -------------------------------------
def from_yaml(path : Path) -> pnd.DataFrame:
    '''
    Takes path to a yaml file
    Makes dataframe from it and returns it
    '''
    with open(path, encoding='utf-8') as ifile:
        data = yaml.load(ifile, Loader=yaml.CSafeLoader)

    df = pnd.DataFrame(data)

    return df
# -------------------------------------
def dropna(df : pnd.DataFrame, max_frac : float = 0.02) -> pnd.DataFrame:
    '''
    Parameters
    ----------------
    df      : Pandas dataframe potentially with NaNs
    max_frac: Maximum fraction of the data that can be dropped, will raise exception beyond
    '''

    ini = len(df)
    df  = df.dropna()
    fin = len(df)

    if ini == fin:
        log.debug('No NaNs were found')
        return df

    # If fewer elements survive the filter, raise
    if fin < ini * (1 - max_frac):
        raise ValueError(f'Too man NaNs were detected: {ini} --> {fin}')

    log.info(f'Found NaNs: {ini} --> {fin}')

    return df
# -------------------------------------
def colorize_row(
    row    : pnd.Series,
    colors : dict[int, str]) -> pnd.Series:
    '''
    To pick color strings use:

    ```python
    from colorama import Fore

    Fore.RED
    Fore.LIGHTYELLOW_EX
    ```

    Parameters
    -------------
    df    : DataFrame to colorize
    colors: Dictionary where
            key  : Is an integer
            Value: String symbolizing color

    Returns
    -------------
    Dataframe with colors added
    '''

    for col in row.index:
        val : int = tut.numeric_from_series(row, col, int)

        if val not in colors:
            continue

        color = colors[val]

        row[col] = f'{color}{val}{Style.RESET_ALL}'

    return row
# -------------------------------------
