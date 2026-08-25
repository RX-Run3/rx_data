'''
HQM CLI
'''
import typer 

from hqm.cli.build_database import build_database

main = typer.Typer(help = 'HQM CLI')
main.command(name = 'build-database')(build_database)
# ----------------------
if __name__ == '__main__':
    main()
