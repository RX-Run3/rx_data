import os
from pathlib   import Path
from rx_common import Trigger

ANADIR     = Path(os.environ['ANADIR'])
TRIGGER    = config['trigger'] 
SIGNAL     = config['signal' ] 
DATA       = config['data'   ] 
BLOCKS     = config['blocks' ] 
BREMS      = config['brems'  ] 
COMPONENTS = config['components']
Q2BINS     = config['q2bins'] 
NAME       = config['name']
CHANNEL    = Trigger(TRIGGER).channel
PROJECT    = Trigger(TRIGGER).project

INPUT_DIR  = ANADIR / f'fits/data/{NAME}'
OUTPUTDIR  = ANADIR / f'plots/web/{NAME}/components/{PROJECT}'
REGEX      = r'\d{3}_\d{3}'

OUTPUTDIR.mkdir(parents=True, exist_ok=True)
# ----------------------------
def _get_wc() -> tuple[list[str], list[str]]:
    '''
    Returns
    ---------
    Working points for BDT
    '''
    paths = list(INPUT_DIR.glob('*'))
    paths = [ path for path in paths if re.match(REGEX, path.name) ]

    cmb   = [ path.name.split('_')[0] for path in paths ]
    prc   = [ path.name.split('_')[1] for path in paths ]

    return cmb, prc
# ----------------------------
cmb, prc = _get_wc()
rule all:
    input: 
        expand(
        OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{DATA}_combined.png',
        q2bin     = Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        ),
        # ----------
        expand(
        OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{SIGNAL}_{{brem}}_{{block}}.png',
        q2bin     = Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        brem      = BREMS,
        block     = BLOCKS,
        ),
        # ----------
        expand(
        OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}_{brem}.png',
        q2bin     = Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        component = COMPONENTS,
        brem      = BREMS,
        ),
        # ----------
        expand(
        OUTPUTDIR / '{q2bin}/{prc}_{cmb}/index.md',
        q2bin     = Q2BINS,
        prc       = prc, 
        cmb       = cmb, 
        )
rule metadata:
    output: OUTPUTDIR / '{q2bin}/{prc}_{cmb}/index.md'
    params:
        data = DATA
    shell :
        '''
        echo "Title: {wildcards.prc}-{wildcards.cmb}"  > {output}
        echo "Thumbnail: {params.data}_combined.png"   >> {output}
        '''
rule copy_signal:
    output: OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{SIGNAL}_{{brem}}_{{block}}.png'
    params:
        root_dir = INPUT_DIR,
        trigger  = TRIGGER,
        project  = PROJECT,
        channel  = CHANNEL,
        signal   = SIGNAL,
        name     = NAME,
    shell:
        '''
        mkdir -p $(dirname {output})

        WP="{wildcards.cmb}_{wildcards.prc}_all"
        CAT={wildcards.brem}_{wildcards.block}

        OUTDIR="{params.root_dir}/$WP/{params.name}/{params.project}/{params.channel}/{wildcards.q2bin}/{params.signal}/fit/{wildcards.brem}/$CAT"
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
    output: OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{component}_{brem}.png'
    wildcard_constraints:
        component = '|'.join(COMPONENTS),
        brem      = '|'.join(BREMS),
    params:
        root_dir = INPUT_DIR,
        trigger  = TRIGGER,
        name     = NAME,
        project  = PROJECT,
        channel  = CHANNEL,
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP="{wildcards.cmb}_{wildcards.prc}_all"

        if   [[ $COMP == "data_24" ]]; then
            OUTDIR="{params.root_dir}/$WP/{params.name}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/brem_xx1_brem_xx2/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "comb"    ]]; then
            OUTDIR="{params.root_dir}/$WP/{params.name}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "ccbar"   ]]; then
            OUTDIR="{params.root_dir}/$WP/{params.name}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/c-bar-c-X.png
        else
            OUTDIR="{params.root_dir}/$WP/{params.name}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
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
    output: OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{DATA}_combined.png'
    params:
        root_dir = INPUT_DIR,
        trigger  = TRIGGER,
        data     = DATA,
        name     = NAME,
        project  = PROJECT,
        channel  = CHANNEL,
    shell:
        '''
        mkdir -p $(dirname {output})

        WP="{wildcards.cmb}_{wildcards.prc}_all"

        OUTDIR="{params.root_dir}/$WP/{params.name}/{params.project}/{params.channel}/{wildcards.q2bin}/{params.data}/fit/brem_xx1_brem_xx2/both_brem"
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
