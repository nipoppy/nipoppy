import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def montage_bold(path):
    fig, axes = plt.subplots(1, 5, figsize=(20,5))

    PROPS = {
        'boxprops':{'facecolor':'none', 'edgecolor':'black'},
        'medianprops':{'color':'black'},
        'whiskerprops':{'color':'black'},
        'capprops':{'color':'black'}
    }

    df = pd.read_csv(path, delimiter='\t')
    df = df.loc[df['bids_name'].str.contains("bold")]


    for num, i in enumerate(['efc', 'snr', ['dvars_std', 'dvars_vstd'], 'fd_mean', ['summary_bg_mean', 'summary_bg_median', 'summary_bg_stdv', 'summary_bg_mad', 'summary_bg_k', 'summary_bg_p05', 'summary_bg_p95']]):

        sns.boxplot(ax= axes[num], data=df[i], showfliers = False, **PROPS)

        g = sns.stripplot(ax=axes[num], data=df[i], alpha=0.5, size=7)


        # for item in ax.collections[num_items:]:
        #     item.set_offsets(item.get_offsets() + 50)
        # df.loc[df['bids_name'].str.contains("bold")].boxplot('efc')

        if type(i) == str: 
            g.set_xticklabels([i])
        else: g.set_xticklabels(i, rotation=80)
        g.set(ylabel=None)

        if i == 'efc': g.set_title('EFC')
        elif i == 'snr': g.set_title('SNR')
        elif i == 'fd_mean': g.set_title('FD (mm)')
        elif any("dvars" in s for s in i): g.set_title('DVARS')
        elif any("summary_bg" in s for s in i): g.set_title('SUMMARY_BG')
            
def montage_T1w(path):
    fig, axes = plt.subplots(1, 5, figsize=(20,5))

    PROPS = {
        'boxprops':{'facecolor':'none', 'edgecolor':'black'},
        'medianprops':{'color':'black'},
        'whiskerprops':{'color':'black'},
        'capprops':{'color':'black'}
    }

    df = pd.read_csv(path, delimiter='\t')
    df = df.loc[df['bids_name'].str.contains("T1w")]


    for num, i in enumerate(['efc', ['snr_csf', 'snr_gm', 'snr_wm'], ['fwhm_avg', 'fwhm_x', 'fwhm_y', 'fwhm_z'], ['inu_med', 'inu_range'], ['summary_bg_mean', 'summary_bg_median', 'summary_bg_stdv', 'summary_bg_mad', 'summary_bg_k', 'summary_bg_p05', 'summary_bg_p95']]):

        sns.boxplot(ax= axes[num], data=df[i], showfliers = False, **PROPS)

        g = sns.stripplot(ax=axes[num], data=df[i], alpha=0.5, size=7)


        if type(i) == str: 
            g.set_xticklabels([i])
        else: g.set_xticklabels(i, rotation=80)
        g.set(ylabel=None)

        if i == 'efc': g.set_title('EFC')
        elif any("snr" in s for s in i): g.set_title('SNR')
        elif any("inu" in s for s in i): g.set_title('INU')
        elif any("fwhm" in s for s in i): g.set_title('FWHM (vox)')
        elif any("summary_bg" in s for s in i): g.set_title('SUMMARY_BG')
 


montage_bold(sys.argv[1]); #mriqc_stats/group_bold.tsv
plt.savefig('group_bold.jpeg', bbox_inches='tight', pad_inches=0.5)
montage_T1w(paths[2]); #mriqc_stats/group_T1w.tsv
plt.savefig('group_T1w.jpeg', bbox_inches='tight', pad_inches=0.5)
