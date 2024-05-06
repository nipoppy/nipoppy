import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from nilearn import plotting
import pandas as pd
import networkx as nx
import os
import warnings

# warnings.simplefilter('ignore')

##########################################################################################

### paths to files
# # local
# FC_root = '/Users/mte/Documents/McGill/JB/QPN/output'
# manifest_path = '/Users/mte/Documents/McGill/JB/QPN/output/demographics.csv'
# output_root = '/Users/mte/Documents/McGill/JB/QPN/result_outputs'

# BIC
FC_root = '/data/origami/mohammad/QPN/output/'
manifest_path = '/data/pd/qpn/tabular/demographics/demographics.csv'
output_root = '/data/origami/mohammad/QPN/results'

### parameters
session_id = 'ses-01'
task = 'task-rest'
space = 'space-MNI152NLin2009cAsym_res-2'
brain_atlas_list = [
    "schaefer_100",
    "schaefer_200", 
    "schaefer_300",
    "schaefer_400", 
    "schaefer_500",
    "schaefer_600", 
    "schaefer_800",
    "schaefer_1000",
    # "DKT",
]

manifest_id_key = "participant_id"
manifest_diagnosis_key = 'group_at_screening'
PD_label = "PD   (Parkinson's Disease)/Maladie de Parkinson"
CTRL_label = "Healthy control/Contrôle"

metric = 'correlation' # correlation , covariance , precision 
graph_prop_list = ['degree', 'communicability', 'shortest_path', 'clustering_coef']
graph_prop_threshold_list = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

reorder_conn_mat = False

# plotting parameters
save_image = True
fix_lim = False # if True, the colorbar will be fixed to (-1, 1) for all plot_FC
fig_dpi = 120
fig_bbox_inches = 'tight'
fig_pad = 0.1
show_title = False
save_fig_format = 'png'

##########################################################################################

######### functions #########

def plot_FC(
        FC,
        roi_labels=None,
        title='',
        reorder=False,
        fix_lim=False,
        save_image=False, output_root=None
    ):
    '''
    
    '''
    figsize = (10, 8)

    # set vmax and vmin
    if fix_lim:
        vmax = 1
        vmin = -1
    else:
        vmax = np.max(np.abs(FC))
        vmin = -1 * vmax
    
    plotting.plot_matrix(
        FC, figure=figsize, labels=roi_labels,
        vmax=vmax, vmin=vmin,
        reorder=reorder
    )

    if show_title:
        plt.suptitle(title, fontsize=15)

    if save_image:
        folder = output_root[:output_root.rfind('/')]
        if not os.path.exists(folder):
            os.makedirs(folder)
        plt.savefig(output_root+title+'.'+save_fig_format, 
            dpi=fig_dpi, bbox_inches=fig_bbox_inches, pad_inches=fig_pad, format=save_fig_format
        ) 
        plt.close()
    else:
        plt.show()

def cat_plot(data, 
    x=None, y=None, 
    hue=None,
    title='',
    save_image=False, output_root=None
    ):
    '''
    data is a dictionary with different vars as keys 
    '''

    sns.set_context("paper", 
        font_scale=1.0, 
        rc={"lines.linewidth": 1.0}
    )

    n_columns = len(data)

    fig_width = n_columns * 6
    fig_height = 6
    fig, axs = plt.subplots(1, n_columns, figsize=(fig_width, fig_height), 
        facecolor='w', edgecolor='k', sharex=False, sharey=False)

    for i, key in enumerate(data):

        if key=="communicability":
            log_scale = True
        else:
            log_scale = False

        df = pd.DataFrame(data[key])
        sns.violinplot(ax=axs[i], data=df, x=x, y=y, hue=hue, width=0.5, split=True, alpha=0.75, log_scale=log_scale)
        sns.stripplot(ax=axs[i], data=df, x=x, y=y, hue=hue, alpha=1, dodge=True, legend=False)
        
        axs[i].set(xlabel=None)
        axs[i].set(ylabel=None)
        axs[i].set_title(key)
    
    if show_title:
        plt.suptitle(title, fontsize=15)

    if save_image:
        folder = output_root[:output_root.rfind('/')]
        if not os.path.exists(folder):
            os.makedirs(folder)
        plt.savefig(output_root+title+'.'+save_fig_format, 
            dpi=fig_dpi, bbox_inches=fig_bbox_inches, pad_inches=fig_pad, format=save_fig_format
        ) 
        plt.close()
    else:
        plt.show()
    
