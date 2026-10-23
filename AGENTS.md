# Project Instructions

## Python
- Use Python 3.13.
- Use type annotations, `Any` is NOT an acceptable annotation.
- Use pyrefly for type checking and Ruff for linting.

## Code Quality
- Follow existing project conventions.
- Avoid unnecessary abstractions.
- Write tests for new functionality.
- Do not use magic numbers or magic strings, whenever a
non-trivial value (non-zero, not one, etc) is neede
make it a module constant and document it as in:

```python
_RGXPR : Final[str] = r'brem_(xx\d)_b(\d)_(?:rk|rkst)_(?:ee|mm)_(scale|reso)_flt'
'''Regex for non-fractions'''
_RGXFR : Final[str] = r'(brem|block)_brem_([x012]{3})_b(\d)(_reso)?_flt'
'''Regex for fractions'''
```
i.e. use `Final` to declare these variables as constant.

- When creating pydantic data models or dataclasses always
freeze them, unless they have to be mutable. Use the following
format:

```python
class WorkingPoint(RootModel[list[Cut]], frozen = True):
```

i.e. do not use `ConfigDict`

- Do not add imports that are not needed

## Workflow
- Make only the changes requested.
- Run relevant tests after modifying code.

## Code navigation and editing

- For finding symbols, definitions and references, 
  prefer the Serena tools over grep or reading whole files.
- For all code edits, use the built-in insert_edit_into_file 
  tool so changes can be reviewed as a diff.
- Do not read entire files when a symbol overview or a 
  single symbol body is enough.
- Do not modify files that are outside the codebase
- Do not modify files in the codebase that you haven't been
  explicitly prompted to modify.
- Do not request access to files unless they are truly
  needed for the task assigned.
- Do not read or use search tools on code that is not
  explicitly mentioned in the request
- If you deem a module as needed for you to do the task,
  request access with a justification of why you need that access.
