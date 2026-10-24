import numpy as np
class CustomBipolarPerceptron:
    def __init__(self, input_dim, lr=0.01, epochs=100):
        self.lr = lr
        self.epochs = epochs
        self.weights = np.zeros(input_dim)
        self.bias = 0.0
    def fit(self, X, y):
        y_bipolar = np.where(y == 0, -1, 1)
        for _ in range(self.epochs):
            for xi, yi in zip(X, y_bipolar):
                activation = np.dot(xi, self.weights) + self.bias
                pred = 1 if activation >= 0 else -1
                if pred != yi:
                    self.weights += self.lr * yi * xi
                    self.bias += self.lr * yi
    def predict(self, X):
        activation = np.dot(X, self.weights) + self.bias
        return np.where(activation >= 0, 1, 0)