def pairwise_cat_plots(data, x, y, label=None,
    title='', 
    save_image=False, output_root=None
    ):
    '''
    data is a dictionary with different vars as keys 
    if label is specidied, it will be used as hue
    '''

    sns.set_context("paper", 
        font_scale=3.0, 
        rc={"lines.linewidth": 3.0}
    )

    row_keys = [key for key in data]
    n_rows = len(row_keys)
    column_keys = [key for key in data[row_keys[-1]]]
    n_columns = len(column_keys)

    sns.set_style('darkgrid')

    fig_width = n_columns * 6
    fig_height = n_rows * 6
    fig, axs = plt.subplots(n_rows, n_columns, figsize=(fig_width, fig_height), 
        facecolor='w', edgecolor='k', sharex=True, sharey=True)
    
    axs_plotted = list()
    for i, key_i in enumerate(data):
        for j, key_j in enumerate(data[key_i]):
            df = pd.DataFrame(data[key_i][key_j])

            gfg = sns.violinplot(ax=axs[i, j], data=df, x=x, y=y, hue=label, split=True)
            sns.stripplot(ax=axs[i, j], data=df, x=x, y=y, alpha=0.25, color='black')

            gfg.legend(
                # bbox_to_anchor= (1.2,1), 
                fontsize=20
            )
            axs[i, j].set(xlabel=None)
            axs[i, j].set(ylabel=None)
            axs[i, j].set_title(key_i+'-'+key_j)
            axs_plotted.append(axs[i, j])

    # remove extra subplots
    for ax in axs.ravel():
        if not ax in axs_plotted:
            ax.set_axis_off()
            ax.xaxis.set_tick_params(which='both', labelbottom=True)
    
    if show_title:
        plt.suptitle(title, fontsize=15, y=0.90)

    if save_image:
        folder = output_root[:output_root.rfind('/')]
        if not os.path.exists(folder):
            os.makedirs(folder)
        plt.savefig(output_root+title+'.'+save_fig_format, \
            dpi=fig_dpi, bbox_inches=fig_bbox_inches, pad_inches=fig_pad, format=save_fig_format \
        ) 
        plt.close()
    else:
        plt.show()

def find_network_label(node, networks):
    '''
    find the network that appears the node's name
    node is a string containing a node's name
    networks is a list of networks names
    '''
    for network in networks:
        if network in node:
            return network
    return None

def segment_FC(FC, nodes, networks):
    '''
    average FC values over each large network in
    networks
    the output FC matrix will be in the same order as 
    networks
    '''
    segmented = np.zeros((len(networks), len(networks)))
    counts = np.zeros((len(networks), len(networks)))
    for i, node_i in enumerate(nodes):
        network_i = networks.index(find_network_label(node_i, networks))
        for j, node_j in enumerate(nodes):
            network_j = networks.index(find_network_label(node_j, networks))
            segmented[network_i, network_j] += FC[i, j]
            counts[network_i, network_j] += 1
    return np.divide(segmented, counts, out=np.zeros_like(segmented), where=counts!=0) 

