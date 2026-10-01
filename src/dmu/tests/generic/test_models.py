import yaml

from typing      import Final
from pytest_mock import MockerFixture
from pathlib     import Path
from dmu.generic import UnpackerModel

_ALT_FREQ : Final[int] = 1
_DEF_FREQ : Final[int] = 3
# -----------------------------------
class SimpleModel(UnpackerModel):
    frequency : int
# -----------------------------------
class CompositeModel(UnpackerModel):
    '''
    Basic model using unpacker base class
    '''
    number : int
    model  : SimpleModel
# -----------------------------------
class DictModel(UnpackerModel):
    '''
    Basic model using unpacker base class
    '''
    number : int
    models : dict[str,SimpleModel]
# -----------------------------------
def _get_simple_model(
    frequency : int,
    path      : Path) -> Path:

    obj = SimpleModel(frequency = frequency)
    obj.to_yaml(path = path)

    return path
# -----------------------------------
def _get_composite_model(proj_dir : Path, freq : int) -> Path:
    simple_path = _get_simple_model(
        frequency = freq,
        path      = proj_dir / 'simple.yaml')

    data = {'number' : 1, 'model' : str(simple_path)}
    text = yaml.safe_dump(data = data, indent = 2)

    composite_path = proj_dir / 'composite.yaml'
    composite_path.write_text(data = text)

    return composite_path
# -----------------------------------
def test_unpackable(tmp_path : Path):
    '''
    Test that config with unpackable fields
    can be loaded
    '''
    simple_path   = _get_simple_model(
        frequency = _DEF_FREQ,
        path      = tmp_path / 'simple.yaml')

    data = {'number' : 1, 'model' : str(simple_path)}
    text = yaml.safe_dump(data = data, indent = 2)

    composite_path = tmp_path / 'composite.yaml'
    composite_path.write_text(data = text)

    cmp = CompositeModel.from_yaml(path = composite_path)

    assert cmp.number == 1
    assert cmp.model  == SimpleModel.from_yaml(path = simple_path)
# -----------------------------------
def test_with_package(mocker : MockerFixture, tmp_path : Path):
    simple_path = tmp_path / 'simple.yaml'

    obj = SimpleModel(frequency = 3)
    obj.to_yaml(path = simple_path)

    data = {'number' : 1, 'model' : simple_path.name}
    text = yaml.safe_dump(data = data, indent = 2)

    composite_path = tmp_path / 'composite.yaml'
    composite_path.write_text(data = text)

    mock_files = mocker.patch('dmu.generic.models.files')
    mock_files.return_value = tmp_path

    cmp = CompositeModel.from_yaml(
        package = 'data_package',
        path    = 'composite.yaml')

    assert cmp.number == 1
    assert cmp.model  == obj
# -----------------------------------
def test_dict_model(tmp_path : Path):
    simple_path = tmp_path / 'simple_models.yaml'

    data = {}
    for val in ['a', 'b', 'c']:
        data[val] = {'frequency' : 2}

    string = yaml.safe_dump({'models' : data, 'number' : 1})
    simple_path.write_text(string)

    DictModel.from_yaml(path = simple_path)
# -----------------------------------
def test_suffix_switch(tmp_path : Path):
    '''
    Test that config with unpackable fields
    can be loaded
    '''
    proj_dir = tmp_path / 'test_project'
    proj_dir.mkdir(exist_ok = True, parents = True)

    _get_simple_model(
        frequency = _ALT_FREQ,
        path      = proj_dir / 'simple_alt.yaml')

    path= _get_composite_model(proj_dir = proj_dir, freq = _DEF_FREQ)
    cmp = CompositeModel.from_yaml(path = path)

    assert cmp.model.frequency == _DEF_FREQ

    files = {'test_project/simple.yaml' : 'test_project/simple_alt.yaml'}
    with UnpackerModel.replacements(files = files):
        cmp = CompositeModel.from_yaml(path = path)
        assert cmp.model.frequency == _ALT_FREQ
# -----------------------------------
