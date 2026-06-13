NJOBS=3
rule all:
    input: expand("results/file_{index}.txt", index=range(1, NJOBS + 1))

rule test:
    output:
        'results/file_{index}.txt'
    container:
        'gitlab-registry.cern.ch/lhcb-rd/cal-rx-run3:97024d733'
    resources:
        kubernetes_memory_limit="4000Mi"
    shell:
        """
        SOURCE=results/file_{wildcards.index}.txt
        TARGET=/eos/lhcb/wg/RD/RX_run3/tests

        mkdir -p results
        mkdir -p $TARGET 

        touch $SOURCE

        cp $SOURCE $TARGET
        """
