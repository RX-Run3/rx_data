import os
from pathlib import Path

_BLOCKS     = [ f'b{block}' for block in range(1, 9) ]
_BREMS      = ['xx1', 'xx2']
_COMPONENTS = [
    'data_24', 
    'comb', 
    'ccbar',
    'bpkpipiee',
    'bdkstkpijpsiee',
    'bdkstkpipsi2ee',
    ]
_Q2BINS    = ['low', 'central']
_INPUT_DIR = Path('/home/acampove/Tests/web/rare')
ANADIR     = Path(os.environ['ANADIR'])
_OUTPUTDIR = ANADIR / 'plots/web/scan/components/rkst'

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
        _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/bdkstkpiee_{brem}_{block}.png',
        q2bin     = _Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        brem      = _BREMS,
        block     = _BLOCKS,
        ),
        # ----------
        expand(
        _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}.png',
        q2bin     = _Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        component = _COMPONENTS,
        ),
        # ----------
        expand(
        _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/index.md',
        q2bin     = _Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        )
rule metadata:
    output: _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/index.md'
    shell :
        '''
        echo "Title: {wildcards.prc}-{wildcards.cmb}"  > {output}
        echo "Thumbnail: data_24.png"   >> {output}
        '''
rule copy_signal:
    output: _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}_{brem}_{block}.png'
    params:
        root_dir = _INPUT_DIR,
        trigger  = 'Hlt2RD_B0ToKpPimEE_MVA',
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP="{wildcards.cmb}_{wildcards.prc}_all"
        CAT=brem_{wildcards.brem}_{wildcards.block}

        OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/$COMP/fit/main/$CAT"
        SOURCE=$OUTDIR/fit_linear.png

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t $COMP -s $SOURCE
        else
            ln -s $SOURCE {output}
        fi
        '''
rule copy_non_signal:
    output: _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}.png'
    wildcard_constraints:
        component = '|'.join(_COMPONENTS)
    params:
        root_dir = _INPUT_DIR,
        trigger  = 'Hlt2RD_B0ToKpPimEE_MVA',
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP="{wildcards.cmb}_{wildcards.prc}_all"

        if   [[ $COMP == "data_24" ]]; then
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/brem_x12/brem_x12"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "comb"    ]]; then
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/comb"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "ccbar"   ]]; then
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/main"
            SOURCE=$OUTDIR/c-bar-c-X.png
        else
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/main"
            SOURCE=$OUTDIR/fit_linear.png
        fi

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t "{wildcards.component}" -s $SOURCE
        else
            ln -s $SOURCE {output}
        fi
        '''
