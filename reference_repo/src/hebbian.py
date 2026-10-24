import numpy as np
class BipolarHebbianClassifier:
    def __init__(self, input_dim):
        self.weights = np.zeros(input_dim)
        self.bias = 0.0
    def fit(self, X, y):
        y_bipolar = np.where(y == 0, -1, 1)
        for xi, yi in zip(X, y_bipolar):
            self.weights += xi * yi
            self.bias += yi
    def predict_score(self, X):
        return np.dot(X, self.weights) + self.bias
    def predict(self, X):
        return np.where(self.predict_score(X) >= 0, 1, 0)
