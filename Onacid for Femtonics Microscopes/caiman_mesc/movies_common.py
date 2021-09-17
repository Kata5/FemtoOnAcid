#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import numpy as np

class MEScParams:
    def __init__(self):
        self.session_handle = 0 # numerical handle of measurement session to load; should usually be left as 0
        self.channel_handle = 0 # numerical handle of the channel to load data from
        self.layer_index = 0 # index of the layer to load; this is overwritten by demos that loop over the layers
        
        self.compute_mean_images = False # if true, compute and save mean images for each layer
        self.do_benchmark = False # if true, create a benchmarker object and print average time per frame or average framerate during onacid
        self.show_plots = True # if true, display custom contour and activity plots during onacid
        self.contour_plot_scale = 1.0 # contour plots are rescaled by this factor
        self.export_centers = True # if true, put formatted ROI data on the clipboard during onacid
        self.show_caiman_diagrams = False # if true, display caiman's own plots after finishing onacid
        self.save_results = False # if true, save all result arrays for each layer as a .hdf5 file after finishing onacid
        self.save_mescroi = True # if true, create a .mescroi JSON file containing the contour of each ROI after finishing onacid
        
        self.length_override = 1000 # upper estimate for number of frames (so that caiman can preallocate the arrays) when loading real-time microscope data
        self.real_time_save_dir = "g:\\projects\\femtonics\\" # when loading real-time data, we have no input file path to place results beside, so they will be placed here instead
        
        self.activity_plot_rows = 5 # number of rows of activity plot windows
        self.activity_plot_cols = 8 # number of cols of activity plot windows
        self.activity_plot_x_offset = 100 # horizontal left padding of activity plot windows

class MEScOpenedFile:
    def __init__(self, mesc_params, file_name):
        self.file_name = file_name
        self.task_type = None
        self.invert_data = None
        
        self.session_handle = mesc_params.session_handle
        self.channel_handle = mesc_params.channel_handle
        
        self.length = None
        self.size_x = None
        self.size_y = None
        
        # data for transforming into local coords
        self.pixel_size_x = None
        self.pixel_size_y = None
        
        # data for transforming into absolute coords
        self.local_coords_min_z = None
        self.local_coords_max_z = None
        self.absolute_coords_rotation = None
        self.absolute_coords_translation = None
        
        self.layers = None
        self.units = None
        
        self.layer_index = mesc_params.layer_index
        
        self.real_time = False
        self.length_override = mesc_params.length_override
        
        path, name_and_ext = os.path.split(self.file_name)
        name, extension = os.path.splitext(name_and_ext)
        if "<Choose a folder>" in path:
            self.base_name = os.path.join(mesc_params.real_time_save_dir, name)
        else:
            self.base_name = os.path.join(path, name)
        
        print("Base name for saving results: " + self.base_name)
    
    def unit_index_of_frame(self, frame_index):
        if frame_index < self.units[0]["start"]:
            return -1
        elif frame_index >= self.units[-1]["end"]:
            return len(self.units)
        
        unit_indices = [unit_index for unit_index, unit_data in enumerate(self.units) if (unit_data["start"] <= frame_index and frame_index < unit_data["end"])]
        
        if len(unit_indices) > 1:
            raise RuntimeError("Overlapping unit ranges detected")
        elif len(unit_indices) == 0:
            raise RuntimeError("Non-contiguous unit ranges detected")
        else:
            return unit_indices[0]
    
    def pixel_coords_to_local(self, pixel_coords):
        # converts the array indices used by CaImAn (measured in pixels)
        # to local coordinates used by MESc GUI (usually measured in micrometers)
        # CaImAn (and OpenCV) use a coordinate system where the origin is the upper left corner and the y coordinate points downwards
        # MESc GUI uses a coordinate system where the origin is in the center and the y coordinate points upwards
        local_x = (pixel_coords[0] - (self.size_x / 2)) * self.pixel_size_x
        local_y = (-1) * (pixel_coords[1] - (self.size_y / 2)) * self.pixel_size_y
        return np.array([local_x, local_y])
    
    def local_coords_to_absolute(self, local_coords):
        # local and absolute coords are both represented in the same units (usually micrometers), so no scaling is necessary
        # however, the local coordinates only contain the x and y coords, while the z coordinate can be computed from
        # the MinZ and MaxZ attributes of the measurement unit. so we first add this as the third coordinate to the vector
        #
        # TODO: which z value to use between MinZ and MaxZ actually depends on the layer index, but currently this is
        # not handled corrently even on the MESc side. so, for the time being, we just use MinZ
        #
        # transformation is described by a rotation and a transation, with a minor quirk:
        # if the rotation is the identity, or it only rotates around the z axis, then the transformation is
        # absolute = rotation * local + translation
        # but, if the rotation is a general one, then we also have to subtract the translation vector before rotating:
        # absolute = rotation * (local - translation) + translation
        
        local_coords_with_z = np.array([local_coords[0], local_coords[1], self.local_coords_min_z])
        if (abs(self.absolute_coords_rotation.as_quat()[0]) < 1e-10) and (abs(self.absolute_coords_rotation.as_quat()[1]) < 1e-10):
            return self.absolute_coords_rotation.apply(local_coords_with_z) + self.absolute_coords_translation
        else:
            return self.absolute_coords_rotation.apply(local_coords_with_z - self.absolute_coords_translation) + self.absolute_coords_translation
    
