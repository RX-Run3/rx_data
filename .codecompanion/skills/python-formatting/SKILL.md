---
name       : python-formatting
description: Python formatting and coding conventions for this project.
---

# Spaces and alignment

The following instructions are meant to improve readability of generated code.

- The code should be aligned for equal signs:

```python
def test_hash_simple():
    '''
    Function testing the hashing of a s list of python objects
    '''
    obj = [1, 'name', [1, 'sub', 'list'], {'x' : 1}]
    val = hashing.hash_object(obj)
```

in imports:

```python
from omegaconf   import OmegaConf
from dmu.generic import hashing
from dmu         import LogStore

log=LogStore.add_logger('dmu:test_hashing')
```

In dictionaries using colons:

```python
    data = {
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Age' : [25, 30, 35],
        'City': ['New York', 'London', 'Paris']
        }
```

Use at least one space between the code and the return statement as in:

```python
        '''
        data = load_data(package = package, fpath = loc)

        return cls(**data)
```

# Imports

When importing make sure that the `import` statements come first, then the
`from` ones, as in:

```python
import math
import pytest

from dmu         import LogStore
from typing      import Any
from dmu.generic import caching
```

in docstrings that list parameters as in:

```python
        '''
        Parameters
        -------------
        brem    : Brem category to fit 
        signal  : Signal component, needed to get constraints for CR fit
        cfg_fit : Full fit configuration
        '''
 
```

# Docstrings

Docstrings should always be added at the beggining of modules and should describe
briefly what the module contains as in:

```python
'''
This file is meant to hold tests for the caching
utilities in generic/caching.py
'''
import math
import pytest
```

Functions should also have docstrings and they should look like:

```python
    def __pick_parameter(self, name : str) -> bool:
        '''
        Parameters
        -------------
        name: Parameter name from SS fit

        Returns
        -------------
        True if this parameter is meant to be constrained
        '''
        par_names = self._cfg_cmb.constraints.parameters[self._q2bin]

```

Pydantic attributes should be documented with a docstring, e.g:

```python
class User(BaseModel):
    name: str
    '''The user's full name.'''

    age: int
    '''The user's age in years.'''
```

# Separation between methods, functions, etc

Separate functions and methods with a hash and dashes as in:

```python
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:fsystem:fcopy', 10)
# ----------------------
def _make_paths(
    dir_path  : Path, 
    make_file : bool,
```

