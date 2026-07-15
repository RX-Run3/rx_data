import os
from pathlib   import Path
from rx_common import Trigger

_KINDS = {'reso', 'rare'}
# --------------------------------------------
def _kind_from_name(name : str) -> str:
    parts = name.split('_')
    kind  = parts[0]

    if kind not in _KINDS:
        raise ValueError(f'Invalid kind: {kind}')

    return kind
# --------------------------------------------
ANADIR     = Path(os.environ['ANADIR'])
TRIGGER    = config['trigger'] 
SIGNAL     = config['signal' ] 
DATA       = config['data'   ] 
BLOCKS     = config['blocks' ] 
BREMS      = config['brems'  ] 
COMPONENTS = config['components']
Q2BINS     = config['q2bins'] 
NAME       = config['name']
KIND       = _kind_from_name(name = NAME)
CHANNEL    = Trigger(TRIGGER).channel
PROJECT    = Trigger(TRIGGER).project
INPUT_DIR  = ANADIR / f'fits/data/{NAME}'
OUTPUTDIR  = ANADIR / f'plots/web/{NAME}/components/{PROJECT}'
REGEX      = r'\d{3}_\d{3}_(b\d|all)'

if SIGNAL in COMPONENTS:
    raise ValueError(f'Found signal {SIGNAL} among components')

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
CMB, PRC = _get_wc()
rule all:
    input: 
        expand(
        OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{{block}}/{DATA}_combined.png',
        q2bin     = Q2BINS,
        prc       = PRC, 
        cmb       = CMB, 
        block     = BLOCKS,
        ),
        # ----------
        expand(
        OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{{block}}/{SIGNAL}_{{brem}}.png',
        q2bin     = Q2BINS,
        prc       = PRC, 
        cmb       = CMB, 
        block     = BLOCKS,
        brem      = BREMS,
        ),
        # ----------
        expand(
        OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{block}/{component}_{brem}.png',
        q2bin     = Q2BINS,
        prc       = PRC, 
        cmb       = CMB, 
        block     = BLOCKS,
        component = COMPONENTS,
        brem      = BREMS,
        ),
        # ----------
        expand(
        OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{block}/index.md',
        q2bin     = Q2BINS,
        prc       = PRC, 
        cmb       = CMB, 
        block     = BLOCKS,
        )
rule metadata:
    output              : OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{block}/index.md'
    wildcard_constraints:
        q2bin= '|'.join(Q2BINS),
        prc  = '|'.join(PRC),
        cmb  = '|'.join(CMB),
        block= '|'.join(BLOCKS),
    params:
        data = DATA
    shell :
        '''
        echo "Title: {wildcards.block}"                 > {output}
        echo "Thumbnail: {params.data}_combined.png"   >> {output}
        '''
rule copy_signal:
    output              : OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{{block}}/{SIGNAL}_{{brem}}.png'
    wildcard_constraints:
        q2bin     = '|'.join(Q2BINS),
        prc       = '|'.join(PRC),
        cmb       = '|'.join(CMB),
        block     = '|'.join(BLOCKS),
        brem      = '|'.join(BREMS),
    params:
        root_dir  = INPUT_DIR,
        trigger   = TRIGGER,
        project   = PROJECT,
        channel   = CHANNEL,
        signal    = SIGNAL,
        name      = NAME,
        kind      = KIND,
    shell:
        '''
        mkdir -p $(dirname {output})

        WP="{wildcards.cmb}_{wildcards.prc}_{wildcards.block}"

        OUTDIR="{params.root_dir}/$WP/{params.kind}/{params.project}/{params.channel}/{wildcards.q2bin}/{params.signal}/fit/{wildcards.brem}/{wildcards.brem}"
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
    output              : OUTPUTDIR / '{q2bin}/{prc}_{cmb}/{block}/{component}_{brem}.png'
    wildcard_constraints:
        q2bin     = '|'.join(Q2BINS),
        prc       = '|'.join(PRC),
        cmb       = '|'.join(CMB),
        block     = '|'.join(BLOCKS),
        component = '|'.join(COMPONENTS),
        brem      = '|'.join(BREMS),
    params:
        root_dir  = INPUT_DIR,
        trigger   = TRIGGER,
        name      = NAME,
        project   = PROJECT,
        channel   = CHANNEL,
        kind      = KIND,
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP="{wildcards.cmb}_{wildcards.prc}_{wildcards.block}"

        if   [[ $COMP == "data_24" ]]; then
            OUTDIR="{params.root_dir}/$WP/{params.kind}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/brem_xx1_brem_xx2/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "comb"    ]]; then
            OUTDIR="{params.root_dir}/$WP/{params.kind}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/fit_linear.png
        elif [[ $COMP == "ccbar"   ]]; then
            OUTDIR="{params.root_dir}/$WP/{params.kind}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}"
            SOURCE=$OUTDIR/c-bar-c-X.png
        else
            OUTDIR="{params.root_dir}/$WP/{params.kind}/{params.project}/{params.channel}/{wildcards.q2bin}/{wildcards.component}/fit/{wildcards.brem}/{wildcards.brem}"
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
    output: OUTPUTDIR / f'{{q2bin}}/{{prc}}_{{cmb}}/{{block}}/{DATA}_combined.png'
    wildcard_constraints:
        q2bin     = '|'.join(Q2BINS),
        prc       = '|'.join(PRC),
        cmb       = '|'.join(CMB),
        block     = '|'.join(BLOCKS),
    params:
        root_dir = INPUT_DIR,
        trigger  = TRIGGER,
        data     = DATA,
        name     = NAME,
        project  = PROJECT,
        channel  = CHANNEL,
        kind     = KIND
    shell:
        '''
        mkdir -p $(dirname {output})

        WP="{wildcards.cmb}_{wildcards.prc}_{wildcards.block}"
        OUTDIR="{params.root_dir}/$WP/{params.kind}/{params.project}/{params.channel}/{wildcards.q2bin}/{params.data}/fit/brem_xx1_brem_xx2/both_brem"
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
