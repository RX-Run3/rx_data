'''
Module with Settings class
'''

from pathlib           import Path
from pydantic_settings import BaseSettings

# ------------------------------
class Settings(BaseSettings):
    '''
    Class meant to store user specific variables
    '''
    ANADIR   : Path
    USERHOST : str
# ------------------------------
