'''
Module with plotting utilities
'''
# pylint: disable=too-many-positional-arguments, too-many-arguments

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
def annotate(
        l_x   : list[float],
        l_y   : list[float],
        l_v   : list[float],
        form  : str =    '{}',
        xoff  : int =  0,
        yoff  : int =-20,
        size  : int = 20,
        color : str = 'black') -> None:
    '''
    Function used to annotate plots

    l_x(y): List of x(y) coordinates for markers
    l_v   : List of numerical values to annotate markers
    form  : Formatting, e.g. {:.3f}
    color : String with color for markers and annotation, e.g. black
    size  : Font size, default 20
    x(y)off : Offset in x(y).
    '''
    for x, y, v in zip(l_x, l_y, l_v, strict=False):
        label = form.format(v)

        plt.plot(x, y, marker='o', markersize= 5, markeredgecolor=color, markerfacecolor=color)
        plt.annotate(label, (x,y), fontsize=size, textcoords="offset points", xytext=(xoff, yoff), color=color, ha='center')
# ---------------------------------------------------------------------------
