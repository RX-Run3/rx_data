from hqm2.config import config

#----------------------------------
def test_simple():
    config.binning['cut'] = 'a < 3'
    config.binning['var'] = 'a'
    config.binning['bin'] = '2'

    config.print_config('binning')
#----------------------------------
def test_make_path():
    out_dir=config.make_data_path(kind='test', dset='2018', dname=f'dir_name', fname=None)
    out_pat=config.make_data_path(kind='test', dset='2018', dname=f'dir_name', fname='file.json')

    config.binning['cut'] = 'a < 3'
    config.binning['var'] = 'a'
    config.binning['bin'] = '2'

    out_dir=config.make_data_path(kind='test', dset='2018', dname=f'dir_name', fname=None)
    out_pat=config.make_data_path(kind='test', dset='2018', dname=f'dir_name', fname='file.json')
#----------------------------------
def main():
    test_simple()
    test_make_path()
#----------------------------------
if __name__ == '__main__':
    main()
