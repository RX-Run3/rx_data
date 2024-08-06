import os
import ROOT
import glob
import numpy
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
    def _get_year_array(self, year, d_cut=None):
        dat_dir = {'data' : 'r_fits'}[self._proc]
        log.info(f'Picking data from: {dat_dir}')

        asl_dir = os.environ['ASLDIR']
        root_wc = f'{asl_dir}/{dat_dir}/{self._proc}/v10.21p2/{year}_{self._trig}/*.root'
        l_file  = glob.glob(root_wc)
        nfiles  = len(l_file)

        if nfiles == 0:
            log.error(f'No files found in: {root_wc}')
            raise

        log.debug(f'{nfiles} files found in: {root_wc}')

        rdf = ROOT.RDataFrame(self._trig, l_file)
        rdf = self._apply_selection(rdf, year, d_cut)

        arr_mass = rdf.AsNumpy(['B_M'])['B_M']

        return arr_mass
    #----------------------------------
    def _apply_selection(self, rdf, year, d_cut):
        qsq = rs.get('q2' , self._trig, q2bin=self._qsq, year=year)
        bdt = rs.get('bdt', self._trig, q2bin=self._qsq, year=year)
        rdf = rdf.Filter(qsq, 'qsq')
        rdf = rdf.Filter(bdt, 'bdt')
        for name, cut in d_cut.items():
            rdf = rdf.Filter(cut, name)

        rep = rdf.Report()
        rep.Print()

        return rdf
    #----------------------------------
    def get_array(self, variable='B_M', d_cut=dict()):
        if   self._dset == 'r1':
            arr_11 = self._get_year_array('2011', d_cut=d_cut)
            arr_12 = self._get_year_array('2012', d_cut=d_cut)

            arr_va = numpy.concatenate([arr_11, arr_12])
        elif self._dset == 'r2p1':
            arr_15 = self._get_year_array('2015', d_cut=d_cut)
            arr_16 = self._get_year_array('2016', d_cut=d_cut)

            arr_va = numpy.concatenate([arr_15, arr_16])
        else:
            arr_va = self._get_year_array(self._dset, d_cut=d_cut)

        return arr_va
#----------------------------------

