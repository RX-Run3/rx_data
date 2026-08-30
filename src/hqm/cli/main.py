'''
HQM CLI
'''
import typer 

from hqm.cli.build_database import build_database
from hqm.cli.make_trfc      import make_trfc 

ctx  = {'help_option_names' : ['-h', '--help']}
main = typer.Typer(help = 'HQM CLI', context_settings=ctx)
main.command(name = 'build-database')(build_database)
main.command(name = 'make-trfc')(make_trfc)
# ----------------------
if __name__ == '__main__':
    main()
