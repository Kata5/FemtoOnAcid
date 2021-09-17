#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import h5py
import natsort
import numpy as np
import scipy.spatial.transform
import math

from . import movies_common
from . import movies_util

class MEScOpenedFileDirect(movies_common.MEScOpenedFile):
    def __init__(self, mesc_params, file_name):
        super().__init__(mesc_params, file_name)
        
        if self.real_time:
            raise RuntimeError("Cannot use direct file access for real-time data")
        
        self.h5py_file =  h5py.File(file_name, "r")
        
        self.session_handle = mesc_params.session_handle
        self.session_key = 'MSession_%d' % (self.session_handle,)
        self.channel_key = 'Channel_%d' % (mesc_params.channel_handle,)
        
        session = self.h5py_file.get(self.session_key)
        
        self.task_type = None
        self.size_x = None
        self.size_y = None
        self.pixel_size_x = None
        self.pixel_size_y = None
        
        self.local_coords_min_z = None
        self.local_coords_max_z = None
        self.absolute_coords_rotation = None
        self.absolute_coords_translation = None
        
        self.layers = None
        self.length = 0
        self.units = []
        for unit_index, unit_key in enumerate(natsort.natsorted(session.keys())):
            unit = session.get(unit_key)
            
            # there are three places where various pieces of metadata are stored for the recording:
            #  - inside the MeasurementParamsJSON field of the HDF5 attributes
            #  - inside the MeasurementParamsXML field of the HDF5 attributes
            #  - directly as a HDF5 attribute
            # often, the same value is stored in more than one way, but not every form is present, so we use a fallback for some values
            # we prefer the JSON, as it is the more modern way, but we fall back to the attribute value when necessary
            # we prefer the XML the least, as it occasionally contains the value with a lower precision
            hdf5_attributes = unit.attrs
            measurement_params_json = hdf5_attributes["MeasurementParamsJSON"] if ("MeasurementParamsJSON" in hdf5_attributes) else None
            measurement_params_xml = hdf5_attributes["MeasurementParamsXML"].decode("cp1252") if ("MeasurementParamsXML" in hdf5_attributes) else None
            
            self.task_type = movies_util.assert_none_or_equal(self.task_type, movies_util.task_type_from_xml(measurement_params_xml))
            self.layers = movies_util.assert_none_or_equal(self.layers, movies_util.layers_fallback(measurement_params_json, measurement_params_xml))
            
            all_dimensions = unit.get(self.channel_key).shape
            
            # sometimes the total number of frames is not divisible by the layer count; that is, not all layers have the final frame
            # to deal with this, and to make the length of the unit consistent across layers, we always ignore the last frame for multilayer files
            if self.layers > 1:
                unit_length = math.ceil(all_dimensions[0] / self.layers) - 1
            else:
                unit_length = all_dimensions[0]
            
            self.length += unit_length
            self.size_y = movies_util.assert_none_or_equal(self.size_y, all_dimensions[1])
            self.size_x = movies_util.assert_none_or_equal(self.size_x, all_dimensions[2])
            
            pixel_sizes = movies_util.pixel_sizes_fallback(measurement_params_json, hdf5_attributes, measurement_params_xml, mesc_params.channel_handle)
            self.pixel_size_x = movies_util.assert_none_or_equal(self.pixel_size_x, pixel_sizes[0])
            self.pixel_size_y = movies_util.assert_none_or_equal(self.pixel_size_y, pixel_sizes[1])
            
            local_coords_z_values = movies_util.local_coords_z_values_from_json(measurement_params_json)
            self.local_coords_min_z = movies_util.assert_none_or_equal(self.local_coords_min_z, local_coords_z_values[0])
            self.local_coords_max_z = movies_util.assert_none_or_equal(self.local_coords_max_z, local_coords_z_values[1])
            
            # TODO: these are more complicated structures, we can't just use assert_none_or_equal to compare them
            self.absolute_coords_rotation = scipy.spatial.transform.Rotation.from_quat(hdf5_attributes["GeomTransRot"])
            self.absolute_coords_translation = np.array(hdf5_attributes["GeomTransTransl"])
            
            self.units.append({"key": unit_key, "length": unit_length, "start": (self.length - unit_length), "end": self.length})
        
        if self.task_type in ["TaskResonantCommon"]:
            self.invert_data = True
        elif self.task_type in ["TaskAOFullFrame"]:
            self.invert_data = False
        else:
            raise ValueError("Unknown task type: " + self.task_type)
    
    def compute_mean_image(self):
        session = self.h5py_file.get(self.session_key)
        
        frame_count = 0
        for unit_index, unit_data in enumerate(self.units):
            unit = session.get(unit_data["key"])
            loaded_dataset = np.flip(np.array(unit.get(self.channel_key)).squeeze()[self.layer_index:(self.layer_index + self.layers * unit_data["length"]):self.layers, :, :], axis = 1)
            if self.invert_data:
                loaded_dataset = 65535 - loaded_dataset
            
            current_unit_mean = np.mean(loaded_dataset, axis=0).squeeze()
            if frame_count == 0:
                mean_image = current_unit_mean
            else:
                mean_image = (float(frame_count) * mean_image + float(unit_data["length"]) * current_unit_mean) / float(frame_count + unit_data["length"])
            
            frame_count += unit_data["length"]
        
        return mean_image

    def load(self, frame_slice):
        session = self.h5py_file.get(self.session_key)
        
        if frame_slice is not None:
            if type(frame_slice) is not slice:
                raise TypeError("MESc loader can only deal with slices as frame indices")
            
            if (frame_slice.step is not None) and (frame_slice.step != 1):
                raise ValueError("MESc loader can only deal with single-stepping slices")
            
            last_requested_frame = (index_count if frame_slice.stop is None else frame_slice.stop) - 1
            
            last_necessary_unit = self.unit_index_of_frame(last_requested_frame)
            if (last_necessary_unit < 0) or (last_necessary_unit >= len(self.units)):
                raise ValueError("Invalid frame index")
            
            necessary_units = slice(0, last_necessary_unit + 1)
        else:
            frame_slice = slice(0, None)
            necessary_units = slice(0, None)
        
        unit_datasets = []
        for unit_index, unit_data in enumerate(self.units[necessary_units]):
            unit = session.get(unit_data["key"])
            loaded_dataset = np.flip(np.array(unit.get(self.channel_key)).squeeze()[self.layer_index:(self.layer_index + self.layers * unit_data["length"]):self.layers, :, :], axis = 1)
            if self.invert_data:
                loaded_dataset = 65535 - loaded_dataset
            
            unit_datasets.append(loaded_dataset)

        input_arr = np.concatenate(unit_datasets, axis=0)[frame_slice]
        
        return input_arr

    def load_iter(self, frame_slice):
        if frame_slice is not None:
            if type(frame_slice) is not slice:
                raise TypeError("MESc loader can only deal with slices as frame indices")
            
            if (frame_slice.step is not None) and (frame_slice.step != 1):
                raise ValueError("MESc loader can only deal with single-stepping slices")
            
            frame_indices = range(frame_slice.start, self.length if frame_slice.stop is None else frame_slice.stop)
        else:
            frame_indices = range(0, self.length)
        
        session = self.h5py_file.get(self.session_key)
        
        loaded_unit_index = None
        loaded_dataset = None
        for frame_index in frame_indices:
            unit_index = self.unit_index_of_frame(frame_index)
            
            if (unit_index < 0) or (unit_index >= len(self.units)):
                raise ValueError("Invalid frame index")
            
            unit_data = self.units[unit_index]
            
            if loaded_unit_index is None or loaded_unit_index != unit_index:
                loaded_unit_index = unit_index
                
                unit = session.get(unit_data["key"])
                loaded_dataset = np.flip(np.array(unit.get(self.channel_key)).squeeze()[self.layer_index:(self.layer_index + self.layers * unit_data["length"]):self.layers, :, :], axis = 1)
                if self.invert_data:
                    loaded_dataset = 65535 - loaded_dataset
            
            # the elements of frame_indices are absolute, but the indices of the currently loaded dataset are relative to its first index
            yield loaded_dataset[frame_index - unit_data["start"]]
