import pandas as pnd

from pydantic import BaseModel
from pathlib  import Path
from ROOT     import RDF # type: ignore

from dmu.logging.log_store import LogStore

log=LogStore.add_logger('dmu:tests:rdf_with_friend')
# ----------------------------------
class Sample(BaseModel):
    trees : list[str ] = []
    files : list[Path] = []

class Spec(BaseModel):
    samples : dict[str, Sample] = {}
    friends : dict[str, Sample] = {}
# ----------------------------------
def _make_files(df : pnd.DataFrame, branch : str) -> tuple[Path, Path]:
    df_1 = df.drop(columns=branch)
    df_2 = df[[branch]]

    path_main  = _make_file(df=df_1, name='main'  )
    path_friend= _make_file(df=df_2, name='friend')

    return path_main, path_friend
# ----------------------------------
def _make_file(df : pnd.DataFrame, name : str) -> Path:
    path = Path(f'/tmp/{name}.root')
    path.parent.mkdir(parents=True, exist_ok=True)

    rdf = RDF.FromPandas(df)
    rdf.Snapshot(treename='tree', filename=str(path))

    return path
# ----------------------------------
def _get_json_path(main : Path, friend : Path) -> Path:
    spc = Spec()
    spc.samples['main'] = Sample(trees = ['tree'], files = [main  ])
    spc.friends['f']    = Sample(trees = ['tree'], files = [friend])

    json_path= Path('/tmp/spec.json')
    with open(json_path, 'w', encoding='utf-8') as ofile:
        data = spc.json()
        ofile.write(data)

    return json_path
# ----------------------------------
def rdf_with_friend(df : pnd.DataFrame, branch : str) -> RDF.RNode:
    '''
    Parameters
    --------------
    df    : Pandas dataframe with e.g. a, b, c columns
    branch: One of the columns in dataframe meant to be transformed into a friend tree
            type of column, e.g. c -> f.c

    Returns
    --------------
    ROOT dataframe with a, b, c, f.c
    '''
    log.debug(f'Returning dataframe with friend tree for branch {branch}')

    path_main, path_friend = _make_files(df=df, branch=branch)
    json_path  = _get_json_path(main=path_main, friend=path_friend)

    rdf = RDF.Experimental.FromSpec(str(json_path))

    log.info(30 * '-')
    log.info('Using the following columns:')
    log.info(30 * '-')
    for name in rdf.GetColumnNames():
        log.info(name)

    return rdf
# ----------------------------------
