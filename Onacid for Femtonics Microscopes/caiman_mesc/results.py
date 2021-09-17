#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import scipy.ndimage
import cv2
import uuid
import json
import pyperclip
import caiman.utils.visualization

from . import movies

def save_mean_image(file_name, image_name):
    opened_file = movies.mesc_state.open_file(file_name)
    mean_image = opened_file.compute_mean_image()
    
    robustmin, robustmax = np.quantile(mean_image, [0.001, 0.999], axis = (0, 1))
    mean_image = 256 * ((mean_image - robustmin) / (robustmax - robustmin))
    cv2.imwrite(image_name, mean_image)

def save_mescroi(file_name, mescroi_name, layer_index, components):
    opened_file = movies.mesc_state.open_file(file_name)
    
    rng = np.random.default_rng(12345)
    mescroi_data = {"rois": []}
    
    contours = caiman.utils.visualization.get_contours(components, [opened_file.size_y, opened_file.size_x], thr_method='max', thr=0.2)
    for roi_index, contour in enumerate(contours):
        # lighter colours are more visible in the MESc GUI
        r = 128 + int(rng.integers(128))
        g = 128 + int(rng.integers(128))
        b = 128 + int(rng.integers(128))
        
        roi_data = {
            "color": "#ff%02x%02x%02x" % (r, g, b),
            "firstZPlane": layer_index,
            "label": str(roi_index + 1),
            "lastZPlane": layer_index,
            "role": "standard",
            "type": "polygonXY",
            "uniqueID": ("{" + str(uuid.uuid4()) + "}"),
            "vertices": [],
            }
        
        # the component might be non-contiguous, which means the contour may be multiple disconnected loops
        # for each region (thus, contour loop) the coordinates array contains a block of points, delimited by NaNs. the first and last rows are also NaNs.
        # here, we just need to filter out the NaNs
        coords = contour["coordinates"]
        
        for point in coords:
            if not np.any(np.isnan(point)):
                local_coords = opened_file.pixel_coords_to_local(point)
                roi_data["vertices"].append(local_coords.tolist())
        
        mescroi_data["rois"].append(roi_data)
    
    with open(mescroi_name, "w") as f:
        f.write(json.dumps(mescroi_data, indent=4))

class CenterExporter:
    def __init__(self):
        self.modulo = 100 # centers are put onto clipboard every this many frames. set to zero or negative to print every frame
        self.point_format_string = "%f %f %f\n"
        self.header = "X\tY\tZ\n"
    
    def export_periodically(self, file_name, sizes, frame_count, components, component_count, enable_printing):
        if (self.modulo <= 0) or ((frame_count - 1) % self.modulo == 0):
            self.export(file_name, sizes, components, component_count, enable_printing)
            
    def export(self, file_name, sizes, components, component_count, enable_printing):
        opened_file = movies.mesc_state.open_file(file_name)
        
        # the first components are the background, we need the last component_count components
        component_offset = components.shape[-1] - component_count
        
        # computing the centroid of each neuron
        centers = np.empty((component_count, 2))
        for component_index in range(0, component_count):
            center = scipy.ndimage.center_of_mass(components[:, component_offset + component_index].toarray().reshape(sizes))
            centers[component_index, 0] = center[0]
            centers[component_index, 1] = center[1]
        
        string = self.header
        for point in centers:
            absolute_coords = opened_file.local_coords_to_absolute(opened_file.pixel_coords_to_local(point))
            string += (self.point_format_string % (absolute_coords[0], absolute_coords[1], absolute_coords[2]))
        
        print("Placing formatted ROI centroid data on clipboard...")
        
        pyperclip.copy(string)
        
        if enable_printing:
            print(string)
