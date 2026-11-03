'''
Module with tests for functions in generic/utilities.py
'''
import os
import sys
import pytest

from time        import sleep
from pathlib     import Path
from typing      import Any
from omegaconf   import DictConfig, OmegaConf
from dmu         import LogStore
from dmu.generic import utilities as gut

log=LogStore.add_logger('dmu:test_generic_utilities')
# ----------------------
def test_environment_context():
    '''
    This function tests the environment context manager
    '''
    with gut.environment(mapping = {}):
        pass

    with gut.environment(mapping = {'VAR' : '1234'}):
        assert os.environ['VAR'] == '1234'

    with gut.environment(mapping = {'VAR' : '1234', 'VOR' : 'abcd'}):
        assert os.environ['VAR'] == '1234'
        assert os.environ['VOR'] == 'abcd'

    with pytest.raises(KeyError):
        os.environ['VAR']
# ----------------------
@pytest.fixture
def no_schema_pkg(tmp_path : Path):
    '''
    This fixture creates a fake package missing the schema
    validating data package
    '''
    pkg_dir = tmp_path / 'fake_data'
    pkg_dir.mkdir()
    (pkg_dir / '__init__.py').write_text('')
    (pkg_dir / 'config.yaml').write_text('dummy: data')

    sys.path.insert(0, str(tmp_path))
    try:
        yield pkg_dir
    finally:
        try:
            sys.path.remove(str(tmp_path))
        except ValueError:
            pass
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('dmu:generic:utilities'     , 10)
    LogStore.set_level('dmu:test_generic_utilities', 10)
# ----------------------
def _check_data(path : Path, data : list[str]) -> None:
    '''
    Parameters
    -------------
    path: Path where data was dumped
    data: List of lines dumped
    '''
    if not path.exists():
        raise FileNotFoundError(f'Cannot find: {path}')

    with open(path) as ifile:
        tmp   = ifile.readlines()
        lines = [ line.strip() for line in tmp ]

    assert lines == data
# -------------------------
def test_timeit():
    '''
    Will test timer
    '''
    gut.TIMER_ON=True
    @gut.timeit
    def fun():
        sleep(3)

    fun()
# -------------------------
@pytest.mark.parametrize('ext', ['json', 'yaml'])
def test_dump_json(ext : str, tmp_path : Path):
    '''
    Tests dump_json
    '''
    this_path = tmp_path/'dump_json'
    this_path.mkdir(parents=True, exist_ok=True)

    l_data = [1,2,3,4]
    d_data = {
        1           : 'a',
        'b'         : 2,
        'some_path' : this_path}

    gut.dump_json(l_data, this_path/f'list.{ext}')
    gut.dump_json(d_data, this_path/f'dict.{ext}')

    oc_l_data = OmegaConf.create(l_data)
    oc_d_data = OmegaConf.create(d_data)

    gut.dump_json(oc_l_data, this_path/f'oc_list.{ext}')
    gut.dump_json(oc_d_data, this_path/f'od_dict.{ext}')

    with pytest.raises(FileExistsError):
        gut.dump_json(oc_l_data, this_path/f'oc_list.{ext}')

    gut.dump_json(oc_l_data, this_path/f'oc_list.{ext}', exists_ok=True)
# -------------------------
def test_dump_text(tmp_path : Path):
    '''
    Tests dump_text
    '''
    this_path = tmp_path / 'dump_text'
    this_path.mkdir(parents=True, exist_ok=True)

    list_str = ['1', '2', '3']
    list_cfg = OmegaConf.create(list_str)

    gut.dump_text(lines=list_str, path=this_path / 'list_str.txt')
    gut.dump_text(lines=list_cfg, path=this_path / 'list_cfg.txt')

    _check_data(path=this_path / 'list_str.txt', data=list_str)
    _check_data(path=this_path / 'list_cfg.txt', data=list_str)
# -------------------------
@pytest.mark.parametrize('ext', ['json', 'yaml'])
def test_load_json(ext : str, tmp_path : Path):
    '''
    Tests load_json
    '''
    json_dir = tmp_path/'load_json'
    json_dir.mkdir(parents=True, exist_ok=True)
    log.debug(f'Using path: {json_dir}')
    json_path= json_dir/f'list.{ext}'

    l_data_org = [1,2,3,4]
    gut.dump_json(l_data_org, json_path)

    l_data_lod = gut.load_json(json_path)

    assert l_data_org == l_data_lod
# -------------------------
def test_dump_pickle():
    '''
    Tests dump_json and loading it
    '''
    path = '/tmp/tests/dmu/generic/list.pkl'
    data = [1,2,3,4]
    gut.dump_pickle(data=data, path=path)

    loaded = gut.load_pickle(path=path)

    assert data == loaded
