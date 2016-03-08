"""
Non-negative Matrix Factorization algorithms.
Many can be unified under a single framework based on multiplicative updates.
Implementation is inspired by NMFlib by Graham Grindlay
Currently implemented as processor for flexibility, so W and H are not kept in the object, the user is supposed to manage them.
"""
import numpy as np
from untwist.base.algorithms import Processor
from untwist.data import audio

eps = np.spacing(1)

class NMF(Processor):
    
    def __init__(self, rank, update_func = "kl", iterations = 100, 
        threshold = None, W_norm = 2, H_norm = 0, 
        update_W = True, update_H = True, return_divergence = False, beta = 0):

        self.rank = rank
        self.update = getattr(self, update_func + "_updates")
        self.iterations = iterations
        self.threshold = threshold
        self.W_norm = W_norm
        self.H_norm = H_norm
        self.update_W = update_W
        self.update_H = update_H
        self.compute_divergence = threshold != None or return_divergence 
        self.beta = beta

    """
    Compute divergence between reconstruction and original
    """    
        
    def divergence(self, V, W, H):
        R = np.maximum(np.dot(W,H), eps)
        V = np.maximum(V, eps)
        err = 0
        if self.update == self.kl_updates:
            err = np.sum(np.multiply(V, np.log(V/R)) - V + R)
        elif self.update == self.euc_updates:
            err = np.sum((V - np.dot(W,H)) ** 2)
        elif self.update == self.is_updates:
            err = np.sum(V/R - np.log(V/R) - 1)
        elif self.update == self.beta_updates:
            err = (np.sum(V ** self.beta + (self.beta -1) * R ** self.beta
                  - self.beta * V * R ** (self.beta - 1)) 
                  / (self.beta * (self.beta - 1)))
        return err


    """
    Normalize marix (W or H)
    """    
        
    def normalize(self, X, p, axis):        
        if p == 1:
            norm = np.sum(X, axis)
        elif p == 2:
            norm = np.sqrt(np.sum(np.square(X), axis))
        else: return X
        norm[norm == 0] = 1.0
        return X / norm

    """
    Initialize and compute multiplicative updates iterations
    """                
    def process(self, V, W0 = None, H0 = None):
         W = W0 if W0 is not None else np.random.rand(V.shape[0], self.rank) + eps
         H = H0 if H0 is not None else np.random.rand(self.rank, V.shape[1]) + eps
         err = []
         self.ones = np.ones(V.shape)
         W = self.normalize(W, self.W_norm, 0)
         H = self.normalize(H, self.H_norm, 1)
         
         for i in range(self.iterations):
             [V, W, H] = self.update(V, W, H)
             if self.compute_divergence:
                 err.append(self.divergence(V, W, H))
                 if self.threshold is not None and err[-1] <= self.threshold:
                     return [W, H, err]
         return [W, H, err]

    """
    Multiplicative updates functions
    """    


    """
    Optimize Euclidean distance
    """    
    def euc_updates(self, V, W, H):        
        if self.update_W:            
            W  *= np.dot(V, H.T) / (np.dot(W, np.dot(H, H.T)) + eps)
            W = self.normalize(W, self.W_norm, 0)

        if self.update_H:            
            H  *= np.dot(W.T, V) / (np.dot(np.dot(W.T, W), H) + eps)
            H = self.normalize(H, self.H_norm, 1)
            
        return [V, W, H]


         
    """
    Optimize Kullback-Leibler divergence
    """    
    def kl_updates(self, V, W, H):
        
        if self.update_W:
            W  *= np.dot(V / (np.dot(W, H) + eps) , H.T) / np.maximum(np.dot(self.ones, H.T), eps)            
            W = self.normalize(W, self.W_norm, 0)

        if self.update_H:             
            H  *= np.dot(W.T, V / (np.dot(W, H ) + eps)) / np.maximum(np.dot(W.T, self.ones), eps)
            H = self.normalize(H, self.H_norm, 1)

        return [V, W, H]

    """
    Optimize B-divergence
    """
    def beta_updates(self, V, W, H):        
        if self.update_W:
            R = np.maximum(np.dot(W,H), eps)            
            W *= (np.dot(R ** (self.beta - 2) * V, H.T)  / 
                np.maximum(np.dot(R ** (self.beta -1), H.T), eps))
            W = self.normalize(W, self.W_norm, 0)
        
        if self.update_H:
            R = np.maximum(np.dot(W,H), eps)                        
            H *= (np.dot(W.T, R ** (self.beta -2) * V) / 
                np.maximum(np.dot(W.T, R ** (self.beta -1)), eps))
            H = self.normalize(H, self.H_norm, 1)

        return [V, W, H]
        
    """
    Optimize Itakura-Saito divergence
    """    
    def is_updates(self, V, W, H):
        self.beta = 0
        return self.beta_updates(V, W, H)