import numpy as np
import matplotlib
import matplotlib.pylab as plt
import matplotlib.font_manager as fm
import scipy
import scipy.interpolate as spi
import datetime
import time
import csv
import os

import graph


def main(date):
    plt.figure(figsize=(16, 9), dpi=80)
    plt.subplots_adjust(left=0.10, bottom=0.08, right=0.94, top=0.92)
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()
    with open(f"../data/kr_deepdive/interpolate/{date}.csv", 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        x, y = list(zip(*rdr))
        x = [int(n) for n in x]
        y = [int(n) for n in y]
    plt.hist(y, 16, range=(0, 800000))
    plt.show()
    return


if __name__ == "__main__":
    main(datetime.date.today())
