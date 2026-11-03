import tempfile

from pathlib import Path

# ------------------------------------------------------
def get_tmp_path(
    directory : str,
    extension : str,
    prefix    : str | None = None) -> Path:
    '''
    Parameters
    ----------------
    dir       : directory name
    extension : E.g. `json`
    prefix    : Purpose of path, e.g. specification, optional

    Returns
    ----------------
    Path of the form:

    {tmp_dir}/dir/prefix_xxxx.{extension}

    where:
    - tmp_dir is chosen by the `tmpfile` module
    - {tmp_dir}/prefix is created
    - xxx.{extension} does not exist
    '''
    tmp_dir  = tempfile.gettempdir()
    dir_path = Path(f'{tmp_dir}/{directory}/')
    dir_path.mkdir(parents = True, exist_ok = True)

    ctx = tempfile.NamedTemporaryFile(
        delete = False,
        dir    = dir_path,
        prefix = prefix,
        suffix = f'.{extension}')

    with ctx as tmp:
        path = Path(tmp.name)
        path.unlink()

        return path
# ------------------------------------------------------
def get_tmp_dir(prefix : str) -> Path:
    '''
    Parameters
    ----------------
    prefix: Purpose of path, e.g. specification

    Returns
    ----------------
    Path of the form:

    {tmp_dir}/prefix/xxxx

    where:
    - tmp_dir is chosen by the `tmpfile` module
    - {tmp_dir}/prefix is created
    - xxx is a random value
    '''
    tmp_dir  = tempfile.gettempdir()
    dir_path = Path(f'{tmp_dir}/{prefix}')
    dir_path.mkdir(parents = True, exist_ok = True)

    string   = tempfile.mkdtemp(dir = dir_path)
    return Path(string)
# ------------------------------------------------------
