'''
Tests for Measurement class
'''
import pytest
from pydantic  import ValidationError
from dmu.stats import Measurement

# ------------------------------------
def test_simple():
    data = {'a' : (1., 1.), 'b' : (2., 1.)}

    ms = Measurement(data=data)
    assert ms['a'] == (1., 1.)

    with pytest.raises(ValidationError):
        ms.data = {}

    assert 'a'     in ms
    assert 'x' not in ms
# ------------------------------------
def test_get_values():
    '''
    Tests get_values method
    '''
    data = {'a_par' : (1., 1.), 'b_par' : (2., 1.), 'b_par_x' : (2., 3.)}

    ms = Measurement(data=data)
    assert ms.get_values(prefix = 'a_par') == (1., 1.)

    with pytest.raises(ValueError):
        ms.get_values(prefix = 'b_par')
# ------------------------------------
def test_print():
    '''
    Test string representations
    '''
    data = {'a' : (1., 1.), 'b' : (2., 1.)}

    ms = Measurement(data=data)

    ms.__repr__()
    ms.__str__()
# ----------------------
def test_to_dict():
    '''
    Tests to_dict method
    '''
    data = {'a' : (1., 1.), 'b' : (2., 1.)}

    ms  = Measurement(data=data)
    res = ms.to_dict()

    assert res == {
        'a' : 1., 'a_error' : 1.,
        'b' : 2., 'b_error' : 1.}
