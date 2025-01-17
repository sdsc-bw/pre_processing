import pandas as pd #Package zur Tabellenberechnung
from datetime import timedelta #Package zur Verwendung von Daten
import imageio
import base64

import graphviz
from dtreeviz.trees import dtreeviz

from datetime import datetime, timedelta #Package zur Verwendung von Daten

# Packages um Website und Plots zu generieren
from matplotlib import pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import Dash, dcc, html
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform, State

#datafactory
import sys
sys.path.append('../preprocessing')
from ..preprocessing.loading import *
from ..preprocessing.splitting import *
from ..preprocessing.encoding import * # methods for encoding
from ..preprocessing.outlier_detecting import outlier_detection_feature, outlier_detection_dataframe # methods for outlier detection
from ..preprocessing.cleaning import * # methods for data cleaning
from ..preprocessing.validating import * # methods for data checking
from ..plotting.model_plotting import compute_fig_from_df

sys.path.append('../model_training')
from ..model_training.basic_model_training import compare_models

sys.path.append('../model_explaining')
from ..model_explaining.model_explaining import explain_models

sys.path.append('../../util')
from ...util.constants import logger
from ...util.models import *

global APP, DF, SR_OPTIONS, MODEL_PERFORMANCE, FEATURE_IMPORTANCE, PREDICTIONS_TRAIN, PREDICTIONS_TEST

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
APP = DashProxy(__name__, external_stylesheets=external_stylesheets, prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
    
SR_OPTIONS = {'Day(s)': 'days', 'Hour(s)': 'hours', 'Minute(s)': 'minutes', 'Second(s)': 'seconds'}

def run_pipline(data_type: str, model_type, file_path, is_file=True, query: Union[list,str]="""select *""", output_path='./output/', 
                target_feature=None, initial_features=None, sep=',', 
                header: str='infer', index_col: Union[str, int]=0, resample=True, agg='mean', grad=timedelta(hours=1), 
                time_col: Union[str, List]='Time', time_format=None,
                index_start=None, index_end=None, lags=15, sampling_rate=timedelta(days=1), sampling_rate_format='Hour(s)',
                standard_models=['baseline', 'linear', 'decisiontree', 'randomforest', 'adaboost'], 
                standard_metrics=['mean_absolute_error','mean_squared_error'], feature_selection_strategy=None, transformations=None,
                pref=None):
    global APP, FILE_PATH, MODEL_TYPE, OUTPUT_PATH
    
    FILE_PATH = file_path
    MODEL_TYPE = model_type
    OUTPUT_PATH = output_path
    
    # create output directories
    _create_output_directory(output_path)
    
    # load the data
    # TODO do resampling later, after selecting in parameter tab
    input_df = load_dataset(data_type, file_path, is_file=is_file, sep=sep, index_col=index_col, time_col=time_col, time_format=time_format, sampling_rate=sampling_rate, header=header, query=query, agg=agg, index_start=index_start, index_end=index_end, pref=pref)
    
    # basic information
    data_description = _get_statistical_information(output_path, input_df) 
    
    create_layout(input_df, data_description, sampling_rate, sampling_rate_format, standard_models, standard_metrics)
    
    APP.run_server()
    
##################### Basic computations #########################    
def _create_output_directory(output_path):
    if not os.path.isdir(output_path):
        os.mkdir(output_path)
     
    if not os.path.isdir(output_path + '/plots/'):
        os.mkdir(output_path + '/plots/')
    
    if not os.path.isdir(output_path + '/plots/scatter_att/'):
        os.mkdir(output_path + '/plots/scatter_att/')
    
    if not os.path.isdir(output_path + '/plots/scatter_y/'):
        os.mkdir(output_path + '/plots/scatter_y/')
    
    if not os.path.isdir(output_path + '/plots/class_based_distribution/'):
        os.mkdir(output_path + '/plots/class_based_distribution/')
        
    if not os.path.isdir(output_path + '/datasets/'):
        os.mkdir(output_path + '/datasets/')
        
    if not os.path.isdir(output_path + '/feature_importance/'):
        os.mkdir(output_path + '/feature_importance/')
        
def _get_statistical_information(output_path, df):
    data_description = df.describe()
    data_description.to_csv(output_path + '/statistic.csv')
    data_description = pd.read_csv(output_path + '/statistic.csv')
    return data_description

def _get_outlier(output_path, df):
    outlier = outlier_detection_dataframe(df)
    outlier.to_csv(output_path + '/outlier.csv')
    return outlier

def _check_data(output_path, target_col, df, model_type):
    info_file = open(output_path + "/data_report.txt", "w")
    data_numeric, _, y, n_numeric_nan, le_name_mapping, _, flag_wrong_target = check_data_and_distribute(df, model_type=model_type, file=info_file, target_col=target_col)
    info_file.close()
    
    return le_name_mapping

##################### Layout ######################### 

def create_layout(input_df, data_description, sampling_rate, sampling_rate_format, standard_models, standard_metrics):
    #global APP
    APP.layout = html.Div([
        _add_title(),
        dcc.Tabs([
            _add_info_tab(input_df, data_description, sampling_rate, sampling_rate_format),
            _add_parameter_tab(input_df, standard_models, standard_metrics),
            #_add_preprocessed_tab() # add feature corr, scatterplots, ...
            #_add_feature_distribution_tab(), # the trend is added as a sub-tab in distribution tab, TODO !!!
            #_add_feature_correlation_tab(), # two more correlation sub-tabs are add here: self-reg and pcmci TODO !!!
            _add_preprocessing_tab(input_df),
            _add_model_comparison_tab(input_df),
            _add_explanation_tab(input_df),
            #_add_summary_tab(),
            #_add_dt_tab(), # TODO move to explanation tab
            
            
        ])
    ])
    
def _add_title():
    out = html.Div([
        html.H1(f"Data Analysis"),
        html.Hr()
    ])
    
    return out

############## Info-Tab ###########
def _add_info_tab(input_df, data_description, sampling_rate, sampling_rate_format):
    out = dcc.Tab(label='Basic Information', children=[
        dcc.Tabs([
#            __add_task_tab(), # TODO add infos about task
            __add_statistics_tab(data_description),
            #__add_feature_correlation_tab(input_df),
            ___add_corr_tab(input_df),
            ___add_scatter_plot_custom(input_df),
#            __add_scatter_plot_tab(input_df),
#            __add_input_line_plot(input_df, sep, output_path, agg, sampling_rate, sampling_rate_format), # comment in after adding parameter tab
            #__add_outlier_tab(input_df), # TODO add representation of outliers
        ])
    ])
    
    return out

def __add_statistics_tab(data_description):
    out = dcc.Tab(label='Statistics', children=[
        html.H2('Statistics'),
        html.P('Here are the common statistical measurements applied on the numeric features of the dataset.', className='par'),
        add_dataframe_table(data_description),
    ])
    
    return out

def __add_feature_correlation_tab(input_df):
    out = dcc.Tab(label='Correlations', children=[
        dcc.Tabs([
            ___add_corr_tab(input_df),
            ___add_self_regression_tab(), # TODO add self regression !!!!! Seems on wrong place?
            ___add_pcmci_tab() # TODO add pcmci!!!!! only after/before preprocessing bc it takes very long
        ])
    ])
    
    return out

def ___add_corr_tab(input_df):
    df_heatmap_all = input_df.corr()
    df_heatmap = df_heatmap_all.reset_index().melt(id_vars='index').query(f'(value >={99/100})&(value<1)')
    ticks = np.arange(1, 100)
    cols = input_df.columns[:4]
    fig = px.imshow(input_df[cols].corr())
    
    out = dcc.Tab(label='Correlation Matrix', children=[
        html.H2('Correlation Matrix'),
        html.P('Here it shows the correlations between features of the input data. Features with constand or too less values are filtered out.', className='par'),
        dcc.Dropdown(id = 'dropdown_heatmap_input', options = input_df.columns, value = cols, multi=True),
        dcc.Graph(figure=fig, id = 'heatmap_input'),
        html.Div([
            html.P(f'Following feature pairs are over', className='par_corr'),
            dcc.Dropdown(id="dropdown_corr_per_input", options=[{'label': x , 'value': x} for x in ticks], value = 90, multi=False,
                        className='dropdown_corr', clearable=False),
            html.P(f'%'),
            html.P(f'correlated:', className='par_corr'),
        ], className='par_corr'),
        add_dataframe_table(df_heatmap, id='table_corr_per_input'),
    ])
    
    @APP.callback(Output('heatmap_input', 'figure'),
                 Input('dropdown_heatmap_input', 'value'))
    def update_heatmap_chart(cols):
        fig = px.imshow(input_df[cols].corr())
        return fig
    
    @APP.callback(Output('table_corr_per_input', 'data'),
                  Output('table_corr_per_input', 'columns'),
                  Input('dropdown_corr_per_input', 'value'))
    def update_corr_pairs(x):
        df_heatmap = df_heatmap_all.reset_index().melt(id_vars='index').query(f'(value >={int(x)/100})&(value<1)')
        data = df_heatmap.to_dict('records')
        columns = [{'name': i, 'id': i} for i in df_heatmap.columns]
        
        return data, columns
    
    return out

def __add_scatter_plot_tab(input_df):
    out = dcc.Tab(label='Scatter Plots', children=[
        dcc.Tabs([
            ____add_scatter_plot_important_features_tab(input_df),
            ___add_scatter_plot_custom(input_df)
            
        ])
    ])
    
    return out

def ____add_scatter_plot_important_features_tab(input_df):
    # TODO select important features instead of whole DF
    out = dcc.Tab(label='Important Features', children=[
        html.H2('Scatter Plots of Important Features'),
        html.P("A scatter plot displays the values of two features of the dataset. It can show the degree of the correlation between two features. If the points' pattern slopes from lower left to upper right, it indicates a positive correlation. If the pattern of points slopes from upper left to lower right, it indicates a negative correlation.", className='par'),
        html.Div([
            html.Label('X-axis:', className='dropdown_label'),
            dcc.Dropdown(
                id = "dropdown_scatter_important_features1",
                options = [{'label': col, 'value': col} for col in input_df.columns],
                multi = False,
                clearable=False,
                className='dropdown',
                placeholder="Select 1. feature...",
            ),
        ], className='dropdown_with_label'),
        html.Div([
            html.Label('Y-axis:', className='dropdown_label'),
            dcc.Dropdown(
                id = "dropdown_scatter_important_features2",
                options = [{'label': col, 'value': col} for col in input_df.columns],
                multi = False,
                clearable=False,
                className='dropdown',
                placeholder="Select 2. feature...",
            ),
        ], className='dropdown_with_label'),
        dcc.Graph(id="figure_scatter_important_features"),
        
    ])
    
    @APP.callback(Output('figure_scatter_important_features', 'figure'), 
                  [Input('dropdown_scatter_important_features1', 'value'), Input('dropdown_scatter_important_features2', 'value')])
    def _update_scatter_plot_features(feature1, feature2):
        # TODO only use df with important features
        out = px.scatter(input_df, x=feature1, y=feature2, marginal_x="histogram", marginal_y="histogram")
        return out
    
    return out

def ___add_scatter_plot_custom(input_df):
    out = dcc.Tab(label='Scatter Plots', children=[
        html.H2('Scatter Plots of Custom Features'),
        html.P("Here you can create a scatter plot of every column in the dataset.", className='par'),
        html.Div([
            html.Label('X-axis:', className='dropdown_label'),
            dcc.Dropdown(
                id = "dropdown_scatter_custom_features1",
                options = [{'label': col, 'value': col} for col in input_df.columns],
                multi = False,
                clearable=False,
                className='dropdown',
                placeholder="Select 1. feature...",
            ),
        ], className='dropdown_with_label'),
        html.Div([
            html.Label('Y-axis:', className='dropdown_label'),
            dcc.Dropdown(
                id = "dropdown_scatter_custom_features2",
                options = [{'label': col, 'value': col} for col in input_df.columns],
                multi = False,
                clearable=False,
                className='dropdown',
                placeholder="Select 2. feature...",
            ),
        ], className='dropdown_with_label'),
        dcc.Graph(id="figure_scatter_custom_features"),
    ])
    
    @APP.callback(Output('figure_scatter_custom_features', 'figure'), 
                  [Input('dropdown_scatter_custom_features1', 'value'), Input('dropdown_scatter_custom_features2', 'value')])
    def _update_scatter_plot_features(feature1, feature2):
        # TODO only use df with important features
        out = px.scatter(input_df, x=feature1, y=feature2, marginal_x="histogram", marginal_y="histogram")
        return out
    
    return out

############## PCMI Tab ##################

def ___add_pcmi_tab():  # tab to show the pcmci result TODO!!!!!
    """
    it may include:
        - a title
        - a dropdown to select the pcmci parameter, e.g., maximum number of lag
        - a dropdown to select the roll window size, to recalculation time maybe long.....
        - a graph to show the result
    """
    # TODO add
    out = dcc.Tab(label='PCMI Analysis', children=[
        html.H2('PCMI Analysis'),
    ])
    
    return out

############## Self Regression Tab ##################

def ___add_self_regression_tab(): # the new tab to show self regression TODO!!!!
    """
    it may includes:
        - a title
        - a dropdown for feature selection
        - a dropdown for roll window size ? 
        - a graph to show the self regression result
    """
    # TODO add
    out = dcc.Tab(label='Self Regression', children=[
        html.H2('Self Regression'),
    ])
    
    return out

############## Line Plot Tab ##################

def __add_input_line_plot(input_df, sep, output_path, agg, sampling_rate, sampling_rate_format):
    cols = input_df.columns[:2]
    #line plot
    line_fig = go.Figure()
    for i in cols:
        line_fig.add_trace(go.Scatter(x=input_df.index, y=input_df[i], mode='lines', name=i))
        
    # normalized line plot
    norm_line_fig = go.Figure()    
    tmp = (input_df - input_df.mean()) / input_df.std()
    for i in cols:
        norm_line_fig.add_trace(go.Scatter(x=tmp.index, y=tmp[i], mode='lines', name=i))
        
    # resampled line plot
        
    sampling_rate = {SR_OPTIONS[sampling_rate_format]: int(sampling_rate)}
    grad = timedelta(**sampling_rate)

    agg_line_fig = go.Figure()
    for i in cols:
        agg_line_fig.add_trace(go.Scatter(x=tdf.index, y=tdf[i], mode='lines', name=i))
    
    out = dcc.Tab(label='Verlauf', children=[
        html.H2('Verlauf'),
        html.H4('Orginal'),
        html.P('Hier kann der Verlauf der einzelnen Features der Eingabedateien angezeigt. Features mit konstanten oder zu wenig Werten wurden bereits aussortiert.', className='par'),
        dcc.Dropdown(id='dropdown_line_input', options=input_df.columns, value=cols, multi=True),
        dcc.Graph(id='graph_line_input', figure=line_fig),
        html.H4('Mit Normalisierung'),
        html.P('Hier wird der Verlauf nach der Normalisierung angezeigt. Dadurch können leiter Trends oder Zusammenhänge erkannt werde.', className='par'),
        dcc.Graph(id='graph_norm_line_input', figure=norm_line_fig),
        html.H4('Nach Resampling'),
        html.P('Hier wird der Verlauf nach dem Resampling mit der ausgewählten Samplingstrategie angezeigt. Achtung: Wenn das Dataset noch nie berechnet wurde, kann es einige Zeit dauern, bis die Graphik aktualisiert wurde.', className='par'),
        html.Div([
            html.Label('Wähle die Samplingstrategie:', className='dropdown_label'),
            dcc.Dropdown(id='dropdown_agg', options=['mean', 'max', 'min', 'std'], value='mean', className='dropdown'),
        ]),
        html.Div([
            html.Label('Wähle die Samplingrate:', className='dropdown_label'),
            html.Div([
                dcc.Input(id="input_sr", type="text", value=1, className='dropdown'),
                dcc.Dropdown(id='dropdown_sr', options=list(SR_OPTIONS.keys()), value='Stunde(n)', className='dropdown'),
             ]),
            html.Button('Compute', id='compute_resampling_button', n_clicks=0),
        ]),
        dcc.Graph(id='graph_agg_line_input', figure=agg_line_fig),
    
    ])
    
    @APP.callback(Output('graph_line_input', 'figure'),
                  Output('graph_norm_line_input', 'figure'),
                  Output('graph_agg_line_input', 'figure'),
                  Input('dropdown_line_input', 'value'),
                  Input('dropdown_agg', 'value'),
                  State('input_sr', 'value'),
                  State('dropdown_sr', 'value'), 
                  Input('compute_resampling_button', 'n_clicks'))
    def update_line_chart(cols, agg, sampling_rate, sampling_rate_format, n_clicks):
        
        #line plot
        line_fig = go.Figure()
        for i in cols:
            line_fig.add_trace(go.Scatter(x=input_df.index, y=input_df[i], mode='lines', name=i))
        
        # normalized line plot
        norm_line_fig = go.Figure()    
        tmp = (input_df - input_df.mean()) / input_df.std()
        for i in cols:
            norm_line_fig.add_trace(go.Scatter(x=tmp.index, y=tmp[i], mode='lines', name=i))
        
        # resampled line plot
        
        sampling_rate = {SR_OPTIONS[sampling_rate_format]: int(sampling_rate)}
        grad = timedelta(**sampling_rate)

        _, tdf, _ = combine_df_and_save(input_dfs, grad=grad, sep=sep, agg=agg, locations=locations, output_path=output_path)

        agg_line_fig = go.Figure()
        for i in cols:
            agg_line_fig.add_trace(go.Scatter(x=tdf.index, y=tdf[i], mode='lines', name=i))

        return line_fig, norm_line_fig, agg_line_fig
        
    
    return out

############## Outlier Tab ##################

def __add_outlier_tab(input_df): # TODO add repräsentation of outliers
    outliers = _get_outlier(OUTPUT_PATH, input_df)
    
    out = dcc.Tab(label='Outlier', children=[
        html.H2('Outlier'),
    ])
    
    return out

########### Parameter Tab ##################

def _add_parameter_tab(input_df, models, metrics):
    options = list(input_df.columns)
    target_value = input_df.columns[-1]
    
    available_models, available_scorings, available_averages = get_available_models_and_metrics(MODEL_TYPE)
    
    out = dcc.Tab(label='Parameter', children=[
        html.H2('Parameter'),
        html.P('Here you can define the parameters for the computations.', className='par'),
        
        html.H4('Target'),
        html.Label('Select the target:', className='dropdown_label'),
        dcc.Dropdown(id='dropdown_target_par', options=options, value=target_value, multi=False, className='dropdown_with_label'),
        
#        html.H4('Feature Selection'),
#        html.Label('Select strategies for the feature selection:'),
#        dcc.RadioItems(options=['Manual', 'Factor Analysis', 'K-Best', 'Precentile', 'Generic Univariate Select', 'Recursive Feature Elimination', 'Recursive Feature Elimination with Cross Validation', 'Model Selection'], value='Manual', id='checkbox_feature_par'),
#        html.Div([
#            html.H6('Manual'),
#            html.Div([
#                html.Label('Select the features:', className='dropdown_label'),
#                dcc.Dropdown(id = 'dropdown_features_par', options=options, value=options, multi=True, className='dropdown_with_label'),
#            ]),
#        ], id='div_manual', className='div_hidden'),
#        html.Div([
#            html.H6('Factor Analysis'),
#            html.Div([
#                html.Label('Select the number of components:', className='dropdown_label'),
#                dcc.Input(id="input_fa_par", type="text", value=5, className='dropdown_component'),
#            ]),
#        ], id='div_factor_analysis', className='div_hidden'),
#        html.Div([
#            html.H6('K-Best'),
#            html.Div([
#               html.Label('Select k:', className='dropdown_label'),
#               dcc.Input(id="input_k_par", type="text", value=5, className='dropdown_component'),
#           ]),
#       ], id='div_k_best', className='div_hidden'),
#       # TODO add rest divs of the options
        
#        html.H4('Preprocessing'),
#        html.Label('Select strategies for the preprocessing:'),
#        dcc.Checklist(options=['Resampling'], value=[], id='checkbox_prep_par'),
#        html.Div([
#             html.H6('Resampling'),
 #            html.Div([
 #                html.Label('Select the sampling strategy:', className='dropdown_label'),
 #                dcc.Dropdown(id='dropdown_agg_par', options=['mean', 'max', 'min', 'std'], value='mean', className='dropdown'),
 #            ]),
 #            html.Div([
 #                html.Label('Select the sampling rate:', className='dropdown_label'),
 #                html.Div([
 #                    dcc.Input(id="input_sr_par", type="text", value=1, className='dropdown'),
 #                    dcc.Dropdown(id='dropdown_grad_par', options=list(SR_OPTIONS.keys()), value='Hour(s)', className='dropdown'),
 #                ]),
 #            ]),
#        ], id='div_resampling_par', className='div_hidden'),
        # TODO add rest divs of the options
        
        html.H4('Modelle'),
        html.Label('Select the models:', className='dropdown_label'),
        dcc.Dropdown(id="dropdown_models_par", options=available_models, 
                     value=[model['value'] for model in available_models], multi=True, className='dropdown_with_label'),
        html.Label('Select a scoring for the evaluation:', className='dropdown_label'),
        dcc.Dropdown(id="dropdown_scoring_par", options=available_scorings, 
                     value=available_scorings, multi=True, className='dropdown_with_label'),
        html.Label('Select an average to the scoring:', className='dropdown_label'),
        dcc.Dropdown(id="dropdown_average_par", options=available_averages, 
                     value=available_averages[2], multi=False, className='dropdown_with_label'),
        
        html.Button('Compute', id='compute_button', n_clicks=0),
    ])
        
    
    @APP.callback(Output('div_resampling_par', 'style'),
                 Input('checkbox_prep_par', 'value'))
    def show_hide_resampling(checked):
        if 'Resampling' in checked:
            return {'display': 'block'}
        else:
            return {'display': 'none'}
       
    @APP.callback(Output('div_manual', 'style'),
                 Input('checkbox_prep_par', 'value'))
    def show_hide_resampling(checked):
        if 'Manual' in checked:
            return {'display': 'block'}
        else:
            return {'display': 'none'}
        
    @APP.callback(Output('div_factor_analysis', 'style'),
                 Input('checkbox_feature_par', 'value'))
    def show_hide_factor_analysis(checked):
        if 'Factor Analysis' in checked:
            return {'display': 'block'}
        else:
            return {'display': 'none'}
        
    @APP.callback(Output('div_k_best', 'style'),
                 Input('checkbox_feature_par', 'value'))
    def show_hide_factor_analysis(checked):
        if 'K-Best' in checked:
            return {'display': 'block'}
        else:
            return {'display': 'none'}
    
    return out

######################### Explanation Tab #########################

def _add_explanation_tab(input_df):
    
    out = dcc.Tab(label='Model Explanations', children=[
        html.H2('Model Explanation'),
        html.P('Here you can see the importance of each feature of the selected model for a random sample.', className='par'),
        html.Label('Select a model:', className='dropdown_label'),
        dcc.Dropdown(id="dropdown_model_exp", multi = False, className='dropdown_with_label'),
        html.Label('Select an index to explain:', className='input_label'),
        dcc.Input(id="input_exp_idx", type='number', className='input_with_label'),
        html.Button('Explain', id='explain_button', n_clicks=0),       
        dcc.Graph(id='graph_predictions'),
        html.Img(id='graph_lime'),
    ])
    
    #
    @APP.callback(Output('graph_lime', 'src'),
                  Output('dropdown_model_exp', 'options'),
                  Output('dropdown_model_exp', 'value'),
                  Output('graph_predictions', 'figure'),
                  Output('input_exp_idx', 'value'),
#                  State('checkbox_feature_par', 'value'), # TODO add parameters parametertab
#                  State('checkbox_prep_par', 'value'),
#                  State('input_fa_par', 'value'),  
#                  State('dropdown_agg_par', 'value'),                
#                  State('input_sr_par', 'value'),
#                  State('dropdown_grad_par', 'value'),
 #                 State('dropdown_features_par', 'value'),
                  State('dropdown_target_par', 'value'),
                  State('dropdown_models_par', 'value'),
                  State('dropdown_model_exp', 'value'),
                  State('input_exp_idx', 'value'),
                  Input('compute_button', 'n_clicks'), 
                  Input('explain_button', 'n_clicks'))
    def update_explanation_tab(target, models, curr_model_exp, idx, n_clicks_compute, n_clicks_explain):   
        options = sorted([m for m in get_models_from_list(MODEL_TYPE, models_values=models)], key=lambda m: m['label'])
        # TODO edit function so that baseline is also explainable
        if {'label': 'Baseline', 'value': 'baseline_ts'} in options:
            options.remove({'label': 'Baseline', 'value': 'baseline_ts'})
            models.remove('baseline_ts')
        curr_option = options[0]['value']
        
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
        if idx is None or idx == '':
            idx = random.randint(0, len(X) - 1)
            
        
        # compute feature importance an prediction of models
        global FEATURE_IMPORTANCE, PREDICTIONS_TRAIN, PREDICTIONS_TEST
        FEATURE_IMPORTANCE, PREDICTIONS_TRAIN, PREDICTIONS_TEST = explain_models(X, y, models, MODEL_TYPE, idx=idx)
        
        # plot predictions
        fig_pred = plot_predictions(PREDICTIONS_TRAIN[curr_option], PREDICTIONS_TEST[curr_option], y)
        
        # plot feature importance        
        fi = FEATURE_IMPORTANCE[curr_option].as_pyplot_figure()
        plt.savefig(OUTPUT_PATH + '/feature_importance/' + curr_option + '.png', bbox_inches='tight')
        fi_fig = base64.b64encode(open(OUTPUT_PATH + '/feature_importance/' + curr_option + '.png', 'rb').read()).decode('ascii')
        fi_src = 'data:image/png;base64,{}'.format(fi_fig)
        
        return fi_src, options, curr_option, fig_pred, idx
    
        
    @APP.callback(Output('graph_lime', 'src'),
                  Input('dropdown_model_exp', 'value'))
    def update_fi_fig(curr_model):
        fi = FEATURE_IMPORTANCE[curr_model].as_pyplot_figure()
        plt.savefig(OUTPUT_PATH + '/feature_importance/' + curr_model + '.png', bbox_inches='tight')
        fig = base64.b64encode(open(OUTPUT_PATH + '/feature_importance/' + curr_model + '.png', 'rb').read()).decode('ascii')
        src = 'data:image/png;base64,{}'.format(fig)
        return src

    @APP.callback(Output('graph_predictions', 'figure'),
                  State('dropdown_target_par', 'value'),
                  Input('dropdown_model_exp', 'value'))
    def update_pred_fig(target, curr_model):
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        _, y = split_X_y(input_df, target)
        fig = plot_predictions(PREDICTIONS_TRAIN[curr_model], PREDICTIONS_TEST[curr_model], y)
        return fig
    
    @APP.callback(Output('input_exp_idx', 'value'),
                  Input('graph_predictions', 'clickData'))
    def update_pred_fig(clickData):
        idx = clickData['points'][0]['x']
        return idx
    
    return out

###################### Preprocessing Tab ########################

def _add_preprocessing_tab(input_df):
    
    out = dcc.Tab(label='Preprocessing', children=[
        dcc.Tabs([
            #__add_violin_distribution_tab(input_df),
            ___add_violin_distribution_custom(input_df),
            #__add_feature_correlation_after_processing_tab(input_df),
            ___add_corr_after_processing_tab(input_df),
            #__add_outlier_after_processing_tab(input_df),
            
        ])
    ])
    
    return out

############## Violin Distribution ##################

def __add_violin_distribution_tab(input_df):
    if MODEL_TYPE == 'C':
        out = dcc.Tab(label='Violin Distributions', children=[
            dcc.Tabs([
                ___add_violin_distribution_important_features(input_df),
#                ___add_violin_distribution_class_based(input_df),
                ___add_violin_distribution_custom(input_df)
            ])
        ])
    else:
        out = dcc.Tab(label='Violin Distributions', children=[
            dcc.Tabs([
                ___add_violin_distribution_important_features(input_df),
                ___add_violin_distribution_custom(input_df)
            ])
        ])
    
    return out

def ___add_violin_distribution_important_features(input_df):
    out = dcc.Tab(label='Important Features', children=[
        html.H4('Violin Distribution of Important Features'),
        html.P("This violin plot shows the probability density of the important features. It also contains a marker for the statistical metrics.", className='par'),
        dcc.Dropdown(
            id = "dropdown_violin_features",
            multi = True,
        ),
        dcc.Graph(id="figure_violin_features"),
    ])
    
    @APP.callback(Output('dropdown_violin_features', 'options'),
                  Output('dropdown_violin_features', 'value'),
#                  State('checkbox_feature_par', 'value'), # TODO add parameters parametertab
#                  State('checkbox_prep_par', 'value'),
#                  State('input_fa_par', 'value'),  
#                  State('dropdown_agg_par', 'value'),                
#                  State('input_sr_par', 'value'),
#                  State('dropdown_grad_par', 'value'),
 #                 State('dropdown_features_par', 'value'),
                  State('dropdown_target_par', 'value'),
                  Input('compute_button', 'n_clicks'))
    def update_violin_distribution_important_features_tab(target, n_clicks):   
        
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
        options = [{'label': col, 'value': col} for col in X.columns]
        value = X.columns[:2]
        
        return options, value
    
    @APP.callback(Output('figure_violin_features', 'figure'),
                  State('dropdown_target_par', 'value'),
                  Input('dropdown_violin_features', 'value'))
    def _update_violin_plot_features(target, values):
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
        df = X[values] # TODO also only use important features
        out = plot_violin_distribution(df)
        return out
    
    return out

def ___add_violin_distribution_class_based():
    if MODEL_TYPE == 'C':
        out = dcc.Tab(label='Class-based', children=[
            html.H4('Class-based Violin Distribution'),
            html.P("This violin plot shows the probability density of every feature based on the classes. These classes will be useful for classification tasks if the distribution of the same attributes varies widely across classes", className='par'),
            html.Label('Feature:', className='dropdown_label'),
            dcc.Dropdown(
                id = "dropdown_class_based_violin_features",
                options = [{'label': col, 'value': col} for col in X.columns],
                value = X.columns[0],
                multi = False,
                clearable=False,
                className='dropdown',
                placeholder="Select a feature...",
            ),
            dcc.Graph(id="figure_class_based_violin_features"),
        ])
    else:
        out = None
        
    @app.callback(Output('figure_class_based_violin_features', 'figure'),
                 [Input('dropdown_class_based_violin_features', 'value')])
    def _update_class_based_violin_plot_features(value):
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
#        le_name_mapping = _check_data() # TODO does le_name_mapping and check data still makes sense after different function for preprocessing?
        
        df = X[values]
        out = get_class_based_violin_distribution(X, y, value, le_name_mapping, OUTPUT_PATH)

        return out    
        
    return out

def ___add_violin_distribution_custom(input_df):
    out = dcc.Tab(label='Violin Distribution', children=[
        html.H4('Violin Distribution of Custom Features'),
        html.P("This violin plot shows the probability density of every feature.", className='par'),
        dcc.Dropdown(
            id = "dropdown_violin_custom_features",
            multi = True,
        ),
        dcc.Graph(id="figure_violin_custom_features"),
    ])
    
    @APP.callback(Output('dropdown_violin_custom_features', 'options'),
                  Output('dropdown_violin_custom_features', 'value'),
#                  State('checkbox_feature_par', 'value'), # TODO add parameters parametertab
#                  State('checkbox_prep_par', 'value'),
#                  State('input_fa_par', 'value'),  
#                  State('dropdown_agg_par', 'value'),                
#                  State('input_sr_par', 'value'),
#                  State('dropdown_grad_par', 'value'),
 #                 State('dropdown_features_par', 'value'),
                  State('dropdown_target_par', 'value'),
                  Input('compute_button', 'n_clicks'))
    def update_violin_distribution_important_features_tab(target, n_clicks):   
        
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
        options = [{'label': col, 'value': col} for col in X.columns]
        value = X.columns[:2]
        
        return options, value
    
    @APP.callback(Output('figure_violin_custom_features', 'figure'),
                  State('dropdown_target_par', 'value'),
                  Input('dropdown_violin_custom_features', 'value'))
    def _update_violin_plot_custom_features(target, values):
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
        df = X[values]
        out = plot_violin_distribution(df)
        return out
    
    return out


############## Korrelations after Processing ##################

def __add_feature_correlation_after_processing_tab(input_df):
    out = dcc.Tab(label='Correlations', children=[
        dcc.Tabs([
            ___add_corr_after_processing_tab(input_df),
            #___add_pcmi_tab() # TODO add pcmci!!!!! only after/before preprocessing bc it takes very long
        ])
    ])
    
    return out

def ___add_corr_after_processing_tab(input_df):
#    df_heatmap_all = input_df.corr()
#    df_heatmap = df_heatmap_all.reset_index().melt(id_vars='index').query(f'(value >={99/100})&(value<1)')
    ticks = np.arange(1, 100)
#    cols = input_df.columns[:4]
#    fig = px.imshow(input_df[cols].corr())
    
    out = dcc.Tab(label='Correlation Matrix', children=[
        html.H2('Correlation Matrix'),
        html.P('Here it shows the correlations between features of the input data. Features with constand or too less values are filtered out.', className='par'),
        dcc.Dropdown(id='dropdown_heatmap_after_processing_input', multi=True),
        dcc.Graph(id='heatmap_after_processing_input'),
        html.Div([
            html.P(f'Following feature pairs are over', className='par_corr'),
            dcc.Dropdown(id="dropdown_corr_after_processing_input", options=[{'label': x , 'value': x} for x in ticks], value=90, multi=False,
                        className='dropdown_corr', clearable=False),
            html.P(f'%'),
            html.P(f'correlated:', className='par_corr'),
        ], className='par_corr'),
        html.Div([        
            dash.dash_table.DataTable(id='table_corr_after_processing_input'),
        ], className='table'),
    ])
    
    @APP.callback(Output('dropdown_heatmap_after_processing_input', 'options'),
                  Output('dropdown_heatmap_after_processing_input', 'value'),
                  Output('dropdown_corr_after_processing_input', 'value'),
#                  State('checkbox_feature_par', 'value'), # TODO add parameters parametertab especially selected features
#                  State('checkbox_prep_par', 'value'),
#                  State('input_fa_par', 'value'),  
#                  State('dropdown_agg_par', 'value'),                
#                  State('input_sr_par', 'value'),
#                  State('dropdown_grad_par', 'value'),
 #                 State('dropdown_features_par', 'value'),
#                  State('dropdown_heatmap_after_processing_input', 'value'),
                  Input('compute_button', 'n_clicks'))
    def update_corr_after_processing_tab(n_clicks):           
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        output_df = input_df
        
        options = [{'label': col, 'value': col} for col in output_df.columns]
        value = output_df.columns[:4]
        
        return options, value, 90
    
    @APP.callback(Output('heatmap_after_processing_input', 'figure'),
                 Input('dropdown_heatmap_after_processing_input', 'value'))
    def update_heatmap_chart(cols):
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        output_df = input_df
        
        fig = px.imshow(output_df[cols].corr())
        return fig
    
    @APP.callback(Output('table_corr_after_processing_input', 'data'),
                  Output('table_corr_after_processing_input', 'columns'),
                  Input('dropdown_corr_after_processing_input', 'value'))
    def update_corr_pairs(x):
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        output_df = input_df
        
        df_heatmap = input_df.corr()
        df_heatmap = df_heatmap.reset_index().melt(id_vars='index').query(f'(value >={int(x)/100})&(value<1)')
        data = df_heatmap.to_dict('records')
        columns = [{'name': i, 'id': i} for i in df_heatmap.columns]
        
        return data, columns
    
    return out

############## Outlier Tab after Processing ##################

def __add_outlier_after_processing_tab(input_df): # TODO add representation of outliers
    
    out = dcc.Tab(label='Outlier', children=[
        html.H2('Outlier'),
    ])
    
    return out

###################### Model Tab ########################

def _add_model_comparison_tab(input_df):
    
    out = dcc.Tab(label='Model Comparison', children=[
        html.H2('Modell Comparison'),
        html.P("Here you can see the performance of the models on the given task", className='par'),
        dcc.Dropdown(id = "dropdown_models", multi = True),
        dcc.Graph(id = "fig_basic_model_comparison"),
    ])
    
   
    @APP.callback(Output('fig_basic_model_comparison', 'figure'),
                  Output('dropdown_models', 'options'),
                  Output('dropdown_models', 'value'),
#                  State('checkbox_par', 'value'), # TODO add parameters parametertab
#                  State('input_fa_par', 'value'),  
#                  State('dropdown_agg_par', 'value'),                
#                  State('input_sr_par', 'value'),
#                  State('dropdown_grad_par', 'value'),
#                  State('dropdown_features_par', 'value'),
                  State('dropdown_target_par', 'value'),
                  State('dropdown_models_par', 'value'),
                  State('dropdown_scoring_par', 'value'),
                  State('dropdown_average_par', 'value'),
                  Input('compute_button', 'n_clicks'))
    def update_model_tab(target, models, scoring, average, n_clicks):   
        options = sorted([m for m in get_models_from_list(MODEL_TYPE, models_values=models)], key=lambda m: m['label'])
        curr_option = [m['value'] for m in options]
        
        # TODO do preprocessing with callback params (also find a way to avoid doing this in every callback)
        # TDO add strategy parameter and lags in parameter tab and give them to split function
        X, y = split_X_y(input_df, target)
        
        global MODEL_PERFORMANCE
        # TODO add cv param
        MODEL_PERFORMANCE = compare_models(X, y, models, MODEL_TYPE, scoring, average)
        fig = compute_fig_from_df(MODEL_PERFORMANCE)
        
        return fig, options, curr_option 
        
    @APP.callback(Output('fig_basic_model_comparison', 'figure'),
                  Input('dropdown_models', 'value'))
    def update_model_fig(models):    
        global MODEL_PERFORMANCE
        models = get_labels_from_values(MODEL_TYPE, models)
        tmp_model_peformance = MODEL_PERFORMANCE[MODEL_PERFORMANCE['model'].isin(models)]
        fig = compute_fig_from_df(tmp_model_peformance)
        
        return fig
    
    return out

###################### Summary Tab ########################

def _add_summary_tab():
    
    out = dcc.Tab(label='Summary', children=[
        html.H2('Summary'),
    ])
    
   
    
    return out

######################### Helper #########################

def add_dataframe_table(df: pd.DataFrame, id=None, className='table'):
    """
    display a dataframe with dash
    =============
    Parameter
    =============
    df, type of DataFrame
        the target dataframe to display with dash
    width, type of str
        the width of the displayed table, in form of number+px, e.g., 100px
    height, type of str
        the height of the displayed table
    """
    if id:
        out = html.Div([        
            dash.dash_table.DataTable(df.to_dict('records'),[{'name': i, 'id': i} for i in df.columns], id=id),
        ], className=className)
    else:
        out = html.Div([        
            dash.dash_table.DataTable(df.to_dict('records'),[{'name': i, 'id': i} for i in df.columns]),
        ], className=className)
    return out

def plot_predictions(pred_train, pred_test, y):
    fig = go.Figure()
    x = list(range(len(y)))
    x_test = list(range(len(pred_train), len(y)))
    x_train = list(range(len(pred_train)))
    
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='real'))
    fig.add_trace(go.Scatter(x=x_train, y=pred_train, mode='lines', name='Train-prediction'))
    fig.add_trace(go.Scatter(x=x_test, y=pred_test, mode='lines', name='Test-prediction'))

    return fig

