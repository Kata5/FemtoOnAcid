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
from multiprocessing import freeze_support

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

    import sys
    print("Number of arguments: %d" % (len(sys.argv)))
    print("Argument List: %s" % (str(sys.argv)))

    # enable to debug the cause of numpy warnings
    #np.seterr(invalid='raise')

    caiman_mesc.movies.mesc_state.initialize()
    
    # %%  Start up the User Interface (GUI)
    if len(sys.argv) == 2 and sys.argv[1] == 'nogui':
        gui = caiman_mesc.gui.GUI(nogui=True)
    else:
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
    
    if gui.values["epochs"] != 1:
        raise ValueError("Plotting functions haven't been tested for multi-epoch runs")
    
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


    #print("THREAD")
    #print(caiman_mesc.movies.mesc_state.mesc_api.p.is_alive())
    
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
        print("Running caiman on layer %d of %d" % (layer_name, layers))
        caiman_mesc.movies.mesc_state.set_layer_index(layer_index)
        
        if caiman_mesc.movies.mesc_state.mesc_params.compute_mean_images:
            image_name = caiman_mesc.movies.get_base_name(fnames[0]) + '_layer' + str(layer_name) + '_mean.png'
            print("Saving mean image for layer %d as %s" % (layer_name, image_name))
            caiman_mesc.results.save_mean_image(fnames[0], image_name)
        
        # %% fit online
        cnm = cnmf.online_cnmf.OnACID(params=opts)
        cnm.fit_online()

        # when running in real time, we pass caiman an upper estimate for the number of frames
        # after we are finished, we need to resize all its arrays to the actual length
        # we cannot actually check here that the recording was real time, so we just resize the arrays if their length doesn't match
        sizes, length = caiman_mesc.movies.get_file_size(fnames[0])
        
        array_names = ["C", "f", "YrA", "F_dff", "R", "S", "noisyC", "C_on"]
        for array_name in array_names:
            value = getattr(cnm.estimates, array_name)
            if (value is not None) and (value.shape[1] != length):
                setattr(cnm.estimates, array_name, value[:, 0:length])
        
        list_names = ["shifts"]
        for list_name in list_names:
            value = getattr(cnm.estimates, list_name)
            if (value is not None) and (len(value) != length):
                setattr(cnm.estimates, list_name, value[0:length])
        
        logging.info('Number of components: ' + str(cnm.estimates.A.shape[-1]))
        
        if caiman_mesc.movies.mesc_state.mesc_params.export_centers:
            center_exporter = caiman_mesc.results.CenterExporter()
            center_exporter.export(fnames[0], sizes, cnm.estimates.A, cnm.estimates.A.shape[-1], True)
        
        # loading the whole movie again is only necessary for caiman's own plots and/or saving the results
        if caiman_mesc.movies.mesc_state.mesc_params.show_caiman_diagrams or caiman_mesc.movies.mesc_state.mesc_params.save_results:
            images = cm.load(fnames[0])
            Cn = images.local_correlations(swap_dim=False, frames_per_chunk=500)
            
            # hack to eliminate the NaNs caiman produces when at least one pixel is completely constant over a chunk
            Cn = np.where(np.isnan(Cn), 0, Cn)
        
        if caiman_mesc.movies.mesc_state.mesc_params.show_caiman_diagrams:
            print("Displaying caiman's own diagrams for layer %d" % (layer_name,))
            
            # %% plot contours (this may take time)
            cnm.estimates.plot_contours(img=Cn, display_numbers=False)

            # %% view components
            cnm.estimates.view_components(img=Cn)

            # %% plot timing performance (if a movie is generated during processing, timing
            # will be severely over-estimated)
            T_motion = 1e3*np.array(cnm.t_motion)
            T_detect = 1e3*np.array(cnm.t_detect)
            T_shapes = 1e3*np.array(cnm.t_shapes)
            T_track = 1e3*np.array(cnm.t_online) - T_motion - T_detect - T_shapes
            plt.figure()
            plt.stackplot(np.arange(len(T_motion)), T_motion, T_track, T_detect, T_shapes)
            plt.legend(labels=['motion', 'tracking', 'detect', 'shapes'], loc=2)
            plt.title('Processing time allocation')
            plt.xlabel('Frame #')
            plt.ylabel('Processing time [ms]')
        
        if caiman_mesc.movies.mesc_state.mesc_params.save_mescroi:
            mescroi_name = caiman_mesc.movies.get_base_name(fnames[0]) + '_layer' + str(layer_name) + '.mescroi'
            print("Saving ROI data for layer %d as %s" % (layer_name, mescroi_name))
            caiman_mesc.results.save_mescroi(fnames[0], mescroi_name, layer_index, cnm.estimates.A)
        
        if caiman_mesc.movies.mesc_state.mesc_params.save_results:
            # %% RUN IF YOU WANT TO VISUALIZE THE RESULTS (might take time)
            c, dview, n_processes = \
                cm.cluster.setup_cluster(backend='local', n_processes=None,
                                        single_thread=False)
            if opts.online['motion_correct']:
                shifts = cnm.estimates.shifts[-cnm.estimates.C.shape[-1]:]
                if not opts.motion['pw_rigid']:
                    memmap_file = cm.motion_correction.apply_shift_online(images, shifts,
                                                                save_base_name='MC')
                else:
                    mc = cm.motion_correction.MotionCorrect(fnames, dview=dview,
                                                            **opts.get_group('motion'))

                    mc.y_shifts_els = [[sx[0] for sx in sh] for sh in shifts]
                    mc.x_shifts_els = [[sx[1] for sx in sh] for sh in shifts]
                    memmap_file = mc.apply_shifts_movie(fnames, rigid_shifts=False,
                                                        save_memmap=True,
                                                        save_base_name='MC')
            else:  # To do: apply non-rigid shifts on the fly
                memmap_file = images.save(fnames[0][:-4] + 'mmap')
            cnm.mmap_file = memmap_file
            Yr, dims, T = cm.load_memmap(memmap_file)

            images = np.reshape(Yr.T, [T] + list(dims), order='F')
            cnm.estimates.detrend_df_f()
            cnm.estimates.evaluate_components(images, cnm.params, dview=dview)
            cnm.estimates.Cn = Cn
            
            results_file_name = caiman_mesc.movies.get_base_name(fnames[0]) + '_layer' + str(layer_name) + '_results.hdf5'
            print("Saving layer %d results as %s" % (layer_name, results_file_name))
            cnm.save(results_file_name)
            
            # removing the memory mapped file
            Yr._mmap.close()
            del Yr
            os.remove(memmap_file)

            dview.terminate()

#%%
# This is to mask the differences between running this demo in Spyder
# versus from the CLI
if __name__ == "__main__":
    main()
