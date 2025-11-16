import logging
import pickle

import numpy as np


def load_data(data_source):
    logging.info(f"Features vector is loading")
    x = np.load(f"{data_source}X_data.npy")
    logging.info(f"Features vector is loaded")
    logging.info(f"Labels are loading")
    y = np.load(f"{data_source}y_data.npy")
    logging.info(f"Labels are loaded")
    with open(f"{data_source}group.pkl", "rb") as f:
        group = pickle.load(f)

    return x, y, group
