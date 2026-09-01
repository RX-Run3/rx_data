'''
HQM CLI
'''
import typer

from hqm.cli.build_database import build_database
from hqm.cli.make_trfc      import make_trfc
from hqm.cli.make_prec      import make_prec

ctx  = {'help_option_names' : ['-h', '--help']}
main = typer.Typer(help = 'HQM CLI', context_settings=ctx)
main.command(name = 'build-database')(build_database)
main.command(name = 'make-trfc')(make_trfc)
main.command(name = 'make-prec')(make_prec)
# ----------------------
if __name__ == '__main__':
    main()
