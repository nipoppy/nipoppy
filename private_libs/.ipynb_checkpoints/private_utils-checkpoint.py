# -*- coding: utf-8 -*-
"""This is the utils library for the mr_proc project maintained ORIGAMI Lab."
Functions:

"""
import pandas as pd
import numpy as np

def report_visit(df, df_group, sub_, visit_, group_ ):
    tmp_group=df_group.copy();
    tmp_group.columns=[sub_, 'Group'];
    df=df.set_index(sub_).join(tmp_group.set_index(sub_), how='left').copy()
    df=df.dropna()
    print(df.groupby(by=sub_).agg(lambda x: set(x)).Group.value_counts())
    grouped=df.groupby(by=sub_).agg(lambda x: len(set(x)))
    grouped['Visit']= grouped[visit_]
    grouped.hist(column=['Visit']);
    #print('Visit counts:', grouped[visit_].value_counts())
    if group_ !="":
        print(df.groupby(by=sub_).agg(lambda x: len(set(x)))[visit_].value_counts())
        print(df.groupby(by=sub_).agg(lambda x: set(x))[visit_].value_counts())
    return df