def FC2dict(FC_lst, networks, labels):

    output = {}
    for idx, FC in enumerate(FC_lst):

        if labels[idx]=='EXCLUDE':
            continue
        
        for i, network_i in enumerate(networks):
            for j, network_j in enumerate(networks):

                if j>i:
                    continue

                if not network_i in output:
                    output[network_i] = {}
                if not network_j in output[network_i]:
                    output[network_i][network_j] = {'FC':list(), '':list(), 'label':list()}
            
                output[network_i][network_j]['FC'].append(FC[i, j])
                output[network_i][network_j][''].append('FC')
                output[network_i][network_j]['label'].append(labels[idx])
    return output

def calc_graph_propoerty(A, property, threshold=None, binarize=False):
    """
    calc_graph_propoerty: Computes Graph-based properties 
    of adjacency matrix A
    A is converted to positive before calc
    property:
        - ECM: Computes Eigenvector Centrality Mapping (ECM) 
        - shortest_path
        - degree
        - clustering_coef
        - communicability:
            The communicability between pairs of nodes in G is the sum of 
            walks of different lengths starting at node u and ending at node v.
            it does not take into account the weights of the edges

    Input:

        A (np.array): adjacency matrix (must be >0)

    Output:

        graph-property (np.array): a vector

        if the threshold causes the graph to be disconnected,
            it will return None
    """    

    G = nx.from_numpy_array(np.abs(A)) 
    G.remove_edges_from(nx.selfloop_edges(G))
    # G = G.to_undirected()

    # pruning edges 
    if not threshold is None:
        labels = [d["weight"] for (u, v, d) in G.edges(data=True)]
        labels.sort()
        ebunch = [(u, v) for u, v, d in G.edges(data=True) if d['weight']<threshold]
        G.remove_edges_from(ebunch)

    # check if the graph is still connected
    if not nx.is_connected(G):
        warnings.warn(f"The graph was disconnected after thresholding.")
        return None

    if binarize:
        weight='None'
    else:
        weight='weight'

    graph_property = None
    if property=='ECM':
        graph_property = nx.eigenvector_centrality(G, weight=weight)
        graph_property = [graph_property[node] for node in graph_property]
        graph_property = np.array(graph_property)
    if property=='shortest_path':
        SHORTEST_PATHS = dict(nx.shortest_path_length(G, weight=weight))
        graph_property = np.zeros((A.shape[0], A.shape[0]))
        for node_i in SHORTEST_PATHS:
            for node_j in SHORTEST_PATHS[node_i]:
                graph_property[node_i, node_j] = SHORTEST_PATHS[node_i][node_j]
        graph_property = graph_property + graph_property.T
        graph_property = graph_property[np.triu_indices(graph_property.shape[1], k=1)]
    if property=='degree':
        graph_property = [G.degree(weight=weight)[node] for node in G]
        graph_property = np.array(graph_property)
    if property=='clustering_coef':
        graph_property = nx.clustering(G, weight=weight)
        graph_property = [graph_property[node] for node in graph_property]
        graph_property = np.array(graph_property)
    if property=='communicability':
        comm = nx.communicability(G)
        graph_property = np.zeros((len(comm), len(comm)))
        for node_i in comm:
            for node_j in comm[node_i]:
                graph_property[node_i, node_j] = comm[node_i][node_j]
        graph_property = graph_property + graph_property.T
        graph_property = graph_property[np.triu_indices(graph_property.shape[1], k=1)]

    return graph_property

##########################################################################################

##########################################################################################

# calc average static FC

YEO_networks = ['Vis', 'SomMot', 'DorsAttn', 'SalVentAttn', 'Limbic', 'Cont','Default']

# load description and demographics
manifest = pd.read_csv(manifest_path)

ALL_RECORDS = os.listdir(f"{FC_root}/FC/output")
ALL_RECORDS = [i for i in ALL_RECORDS if 'sub-' in i]
ALL_RECORDS.sort()
SUBJECTS = ALL_RECORDS
print(str(len(SUBJECTS))+' subjects were found.')


