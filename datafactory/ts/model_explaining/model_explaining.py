import numpy as np
import pandas as pd
import random

import lime
import lime.lime_tabular

from sklearn.model_selection import train_test_split

from tqdm import tqdm # Package für Fortschrittanzeige

from sklearn.decomposition import FactorAnalysis
from sklearn.impute import SimpleImputer

from skforecast.ForecasterAutoreg import ForecasterAutoreg

import sys
sys.path.append('../../util')
from ...util.constants import logger  
from ...util.models import _get_model

                                                       
def explain_models(X, y, models, model_type, idx=None):  
    
    logger.info('Start calculation of feature importance...')
        
    feature_names = X.columns
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False)
    X = X.to_numpy()
    X_train = X_train.to_numpy()
    X_test = X_test.to_numpy()
    y_train = y_train.to_numpy()
    y_test = y_test.to_numpy()  
    
    if idx is None:
        idx = random.randint(0, len(X_test) - 1)
    
    explanations = {}
    predictions_train = {}
    predictions_test = {}

    for m in tqdm(models):
        model = _get_model(m, X, y, model_type)
        explanations[m], predictions_train[m], predictions_test[m] = train_and_explain(model, X, X_train, X_test, y_train, y_test, model_type, feature_names, idx=idx)
    
    
    return explanations, predictions_train, predictions_test

def train_and_explain(model, X, X_train, X_test, y_train, y_test, model_type, feature_names, idx=None):
    model.fit(X=X_train, y=y_train)    
    
    if model_type == 'C':
        mode = 'classification'
    elif model_type == 'R':
        mode = 'regression'
    else:
        raise ValueError(f'Unknown type of model: {model_type}')
    
    explainer = lime.lime_tabular.LimeTabularExplainer(X_train, mode=mode, feature_names=feature_names)
    
    explanation = explainer.explain_instance(X[idx], model.predict, num_features=len(feature_names), num_samples=10000)
    
    predictions_train = model.predict(X_train)
    predictions_test = model.predict(X_test)
    
    return explanation, predictions_train, predictions_test
    