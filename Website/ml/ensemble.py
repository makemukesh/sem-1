"""Inference wrapper for the trained RainVision blended ensemble."""

import numpy as np


class RainVisionEnsembleRegressor:
    def __init__(self, rf, gb, rf_weight=0.60, gb_weight=0.40):
        self.rf = rf
        self.gb = gb
        self.rf_weight = rf_weight
        self.gb_weight = gb_weight

    def predict(self, X):
        rf_prediction = np.clip(self.rf.predict(X), 0.0, None)
        gb_prediction = np.clip(self.gb.predict(X), 0.0, None)
        return np.clip(
            self.rf_weight * rf_prediction + self.gb_weight * gb_prediction,
            0.0,
            None
        )
