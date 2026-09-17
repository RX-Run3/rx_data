'''
HQM CLI
'''
import typer

from hqm.cli.build_database import build_database
from hqm.cli.make_ccbar     import make_ccbar
from hqm.cli.make_trfc      import make_trfc
from hqm.cli.make_prec      import make_prec
from hqm.cli.plot_ratios    import plot_ratios
from hqm.cli.fit_resonant   import fit_resonant
from hqm.cli.fit_mc         import fit_mc
from hqm.cli.run_ccbar      import run_ccbar
from hqm.cli.run_databases  import run_databases

ctx  = {'help_option_names' : ['-h', '--help']}
main = typer.Typer(help = 'HQM CLI', context_settings=ctx)

main.command(name = 'build-database')(build_database)
main.command(name = 'make-trfc')(make_trfc)
main.command(name = 'make-prec')(make_prec)
main.command(name = 'make-ccbar')(make_ccbar)
main.command(name = 'plot-ratios')(plot_ratios)
main.command(name = 'fit-resonant')(fit_resonant)
main.command(name = 'fit-mc')(fit_mc)

main.command(name = 'run-ccbar')(run_ccbar)
main.command(name = 'run-databases')(run_databases)
# ----------------------
if __name__ == '__main__':
    main()
