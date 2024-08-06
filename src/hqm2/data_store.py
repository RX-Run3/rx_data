import os
import ROOT
import glob
import read_selection as rs

from log_store import log_store

log=log_store.add_logger('rx_hqm2:data_store')
#----------------------------------
class data_store:
    '''
    Class used to provide data, simulated or real after full selection
    '''
    def __init__(self, qsq=None, dset=None, trig=None, proc=None):
        self._qsq  = qsq
        self._dset = dset
        self._trig = trig 
        self._proc = proc 
    #----------------------------------
    def get_array(self, variable='B_M', cuts=dict()):
        dat_dir = {'data' : 'r_fits'}[self._proc]
        log.info(f'Picking data from: {dat_dir}')

        asl_dir = os.environ['ASLDIR']
        root_wc = f'{asl_dir}/{dat_dir}/{self._proc}/v10.21p2/{self._dset}_{self._trig}/*.root'
        l_file  = glob.glob(root_wc)
        nfiles  = len(l_file)

        if nfiles == 0:
            log.error(f'No files found in: {root_wc}')
            raise

        log.debug(f'{nfiles} files found in: {root_wc}')

        rdf = ROOT.RDataFrame(self._trig, l_file)
        qsq = rs.get('q2' , self._trig, q2bin=self._qsq, year=self._dset)
        bdt = rs.get('bdt', self._trig, q2bin=self._qsq, year=self._dset)
        rdf = rdf.Filter(qsq, 'qsq')
        rdf = rdf.Filter(bdt, 'bdt')
        for name, cut in cuts.items():
            rdf = rdf.Filter(cut, name)

        rep = rdf.Report()
        rep.Print()

        arr_mass = rdf.AsNumpy(['B_M'])['B_M']

        return arr_mass
#----------------------------------

