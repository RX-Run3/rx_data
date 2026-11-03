'''
Module with Measurement class
'''
from dmu      import LogStore
from pydantic import BaseModel, ConfigDict

log=LogStore.add_logger('dmu:stats:measurement')
# ----------------------------------------------
class Measurement(BaseModel):
    '''
    Class meant to symbolize a set of measurements, useful to represent:

    - Parameters of fit
    '''
    data         : dict[str, tuple[float, float]]
    model_config = ConfigDict(frozen=True)
    # ----------------------
    def __repr__(self) -> str:
        '''
        String representation
        '''
        message = f'\n{"Variable":<40}{"Value":<20}{"Error":<20}\n'
        message+= 80 * '-' + '\n'
        for name, (value, error) in self.data.items():
            message += f'{name:<40}{value:<20.3f}{error:<20.3f}\n'

        return message
    # ----------------------
    def __str__(self) -> str:
        return self.__repr__()
    # ----------------------
    def __getitem__(self, variable : str) -> tuple[float,float]:
        '''
        Parameters
        -------------
        variable: Name of variable associated to measurement

        Returns
        -------------
        Tuple with value and error
        '''
        if variable not in self.data:
            raise KeyError(f'Invalid variable: {variable}')

        return self.data[variable]
    # ----------------------
    def get_values(self, prefix : str) -> tuple[float,float]:
        '''
        Parameters
        -------------
        prefix: String that parameter has to start with

        Returns
        -------------
        Tuple with value and error for fitted parameter
        '''
        filtered = [ val for key, val in self.data.items() if key.startswith(prefix) ]

        if len(filtered) != 1:
            log.error(self)
            raise ValueError(f'Could not find one and only one parameter starting with {prefix}')

        return filtered[0]
    # ----------------------
    def __contains__(self, variable : str) -> bool:
        '''
        Parameters
        ----------------
        variable: Name of variable sought

        Returns
        ----------------
        True if variable was found
        '''

        return variable in self.data
    # ----------------------
    def to_dict(self) -> dict[str, float]:
        '''
        Returns
        -------------
        Dictionary mapping names of quatities to numerical values.
        E.g. given quantity x, entries x and x_error are created
        '''
        result = dict()
        for name, (value, error) in self.data.items():
            result[name           ] = value
            result[f'{name}_error'] = error

        return result
# ----------------------------------------------