for brain_atlas in brain_atlas_list:
    print(f"Analyzing FC files assessed using {brain_atlas} ...")
    roi_labels_global = None
    FC_lst= list()
    FC_segmented_lst = list()
    conditions = list()
    participant_id_lst = [id for id in manifest[manifest_id_key]]
    for idx, subj in enumerate(SUBJECTS):
        participant_id = subj[4:] # remove 'sub-'
        if participant_id in participant_id_lst: # if the subject id is not in the manifest, it will be excluded
            subj_dir = f"{FC_root}/FC/output/{subj}/{session_id}/"
            FC_file = f"{subj_dir}/{subj}_{session_id}_{task}_{space}_FC_{brain_atlas}.npy"
            FC = np.load(FC_file, allow_pickle='TRUE').item()

            # prepare the roi labels for visualization
            roi_labels = FC['roi_labels']
            roi_labels = [str(label) for label in roi_labels]
            roi_labels = [label[label.find('Networks')+9:-3] for label in roi_labels]
            if roi_labels_global is None:
                roi_labels_global = roi_labels
            else:
                # check if the roi_labels are the same
                if not roi_labels_global==roi_labels:
                    warnings.warn(f"roi_labels are not the same for all subjects.")

            segmented_FC = segment_FC(FC[metric], nodes=roi_labels_global, networks=YEO_networks)
            FC_lst.append(FC[metric])
            FC_segmented_lst.append(segmented_FC)
            if manifest[manifest_diagnosis_key][participant_id_lst.index(participant_id)]==PD_label:
                conditions.append("PD")
            elif manifest[manifest_diagnosis_key][participant_id_lst.index(participant_id)]==CTRL_label:
                conditions.append("CTRL")
            else:
                conditions.append("EXCLUDE")
        
    print(f"{conditions.count('CTRL')} CTRL subjects were found.")
    print(f"{conditions.count('PD')} PD subjects were found.")
    print(f"{len(SUBJECTS) - conditions.count('CTRL') - conditions.count('PD')} subjects were excluded.")

    plot_FC(
        FC=np.mean(np.array(FC_lst), axis=0),
        roi_labels=roi_labels_global,
        title='average_FC',
        reorder=reorder_conn_mat,
        fix_lim=fix_lim,
        save_image=save_image, output_root=f"{output_root}/{brain_atlas}/"
    )

    plot_FC(
        FC=np.mean(np.array(FC_segmented_lst), axis=0),
        roi_labels=YEO_networks,
        title='segmented_average_FC',
        reorder=reorder_conn_mat,
        fix_lim=fix_lim,
        save_image=save_image, output_root=f"{output_root}/{brain_atlas}/"
    )

    FC_dict = FC2dict(FC_lst=FC_segmented_lst, networks=YEO_networks, labels=conditions)

    pairwise_cat_plots(FC_dict, x='', y='FC', label='label',
        title='FC_distribution', 
        save_image=save_image, output_root=f"{output_root}/{brain_atlas}/"
        )

    ## graph

    RESULTS = {}
    for threshold in graph_prop_threshold_list:
        for i, property in enumerate(graph_prop_list):
            
            RESULTS[property] = {'values':list(), 'condition':list(), '':list()}
            for j, FC in enumerate(FC_lst):
                
                if conditions[j]=='EXCLUDE':
                    continue

                features = calc_graph_propoerty(
                    A=FC, 
                    property=property, 
                    threshold=threshold, 
                    binarize=False
                )

                if features is None:
                    warnings.warn(f"Threshold={threshold} caused the graph to be disconnected.")
                    continue

                RESULTS[property][''].append('')
                RESULTS[property]['values'].append(np.mean(features))
                RESULTS[property]['condition'].append(conditions[j])    
        try:
            cat_plot(
                data=RESULTS, x='', y='values',
                hue='condition',
                title=f"graph-properties_threshold-{threshold}",
                save_image=save_image, output_root=f"{output_root}/{brain_atlas}/"
            )
        # catch the error and display
        except Exception as e:
            print(f"Error: {e}")