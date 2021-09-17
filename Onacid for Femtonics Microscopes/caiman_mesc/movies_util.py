#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree
import json

def assert_none_or_equal(variable, value):
    if variable is None:
        return value
    elif variable != value:
        1
        #raise ValueError("Parameters such as frame size and layer count must be the same for all measurement units in the session")
    
    return variable

def task_type_from_xml(measurement_params_xml):
    try:
        parsed_xml = xml.etree.ElementTree.fromstring(measurement_params_xml)
        task_type = parsed_xml.attrib["Type"]
        return task_type
    except:
        return None

def layers_from_xml(measurement_params_xml):
    try:
        parsed_xml = xml.etree.ElementTree.fromstring(measurement_params_xml)
        
        layers = None
        for child in parsed_xml:
            if child.tag == "Params":
                for element in child:
                    if element.tag == "param" and element.attrib["name"] == "Slices":
                        layers = int(element.attrib["value"])
        
        return layers
    except:
        return None

def layers_from_json(measurement_params_json):
    try:
        parsed_json = json.loads(measurement_params_json)
        layers = parsed_json["Slices"] if "Slices" in parsed_json else None
        return layers
    except:
        return None

def layers_fallback(measurement_params_json, measurement_params_xml):
    layers = None
    
    layers = layers if (layers is not None) else layers_from_json(measurement_params_json)
    layers = layers if (layers is not None) else layers_from_xml(measurement_params_xml)
    
    # if neither the JSON nor the XML is present, we assume this is a single-layered recording
    layers = layers if (layers is not None) else 1
    
    return layers

def pixel_sizes_from_json(measurement_params_json, channel_handle):
    try:
        parsed_json = json.loads(measurement_params_json)
        channel_name = parsed_json["channels"][channel_handle]
        
        pixel_size_x = parsed_json["axinfo"][channel_name]["WidthStep"]
        pixel_size_y = parsed_json["axinfo"][channel_name]["HeightStep"]
        
        return (pixel_size_x, pixel_size_y)
    except:
        return None

def pixel_sizes_from_hdf5(hdf5_attributes):
    try:
        pixel_size_x = hdf5_attributes["XAxisConversionConversionLinearScale"]
        pixel_size_y = hdf5_attributes["YAxisConversionConversionLinearScale"]
        return (pixel_size_x, pixel_size_y)
    except:
        return None

def pixel_sizes_from_xml(measurement_params_xml):
    try:
        parsed_xml = xml.etree.ElementTree.fromstring(measurement_params_xml)
        
        pixel_size_x = None
        pixel_size_y = None
        for child in parsed_xml:
            if child.tag == "Params":
                for element in child:
                    if element.tag == "param" and element.attrib["name"] == "PixelSizeX":
                        pixel_size_x = float(element.attrib["value"])
                    if element.tag == "param" and element.attrib["name"] == "PixelSizeY":
                        pixel_size_y = float(element.attrib["value"])
        
        if (pixel_size_x is not None) and (pixel_size_y is not None):
            return (pixel_size_x, pixel_size_y)
        else:
            return None
    except:
        return None

def pixel_sizes_fallback(measurement_params_json, hdf5_attributes, measurement_params_xml, channel_handle):
    pixel_sizes = None
    
    pixel_sizes = pixel_sizes if (pixel_sizes is not None) else pixel_sizes_from_json(measurement_params_json, channel_handle)
    pixel_sizes = pixel_sizes if (pixel_sizes is not None) else pixel_sizes_from_hdf5(hdf5_attributes)
    pixel_sizes = pixel_sizes if (pixel_sizes is not None) else pixel_sizes_from_xml(measurement_params_xml)
    
    return pixel_sizes

def local_coords_z_values_from_json(measurement_params_json):
    try:
        parsed_json = json.loads(measurement_params_json)
        
        local_coords_min_z = parsed_json["MinZ"]
        local_coords_max_z = parsed_json["MaxZ"]
        
        return (local_coords_min_z, local_coords_max_z)
    except:
        return (0.0, 0.0)
