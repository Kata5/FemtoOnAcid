#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Complete pipeline for online processing using CaImAn Online (OnACID).
The demo demonstates the analysis of a sequence of files using the CaImAn online
algorithm. The steps include i) motion correction, ii) tracking current 
components, iii) detecting new components, iv) updating of spatial footprints.
The script demonstrates how to construct and use the params and online_cnmf
objects required for the analysis, and presents the various parameters that
can be passed as options. A plot of the processing time for the various steps
of the algorithm is also included.
@author: Eftychios Pnevmatikakis @epnev
Special thanks to Andreas Tolias and his lab at Baylor College of Medicine
for sharing the data used in this demo.
"""

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import glob
import numpy as np
import os
import logging
import matplotlib.pyplot as plt
import cv2
import time

try:
    if __IPYTHON__:
        # this is used for debugging purposes only.
        get_ipython().magic('load_ext autoreload')
        get_ipython().magic('autoreload 2')
except NameError:
    pass

import caiman as cm
from caiman.paths import caiman_datadir
from caiman.source_extraction import cnmf as cnmf
import caiman.motion_correction

import caiman_mesc.gui
import caiman_mesc.movies
import caiman_mesc.results

logging.basicConfig(format=
                    "%(relativeCreated)12d [%(filename)s:%(funcName)20s():%(lineno)s]"\
                    "[%(process)d] %(message)s",
                    level=logging.INFO)

# %%
def main():
    pass # For compatibility between running under Spyder and the CLI
    
    # enable to debug the cause of numpy warnings
    #np.seterr(invalid='raise')
    
    # %%  Start up the User Interface (GUI)
    gui = caiman_mesc.gui.GUI()
    
    # User specified file from gui
    fnames = gui.values["files"]
    
    # setting the MESc-specific parameters
    caiman_mesc.movies.mesc_state.mesc_params.compute_mean_images = gui.values["compute_mean_images"]
    caiman_mesc.movies.mesc_state.mesc_params.show_plots = gui.values["show_plots"]
    caiman_mesc.movies.mesc_state.mesc_params.contour_plot_scale = gui.values["contour_plot_scale"]
    caiman_mesc.movies.mesc_state.mesc_params.export_centers = gui.values["export_centers"]
    caiman_mesc.movies.mesc_state.mesc_params.save_results = gui.values["save_results"]
    caiman_mesc.movies.mesc_state.mesc_params.save_mescroi = gui.values["save_mescroi"]
    caiman_mesc.movies.mesc_state.mesc_params.length_override = gui.values["length_override"]
    caiman_mesc.movies.mesc_state.mesc_params.real_time_save_dir = gui.values["real_time_save_dir"]
    caiman_mesc.movies.mesc_state.mesc_params.activity_plot_rows = gui.values["activity_plot_rows"]
    caiman_mesc.movies.mesc_state.mesc_params.activity_plot_cols = gui.values["activity_plot_cols"]
    
    # your list of files should look something like this
    logging.info(fnames)

# %%   Set up some parameters
    
    if gui.values["init_batch"] < 100:
        raise ValueError("CaImAn doesn't function well if the init batch size is set to less than 100")
    
    if len(fnames) != 1:
        raise ValueError("The multi-layer loop demo only works on a single file")
    
    params_dict = {
        # data parameters
        'fnames': fnames,
        'fr': 31,
        'decay_time': gui.values["decay_time"],
        
        # patch parameters
        'p_tsub': 2,
        
        # preprocess parameters
        'p': gui.values["p"],
        
        # initialization parameters
        'K': gui.values["K"],
        'gSig': gui.values["gSig"],
        
        # temporal parameters
        'nb': gui.values["gnb"],
        
        # merging parameters
        'merge_thr': 0.8,
        
        # online parameters
        'dist_shape_update': True,
        'ds_factor': gui.values["ds_factor"],
        'epochs': gui.values["epochs"],
        'max_shifts_online': gui.values["max_shifts_online"],
        'motion_correct': gui.values["online_MC"],
        'init_batch': gui.values["init_batch"],
        'init_method': 'bare',
        'min_num_trial': gui.values["min_num_trial"],
        'normalize': True,
        'show_movie': False, # WARNING: do NOT turn on caiman's own movie when using the MESc API; use mesc_params.show_plots to use the custom plotter
        'sniper_mode': True,
        'thresh_CNN_noisy': gui.values["thresh_CNN_noisy"],
        
        # motion correction parameters
        'pw_rigid': gui.values["pw_rigid"],
        
        # quality parameters
        'min_SNR': gui.values["min_SNR"],
        'rval_thr': gui.values["rval_thr"],
        'use_cnn': True,
        'min_cnn_thr': 0.99,
        'cnn_lowest': 0.1,
    }
    
    opts = cnmf.params.CNMFParams(params_dict=params_dict)
    
    cv2.setNumThreads(16)

    layers = caiman_mesc.movies.get_layers(fnames[0])
    
    layer_names = gui.values["layer_names"]
    if layer_names == "*":
        print("Processing all layers")
        layer_indices = range(0, layers)
    else:
        print("Processing only layers " + layer_names)
        layer_indices = []
        for layer_name in layer_names.strip(" ").split(","):
            layer_index = int(layer_name) - 1
            if layer_index >= 0 and layer_index < layers:
                layer_indices.append(layer_index)
            else:
                print("Warning: invalid layer " + layer_name + " will not be processed")
    
    for layer_index in layer_indices:
        layer_name = layer_index + 1
        print("Running motion correction on layer %d of %d" % (layer_name, layers))
        caiman_mesc.movies.mesc_state.set_layer_index(layer_index)
        
        if caiman_mesc.movies.mesc_state.mesc_params.compute_mean_images:
            image_name = caiman_mesc.movies.get_base_name(fnames[0]) + '_layer' + str(layer_name) + '_mean.png'
            print("Saving mean image for layer %d as %s" % (layer_name, image_name))
            caiman_mesc.results.save_mean_image(fnames[0], image_name)
        
        if caiman_mesc.movies.mesc_state.mesc_params.do_benchmark:
            benchmark = caiman_mesc.benchmark.SimpleOnACIDBenchmark(10)
    
        # motion correction and display
        
        moving_average = None
        frame_count = 0
        moving_average_weight = 0.5
        start_time = time.time()
        for frame in caiman_mesc.movies.load_iter(fnames[0]):
            frame = frame.astype(np.float32)
            
            frame_robustmin, frame_robustmax = np.quantile(frame, [0.001, 0.999], axis = (0, 1))
            if frame_robustmax > frame_robustmin:
                frame_normalized = (frame - frame_robustmin) / (frame_robustmax - frame_robustmin)
            else:
                frame_normalized = np.full_like(frame, 0.5)
            
            if frame_count == 0:
                frame_shifted = frame_normalized
                moving_average = frame_shifted
            else:
                max_shift = opts.get('online', 'max_shifts_online')
                frame_shifted, shift = caiman.motion_correction.motion_correct_iteration_fast(frame_normalized, moving_average, max_shift, max_shift)
                moving_average = moving_average_weight * moving_average + (1 - moving_average_weight) * frame_shifted
            
            cv2.imshow('frame', moving_average)
            # ugly hack to ensure that this works both with and without the dummy Qt app needed by the MESc API
            if not caiman_mesc.movies.mesc_state.has_qapp():
                cv2.waitKey(1)
            
            frame_count += 1
            
            if caiman_mesc.movies.mesc_state.mesc_params.do_benchmark:
                benchmark.print_benchmark(frame_count)

#%%
# This is to mask the differences between running this demo in Spyder
# versus from the CLI
if __name__ == "__main__":
    main()
