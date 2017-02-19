from .parsedishes import add_dishes
from .parsevegetables import add_vegetables
from .parsepokemon import add_pokemons
from .parsejokes import add_jokes

def prepare_data(dryrun=True):
    add_dishes(dryrun)
    add_vegetables(dryrun)
    add_pokemons(dryrun)
    add_jokes(dryrun)