# -------------------------
def test_silent_import():
    '''
    Tests decorator in charge of suppressing
    messages from imported modules
    '''
    with gut.silent_import():
        import tensorflow

    _ : str = tensorflow.version.VERSION
# -------------------------
@pytest.mark.parametrize('ext', ['yaml', 'json', 'yaml.j2'])
def test_load_data(ext : str):
    '''
    Tests loading file from data package
    '''
    expected = {
            "key" : [
                "value1",
                "value2",
                "value3"]
            }

    data = gut.load_data(
        package='dmu_data',
        fpath  =f'tests/generic/config.{ext}')

    assert data == expected
# -------------------------
def test_load_conf_schema_validation_no_package(no_schema_pkg : Any):
    '''
    Tests that the validation fails when no schema data package is found
    '''
    _ = no_schema_pkg

    cfg = gut.load_conf(
        package='fake_data',
        fpath  ='config.yaml')

    assert cfg == {'dummy' : 'data'}

    with pytest.raises(FileNotFoundError),\
        gut.enforce_schema_validation(value=True):
        cfg = gut.load_conf(
            package='fake_data',
            fpath  ='missing_config.yaml')
# -------------------------
def test_load_conf_schema_validation_no_file():
    '''
    Tests that the validation fails when no schema was found
    '''
    with pytest.raises(FileNotFoundError),\
        gut.enforce_schema_validation(value=True):
        cfg = gut.load_conf(
            package='dmu_data',
            fpath  ='tests/generic/config.yaml')

        assert isinstance(cfg, DictConfig)

        assert cfg.key == ['value1', 'value2', 'value3']
# -------------------------
def test_load_conf_schema_validation():
    '''
    Tests that the validation passes
    '''
    with gut.enforce_schema_validation(value=True):
        cfg = gut.load_conf(
            package='dmu_data',
            fpath  ='tests/generic/validate.yaml')

        assert isinstance(cfg, DictConfig)

        assert cfg.key == ['value1', 'value2', 'value3']
# -------------------------
def test_load_conf_schema_validation_fail():
    '''
    Tests that the validation fails
    '''
    with pytest.raises(RuntimeError),\
         gut.enforce_schema_validation(value=True):
        cfg = gut.load_conf(
            package='dmu_data',
            fpath  ='tests/generic/fail_validate.yaml')

        assert isinstance(cfg, DictConfig)

        assert cfg.key == ['value1', 'value2', 'value3']
# -------------------------
@pytest.mark.parametrize('ext', ['yaml', 'json'])
def test_load_conf_format(ext : str):
    '''
    Tests loading configuration from different formats
    '''
    cfg = gut.load_conf(
        package='dmu_data',
        fpath  =f'tests/generic/config.{ext}')

    assert isinstance(cfg, DictConfig)

    assert cfg.key == ['value1', 'value2', 'value3']
# ----------------------
def test_load_conf_reference() -> None:
    '''
    Tests loading of config when fields are paths to sub-configs
    '''
    log.info('')
    name = 'with_references.yaml'

    cfg = gut.load_conf(
        package='dmu_data',
        fpath  =f'tests/generic/{name}')

    assert cfg.config_1.key         == [ 1,   2,   3 ]
    assert cfg.section.config_2.key == ['a', 'b', 'c']

    log.debug(OmegaConf.to_yaml(cfg))
# -------------------------
@pytest.mark.parametrize('ext', ['yaml', 'json'])
def test_load_from_wcard(ext : str):
    '''
    Tests loading configs from path with wildcard
    '''
    l_cfg = gut.load_from_wcard(
        package='dmu_data',
        fwcard =f'tests/generic/load/*.{ext}')

    assert l_cfg[0] == {'a' : 1, 'b' : 2}
    assert l_cfg[1] == {'a' : ['1', '2', '3'], 'b' : [1,2,3]}
# -------------------------
def test_object_to_string():
    '''
    Tests object_to_string
    '''
    assert gut.object_to_string(obj=[1,2,3]) == '[1, 2, 3]'
    assert gut.object_to_string(obj={1,2,3}) == '{"__set__": [1, 2, 3]}'

    data = OmegaConf.create(obj={'a' : 1, 'b' : 2})
    assert gut.object_to_string(obj=data) == '{"a": 1, "b": 2}'

    path = Path('/a/b/c')
    val  = gut.object_to_string(obj=[path])
    assert val == '["/a/b/c"]'

    path = Path('/a/b/c')
    val  = gut.object_to_string(obj={path})
    assert val == '{"__set__": ["/a/b/c"]}'

    with pytest.raises(ValueError):
        gut.object_to_string(obj='name')
# -------------------------
