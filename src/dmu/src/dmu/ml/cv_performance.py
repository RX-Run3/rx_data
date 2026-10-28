'''
This module contains the class CVPerformance
'''
# pylint: disable=too-many-positional-arguments, too-many-arguments

from ROOT                  import RDF
from dmu.ml.cv_classifier  import CVClassifier
from dmu.ml.cv_predict     import CVPredict
from dmu.ml.train_mva      import TrainMva
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('dmu:ml:cv_performance')
# -----------------------------------------------------
class CVPerformance:
    '''
    This class is meant to:

    - Compare the classifier performance, through the ROC curve, of a model, for a given background and signal sample
    '''
    # ---------------------------
    def plot_roc(
            self,
            name  : str,
            color : str,
            sig   : RDF.RNode,
            bkg   : RDF.RNode,
            model : list[CVClassifier] ) -> float:
        '''
        Method in charge of picking up model and data and plotting ROC curve

        Parameters
        --------------------------
        name : Label of combination, used for plots
        sig  : ROOT dataframe storing signal samples
        bkg  : ROOT dataframe storing background samples
        model: List of instances of the CVClassifier

        Returns
        --------------------------
        Area under the ROC curve
        '''
        log.info(f'Loading {name}')

        cvp_sig = CVPredict(models=model, rdf=sig)
        arr_sig = cvp_sig.predict()

        cvp_bkg = CVPredict(models=model, rdf=bkg)
        arr_bkg = cvp_bkg.predict()

        _, _, auc = TrainMva.plot_roc_from_prob(
                arr_sig_prb=arr_sig,
                arr_bkg_prb=arr_bkg,
                kind       =   name,
                color      =  color, # This should allow the function to pick kind
                ifold      =    999) # for the label

        return auc
# -----------------------------------------------------
