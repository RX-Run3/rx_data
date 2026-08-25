'''
HQM CLI
'''
import typer 

from hqm.cli.build_database import build_database

ctx  = {"help_option_names": ["-h", "--help"]}
main = typer.Typer(help = 'HQM CLI', context_settings=ctx)
main.command(name = 'build-database')(build_database)
# ----------------------
if __name__ == '__main__':
    main()