def plot_feature_importance(feature_importance):
    feature_importance = feature_importance.sort_values(by=['importance'], ascending=False).head(20)
    
    trace1 = go.Bar(
        x = feature_importance['feature'],
        y = feature_importance['importance'],
        )

    data = [trace1]
    fig = go.Figure(data=data)
    return fig

def plot_violin_distribution(df, output_path=None):
    # TODO move to df + split in computation and visualization
    tmp = (df-df.mean())/df.std()
    tmp2 = []

    for i in tmp.columns:
        tmp3 = pd.DataFrame(columns = ['value', 'fname'])
        tmp3['value'] = tmp[i].values
        tmp3['fname'] = i#[i for j in range(tmp3.shape[0])]

        tmp2.append(tmp3)

    violin_distribution = pd.concat(tmp2, axis=0)
    
    fig = go.Figure()
    for i in df.columns:
        fig.add_trace(go.Violin(y=violin_distribution['value'][violin_distribution['fname'] == i], x= violin_distribution['fname'][violin_distribution['fname'] == i],
              name = i,
              box_visible=True, 
              #line_color='black',
              meanline_visible=True, #fillcolor='lightseagreen', 
              #opacity=0.6
              ))
    
    if output_path:
        fig.write_image(output_path + '/plots/violin_features.webp')
        
    return fig

def plot_class_based_violin_distribution(X, y, col, le_name_mapping, output_path=None):
    # TODO move to df + split in computation and visualization
    inv_le_name_mapping = {}
    for i, j in le_name_mapping.items():
        inv_le_name_mapping[j] = i
    fig = go.Figure()

    for i in inv_le_name_mapping.keys():
        fig.add_trace(go.Violin(y=X[col][y == i], 
                                x= pd.Series(y[y == i]).map(lambda x: inv_le_name_mapping[x]),
                                name = inv_le_name_mapping[i],
                                box_visible=True, 
                                points='all',
                                #line_color='black',
                                meanline_visible=True, 
                                #fillcolor='lightseagreen', 
                                #legendgroup='group',
                                showlegend=True))

    if output_path:
        fig.write_image(output_path + '/plots/class_based_distribution/' + col.replace('/', '') + '.webp')
    
    return fig