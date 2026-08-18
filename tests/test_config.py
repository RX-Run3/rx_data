from hqm2.config import Conf

#----------------------------------
def test_simple():
    Conf.binning['cut'] = 'a < 3'
    Conf.binning['var'] = 'a'
    Conf.binning['bin'] = '2'

    Conf.print_config('binning')
#----------------------------------
def test_make_path():
    out_dir=Conf.make_path(kind='test', dset='2018', dname=f'dir_name', fname=None)
    out_pat=Conf.make_path(kind='test', dset='2018', dname=f'dir_name', fname='file.json')

    Conf.binning['cut'] = 'a < 3'
    Conf.binning['var'] = 'a'
    Conf.binning['bin'] = '2'

    out_dir=Conf.make_path(kind='test', dset='2018', dname=f'dir_name', fname=None)
    out_pat=Conf.make_path(kind='test', dset='2018', dname=f'dir_name', fname='file.json')
#----------------------------------
def main():
    test_simple()
    test_make_path()
#----------------------------------
if __name__ == '__main__':
    main()
