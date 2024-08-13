from hqm2.config import config

#----------------------------------
def test_simple():
    config.binning['cut'] = 'a < 3'
    config.binning['var'] = 'a'
    config.binning['bin'] = '2'

    config.print_config('binning')
#----------------------------------
def main():
    test_simple()
#----------------------------------
if __name__ == '__main__':
    main()
