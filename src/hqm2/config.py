from log_store import log_store

log=log_store.add_logger('rx_hqm2:config')
#-------------------------------------------------------------------
class config:
    binning=dict()

    @staticmethod
    def print_config(name):
        if not hasattr(config, name):
            log.error(f'Cannot find {name} in configuration')
            raise

        d_data = getattr(config, name)
        log.info(80 * '-')
        log.info(f'{"Setting":<30}{"Value":<50}')
        log.info(80 * '-')
        for key, val in d_data.items():
            log.info(f'{key:<30}{val:<50}')
#-------------------------------------------------------------------
