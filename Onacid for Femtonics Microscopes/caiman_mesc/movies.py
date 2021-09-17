#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from . import movies_common
from . import movies_direct
from . import movies_mesc_api

class MEScState:
    def __init__(self):
        self.mesc_params = movies_common.MEScParams()
        self.opened_files = {}
        
        self.mesc_api = None
        """
        try:
            self.mesc_api = movies_mesc_api.MEScAPI()
            self.mesc_api.initialize()
        except:
            print("Failed to initialize MESc API, falling back to direct file access")
            self.mesc_api = None
        """

    def initialize(self):
        """
        try:
            self.mesc_api = movies_mesc_api.MEScAPI()
            self.mesc_api.initialize()
        except:
            print("Failed to initialize MESc API, falling back to direct file access")
            self.mesc_api = None
        """
        self.mesc_api = movies_mesc_api.MEScAPI()
        self.mesc_api.initialize()
        
    def has_qapp(self):
        # checking if PySide2's QtCoreApplication singleton is initialized
        return (True if qApp else False)
    
    def open_file(self, file_name):
        if file_name not in self.opened_files:
            if self.mesc_api:
                print(self.mesc_api.conn)
                self.opened_files[file_name] = movies_mesc_api.MEScOpenedFileAPI(self.mesc_api, self.mesc_params, file_name)
            else:
                self.opened_files[file_name] = movies_direct.MEScOpenedFileDirect(self.mesc_params, file_name)
        
        return self.opened_files[file_name]
    
    def set_layer_index(self, layer_index):
        self.mesc_params.layer_index = layer_index
        
        for file_name in self.opened_files:
            self.opened_files[file_name].layer_index = layer_index

def load(file_name, frame_slice = None):
    opened_file = mesc_state.open_file(file_name)
    return opened_file.load(frame_slice)

def load_iter(file_name, frame_slice = None):
    opened_file = mesc_state.open_file(file_name)
    yield from opened_file.load_iter(frame_slice)

def get_file_size(file_name):
    opened_file = mesc_state.open_file(file_name)
    length = opened_file.length_override if opened_file.real_time else opened_file.length
    return np.array([opened_file.size_y, opened_file.size_x]), length

def get_layers(file_name):
    opened_file = mesc_state.open_file(file_name)
    return opened_file.layers

def get_base_name(file_name):
    opened_file = mesc_state.open_file(file_name)
    return opened_file.base_name

mesc_state = MEScState()
