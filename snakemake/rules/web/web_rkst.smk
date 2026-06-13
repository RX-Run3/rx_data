import os
from pathlib import Path

TRIGGER     = 'Hlt2RD_B0ToKpPimEE_MVA',
SIGNAL      = 'bdkstkpiee'
DATA        = 'data_24'
_BLOCKS     = [ f'b{block}' for block in range(1, 1) ]
_BREMS      = ['brem_xx1', 'brem_xx2']
_COMPONENTS = [
    DATA, 
    'comb', 
    'ccbar',
    'bpkpipiee',
    'bdkstkpijpsiee',
    'bdkstkpipsi2ee',
    ]
_Q2BINS    = ['low', 'central']
_INPUT_DIR = Path('/home/acampove/external_02/fits/data/rare')
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
        _OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{DATA}_combined.png',
        q2bin     = _Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        ),
        # ----------
        expand(
        _OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{SIGNAL}_{{brem}}_{{block}}.png',
        q2bin     = _Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        brem      = _BREMS,
        block     = _BLOCKS,
        ),
        # ----------
        expand(
        _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}_{brem}.png',
        q2bin     = _Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        component = _COMPONENTS,
        brem      = _BREMS,
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
    params:
        data = DATA
    shell :
        '''
        echo "Title: {wildcards.prc}-{wildcards.cmb}"  > {output}
        echo "Thumbnail: {params.data}_combined.png"   >> {output}
        '''
rule copy_signal:
    output: _OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{SIGNAL}_{{brem}}_{{block}}.png'
    params:
        root_dir = _INPUT_DIR,
        trigger  = TRIGGER,
        signal   = SIGNAL,
    shell:
        '''
        mkdir -p $(dirname {output})

        WP="{wildcards.cmb}_{wildcards.prc}_all"
        CAT={wildcards.brem}_{wildcards.block}

        OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{params.signal}/fit/{wildcards.brem}/$CAT"
        SOURCE=$OUTDIR/fit_linear.png

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t {params.signal} -s $SOURCE
        else
            ln -s $SOURCE {output}
        fi
        '''
rule copy_non_signal:
    output: _OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}_{brem}.png'
    wildcard_constraints:
        component = '|'.join(_COMPONENTS),
        brem      = '|'.join(_BREMS),
    params:
        root_dir = _INPUT_DIR,
        trigger  = TRIGGER,
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP="{wildcards.cmb}_{wildcards.prc}_all"

        if   [[ $COMP == "data_24" ]]; then
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/brem_xx1_brem_xx2/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "comb"    ]]; then
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "ccbar"   ]]; then
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/c-bar-c-X.png
        else
            OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        fi

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t "{wildcards.component}, {wildcards.brem}" -s $SOURCE
        else
            ln -s $SOURCE {output}
        fi
        '''
rule copy_combined:
    output: _OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{DATA}_combined.png'
    params:
        root_dir = _INPUT_DIR,
        trigger  = TRIGGER,
        data     = DATA
    shell:
        '''
        mkdir -p $(dirname {output})

        WP="{wildcards.cmb}_{wildcards.prc}_all"

        OUTDIR="{params.root_dir}/$WP/rare/rkst/ee/{wildcards.q2bin}/{params.data}/fit/brem_xx1_brem_xx2/both_brem"
        SOURCE=$OUTDIR/fit_linear.png

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t "{params.data}, combined" -s $SOURCE
        else
            ln -s $SOURCE {output}
        fi
        '''
