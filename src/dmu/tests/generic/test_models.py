import yaml

from pytest_mock import MockerFixture
from pathlib     import Path
from dmu.generic import UnpackerModel

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
def test_unpackable(tmp_path : Path):
    '''
    Test that config with unpackable fields
    can be loaded
    '''
    simple_path = tmp_path / 'simple.yaml'

    obj = SimpleModel(frequency = 3)
    obj.to_yaml(path = simple_path)

    data = {'number' : 1, 'model' : str(simple_path)}
    text = yaml.safe_dump(data = data, indent = 2)

    composite_path = tmp_path / 'composite.yaml'
    composite_path.write_text(data = text)

    cmp = CompositeModel.from_yaml(path = composite_path)

    assert cmp.number == 1
    assert cmp.model  == obj 
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
