import os
from pathlib import Path

_COMPONENTS = [
    'data_24', 
    'comb', 
    ]
_Q2BINS    = ['low', 'central', 'high']
_INPUT_DIR = Path('/home/acampove/Tests/web/rare')
ANADIR     = Path(os.environ['ANADIR'])
_OUTPUTDIR = ANADIR / 'plots/web/scan/components'

_OUTPUTDIR.mkdir(parents=True, exist_ok=True)
# ----------------------------
def _get_wc() -> tuple[list[str], list[str]]:
    '''
    Returns
    ---------
    Working points for BDT
    '''
    paths = list(_INPUT_DIR.glob('*'))

    cmb   = [ path.name.split('_')[0] for path in paths ]
    prc   = [ path.name.split('_')[1] for path in paths ]

    return cmb, prc
# ----------------------------
cmb, prc = _get_wc()

rule all:
    input: 
        expand(
        _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}.png',
        cmb       = cmb, 
        prc       = prc, 
        component = _COMPONENTS,
        q2bin     = _Q2BINS,
        ),
        # ----------
        expand(
        _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/index.md',
        cmb       = cmb, 
        prc       = prc, 
        component = _COMPONENTS,
        q2bin     = _Q2BINS,
        )
rule metadata:
    output: _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/index.md'
    shell :
        '''
        echo "Title: {wildcards.prc}-{wildcards.cmb}"  > {output}
        echo "Thumbnail: data.png"   >> {output}
        '''
rule link:
    output: _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}.png'
    params:
        root_dir = _INPUT_DIR,
        trigger  = 'Hlt2RD_B0ToKpPimEE_MVA',
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP={wildcards.cmb}_{wildcards.prc}_all
        OUTDIR='{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/brem_x12/brem_x12'

        if   [[ $COMP == "ccbar" ]]; then
            SOURCE=$OUTDIR/c-bar-c-X.png
        else
            SOURCE=$OUTDIR/fit_linear.png
        fi

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t "{wildcards.component}"
        else
            cp $SOURCE {output}
        fi
        '''
