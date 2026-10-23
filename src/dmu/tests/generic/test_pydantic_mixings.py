'''
Module holding tests for mixings for pydantic models
'''
from pathlib       import Path
from pydantic      import BaseModel
from pytest        import MonkeyPatch
from dmu.generic   import Serializable
from typing        import Final

_DUMMY_VALUE : Final[int] = 42
_DUMMY_NAME  : Final[str] = 'test'
# -----------------------------------------------------------------------------
class DummyModel(BaseModel, Serializable):
    value: int
    name : str
# -----------------------------------------------------------------------------
def test_serializable_to_and_from_json(tmp_path : Path) -> None:
    '''
    Test serialization to and from JSON file
    '''
    json_path = tmp_path / 'test.json'
    model     = DummyModel(value = _DUMMY_VALUE, name = _DUMMY_NAME)

    model.to_json(path = json_path)
    assert json_path.exists()

    loaded_model = DummyModel.from_json(path = json_path)
    assert loaded_model.value == _DUMMY_VALUE
    assert loaded_model.name  == _DUMMY_NAME
# -----------------------------------------------------------------------------
def test_serializable_from_package(monkeypatch : MonkeyPatch) -> None:
    '''
    Test loading model from data package
    '''
    mock_data : dict[str,str | int] = {
        'value': _DUMMY_VALUE,
        'name' : _DUMMY_NAME
    }

    called : dict[str, str] = {}
    def mock_load_data(package : str, fpath : str) -> dict[str, int | str]:
        called['package'] = package
        called['fpath']   = fpath

        return mock_data

    monkeypatch.setattr('dmu.generic.pydantic_mixings.load_data', mock_load_data)

    model = DummyModel.from_package(package = 'dmu_data', loc = 'tests/generic/config.json')

    assert called['package'] == 'dmu_data'
    assert called['fpath']   == 'tests/generic/config.json'
    assert model.value       == _DUMMY_VALUE
    assert model.name        == _DUMMY_NAME
# -----------------------------------------------------------------------------

