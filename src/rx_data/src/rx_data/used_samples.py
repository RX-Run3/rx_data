'''
MOdule holding UsedSamples class
'''
from rx_common    import Component, Trigger
from pydantic     import BaseModel, model_validator
from dmu.generic  import utilities as gut
from dmu          import LogStore
from rx_common    import Project

log = LogStore.add_logger('rx_data:used_samples')
# -----------------------------------------
class UsedSamples(BaseModel):
    '''
    Class representing samples needed for analysis
    '''
    triggers : list[Trigger]
    samples  : dict[str,list[int|str]]
    # --------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate_samples(cls, data):
        fail = False
        for samples in data['samples'].values():
            for sample in samples:
                if Component.is_valid(arg = sample):
                    continue

                fail = True
                log.warning(f'Invalid sample: {sample}')

        if fail:
            raise ValueError('Found at least one invalid sample')

        return data
    # --------------------------------
    @classmethod
    def from_project(cls, project : Project) -> 'UsedSamples':
        data = gut.load_data(
            package='rx_data_data',
            fpath  =f'copy_files/{project}.yaml')

        return cls(**data)
    # --------------------------------
    @property
    def identifiers(self) -> list[str]:
        '''
        List of strings used to identify samples
        '''
        values : list[str] = []
        for identifiers in self.samples.values():
            str_identifiers = [ str(val).lower() for val in identifiers ]

            values += str_identifiers

        return values
# --------------------------------
