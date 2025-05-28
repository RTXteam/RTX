import logging
import pickle

import numpy as np


def load_data():
    logging.info(f"Features vector is loading")
    x = np.load("X_data.npy")
    logging.info(f"Features vector is loaded")
    logging.info(f"Labels are loading")
    y = np.load("y_data.npy")
    logging.info(f"Labels are loaded")
    with open("group.pkl", "rb") as f:
        group = pickle.load(f)

    return x, y, group
