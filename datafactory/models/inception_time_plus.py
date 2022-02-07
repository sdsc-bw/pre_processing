'''
Copyright (c) Smart Data Solution Center Baden-Württemberg 2021,
All rights reserved.
'''

import pandas as pd
from typing import cast, Any, Dict, List, Tuple, Optional, Union
from tsai.all import InceptionTimePlus  as InceptionTimePlusTsai

from .model import TsaiModel

class InceptionTimePlus(TsaiModel):
    
    def __init__(self, X: pd.Series, y: pd.Series, model_type: str, params:Dict=dict()):
        self.arch = InceptionTimePlusTsai
        super(InceptionTimePlus, self).__init__(X, y, model_type, params)
        
        self.name = "InceptionTimePlus"
        self.id = "inception_time_plus"