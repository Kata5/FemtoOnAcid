#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import numpy as np
import scipy.spatial.transform
import time
import os.path
import multiprocessing
from threading import Thread, Event, Lock
import math

import PySide2.QtCore

import femtoapi_wrapper.APIFunctions

from . import movies_common
from . import movies_util


class apiThread(Thread):
    def __init__(self, conn):
        Thread.__init__(self)
        self.event = Event()
        self.lock = Lock()
        self.conn = conn


    def run(self):
        #threading
        ws = femtoapi_wrapper.APIFunctions.initConnection()
        if ws is None:
            raise RuntimeError("Failed to connect to MESc API")
        femtoapi_wrapper.APIFunctions.login(ws, 'csp', 'asdf')
        while True:
            if self.event.is_set():
                funct = self.conn['send']
                self.lock.acquire()
                if funct[0] == 'getproc':
                    res = femtoapi_wrapper.APIFunctions.getProcessingState(ws)
                elif funct[0]== 'read':
                    res = femtoapi_wrapper.APIFunctions.readRawChannelDataToClientsBlob(ws, funct[1], funct[2], funct[3])
                elif funct[0] == 'close':
                    res = femtoapi_wrapper.APIFunctions.closeConnection(ws)
                else:
                    res = None
                self.conn['rec'] = res
                self.lock.release()
                self.event.clear()
            time.sleep(1/1000)

def apistart(conn):
    #multiproseccing
    app = PySide2.QtCore.QCoreApplication(sys.argv)
    ws = None
    while True:
        funct = conn.recv()
        if funct[0] == 'start':
            ws = femtoapi_wrapper.APIFunctions.initConnection()
            if ws is None:
                raise RuntimeError("Failed to connect to MESc API")
            femtoapi_wrapper.APIFunctions.login(ws, 'csp', 'asdf')
            res = 'Connected'
        elif funct[0] == 'getproc':
            res = femtoapi_wrapper.APIFunctions.getProcessingState(ws)
        elif funct[0]== 'read':
            res = femtoapi_wrapper.APIFunctions.readRawChannelDataToClientsBlob(ws, funct[1], funct[2], funct[3])
        elif funct[0] == 'close':
            res = femtoapi_wrapper.APIFunctions.closeConnection(ws)
        else:
            res = None
        conn.send(res)
        
        

class MEScAPI:
    def __init__(self):
        self.app = None
        #self.conn = None #orig and multiproc
        self.conn = {'rec':None, 'send':None} #threading
        
        if not qApp:
            # dummy application needed by the API wrapper
            self.app = PySide2.QtCore.QCoreApplication(sys.argv)
        
        """multiprocessing
        parent_conn, child_conn = multiprocessing.Pipe()
        self.p = multiprocessing.Process(target=apistart, args=(child_conn, ))
        self.p.start()
        self.conn = parent_conn
        self.conn.send(['start'])
        print(self.conn.recv())
        """
        """orig
        if multiprocessing.current_process().name == "MainProcess":
            if not qApp:
                # dummy application needed by the API wrapper
                self.app = PySide2.QtCore.QCoreApplication(sys.argv)
            
            #self.conn = femtoapi_wrapper.APIFunctions.initConnection(1)
            self.conn = femtoapi_wrapper.APIFunctions.initConnection()
            if self.conn is None:
                raise RuntimeError("Failed to connect to MESc API")
            
            femtoapi_wrapper.APIFunctions.login(self.conn, 'csp', 'asdf')
        """
    def initialize(self):
        #threading
        self.p = apiThread(self.conn)
        self.p.start()
        """ #multiprocessing
        parent_conn, child_conn = multiprocessing.Pipe()
        self.p = multiprocessing.Process(target=apistart, args=(child_conn, ))
        self.p.start()
        self.conn = parent_conn
        self.conn.send(['start'])
        print(self.conn.recv())
        """
        
    def __del__(self):
        if self.conn is not None:
            """
            self.conn.send(['close'])
            print(self.mesc_api.conn.recv())
            """
            self.mesc_api.conn['send'] = ['close']
            self.mesc_api.p.event.set()
                
            #femtoapi_wrapper.APIFunctions.closeConnection(self.conn)
            self.p.stop()
        
        if (self.app is not None) and self.app:
            self.app.shutdown()

class MEScOpenedFileAPI(movies_common.MEScOpenedFile):
    def __init__(self, mesc_api, mesc_params, file_name):
        super().__init__(mesc_params, file_name)
        
        self.mesc_api = mesc_api
        #self.open_file_sync()
        
        self.load_mesc_state()
        self.parse_file_data()
        self.parse_session_data()
        self.parse_unit_data()
    
    def open_file_sync(self):
        self.mesc_api.conn.send('getproc')
        #self.mesc_state = femtoapi_wrapper.APIFunctions.getProcessingState(self.mesc_api.conn)
        self.mesc_state = self.mesc_api.conn.recv()
        currentFileHandle = self.mesc_state["currentFileHandle"][0]
        command_id = femtoapi_wrapper.APIFunctions.openFilesAsync(self.mesc_api.conn, currentFileHandle)["id"]
        status = {}
        while (len(status) == 0) or (status["isPending"] == True):
            time.sleep(0.01)
            status = femtoapi_wrapper.APIFunctions.getStatus(self.mesc_api.conn, command_id)
        
        if status["error"] != "":
            raise RuntimeError("Error opening file: " + str(status["error"]))
    
    def load_mesc_state(self):
        """multiproc
        self.mesc_api.conn.send(['getproc'])
        self.mesc_state = self.mesc_api.conn.recv()
        """
        self.mesc_api.conn['send'] = ['getproc']
        self.mesc_api.p.event.set()
        while self.mesc_api.p.event.is_set():
            time.sleep(10/1000)
        self.mesc_api.p.lock.acquire()
        self.mesc_state = self.mesc_api.conn['rec']
        self.mesc_api.p.lock.release()
        
        #self.mesc_state = femtoapi_wrapper.APIFunctions.getProcessingState(self.mesc_api.conn)

    
    def parse_file_data(self):
        self.file_index = None
        self.file_handle = None
        for index, open_file in enumerate(self.mesc_state["openedMEScFiles"]):
            if open_file["path"] == self.file_name:
                self.file_index = index
                self.file_handle = open_file["handle"][0]
        
        if self.file_index is None:
            raise RuntimeError("Cannot find index for file handle")
        
        self.file_data = self.mesc_state["openedMEScFiles"][self.file_index]
    
    def parse_session_data(self):
        for session_index, session_data in enumerate(self.file_data["measurementSessions"]):
            if session_data["handle"][1] == self.session_handle:
                self.session_index = session_index
                self.session_data = session_data
    
    def parse_unit_data(self):
        if len(self.session_data["measurements"]) == 0:
            raise RuntimeError("Cannot process sessions without measurement units")
        
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
        self.real_time = False
        for unit_index, unit_data in enumerate(self.session_data["measurements"]):
            self.task_type = movies_util.assert_none_or_equal(self.task_type, unit_data["measurementType"])
            self.size_x = movies_util.assert_none_or_equal(self.size_x, unit_data["dimensions"][0]["size"])
            self.size_y = movies_util.assert_none_or_equal(self.size_y, unit_data["dimensions"][1]["size"])
            self.pixel_size_x = movies_util.assert_none_or_equal(self.pixel_size_x, unit_data["dimensions"][0]["conversion"]["scale"])
            self.pixel_size_y = movies_util.assert_none_or_equal(self.pixel_size_y, unit_data["dimensions"][1]["conversion"]["scale"])
            
            if len(unit_data["dimensions"]) == 3:
                unit_length = unit_data["dimensions"][2]["size"]
                unit_layers = 1
            elif len(unit_data["dimensions"]) == 4:
                unit_length = unit_data["dimensions"][3]["size"]
                unit_layers = unit_data["dimensions"][2]["size"]
            else:
                raise ValueError("Invalid number of dimensions")
            
            # sometimes the total number of frames is not divisible by the layer count; that is, not all layers have the final frame
            # to deal with this, and to make the length of the unit consistent across layers, we always ignore the last frame for multilayer files
            if unit_layers > 1:
                unit_length -= 1
            
            self.local_coords_min_z = movies_util.assert_none_or_equal(self.local_coords_min_z, (unit_data["measurementParams"]["MinZ"] if ("MinZ" in unit_data["measurementParams"]) else 0.0))
            self.local_coords_max_z = movies_util.assert_none_or_equal(self.local_coords_max_z, (unit_data["measurementParams"]["MaxZ"] if ("MaxZ" in unit_data["measurementParams"]) else 0.0))
            
            # TODO: these are more complicated structures, we can't just use assert_none_or_equal to compare them
            self.absolute_coords_rotation = scipy.spatial.transform.Rotation.from_quat(unit_data["rotationQuaternion"])
            self.absolute_coords_translation = np.array(unit_data["translation"])
            
            self.length += unit_length
            self.layers = movies_util.assert_none_or_equal(self.layers, unit_layers)
            self.units.append({"handle": unit_data["handle"][2], "length": unit_length, "start": (self.length - unit_length), "end": self.length})
            
            if unit_data["isBeingRecorded"]:
                if unit_index < len(self.session_data["measurements"]) - 1:
                    raise RuntimeError("Only the last measurement unit can be in the process of being recorded")
                else:
                    self.real_time = True
        
        if self.task_type in ["Resonant XY scan time series"]:
            self.invert_data = True
        elif self.task_type in ["AO full frame scan time series", "AO volume scan"]:
            self.invert_data = False
        else:
            raise ValueError("Unknown task type: " + self.task_type)
    
    def update_real_time(self):
        # it is simpler to just reload and reparse everything when waiting for the next frame during recording
        # if that is too slow, there is room for optimization here
        self.load_mesc_state()
        self.parse_file_data()
        self.parse_session_data()
        self.parse_unit_data()
    
    # TODO: potential room for optimization: request entire units instead of single frames
    def compute_mean_image(self):
        for unit_index, unit_data in enumerate(self.units):
            for frame_index in range(unit_data["start"], unit_data["end"]):
                channel_id = "%d,%d,%d,%d" % (self.file_handle, self.session_handle, unit_data["handle"], self.channel_handle)
                if self.layers == 1:
                    start_indices = "%d,%d,%d" % (0, 0, frame_index - unit_data["start"])
                    tile_sizes = "%d,%d,%d" % (self.size_x, self.size_y, 1)
                else:
                    start_indices = "%d,%d,%d,%d" % (0, 0, self.layer_index, frame_index - unit_data["start"])
                    tile_sizes = "%d,%d,%d,%d" % (self.size_x, self.size_y, 1, 1)
                """multiproc
                self.mesc_api.conn.send(['read', channel_id, start_indices, tile_sizes])
                byte_array = self.mesc_api.conn.recv()
                """
                self.mesc_api.conn['send'] = ['read', channel_id, start_indices, tile_sizes]
                self.mesc_api.p.event.set()
                while self.mesc_api.p.event.is_set():
                    time.sleep(10/1000)
                self.mesc_api.p.lock.acquire()
                byte_array = self.mesc_api.conn['rec']
                self.mesc_api.p.lock.release()
                #byte_array = femtoapi_wrapper.APIFunctions.readRawChannelDataToClientsBlob(self.mesc_api.conn, channel_id, start_indices, tile_sizes)
                
                loaded_dataset = np.flip(np.frombuffer(byte_array, dtype=np.uint16).reshape((self.size_y, self.size_x)), axis = 0).astype(float)
                if self.invert_data:
                    loaded_dataset = 65535 - loaded_dataset
                
                if frame_index == 0:
                    mean_image = loaded_dataset
                else:
                    mean_image = (float(frame_index) * mean_image + loaded_dataset) / float(frame_index + 1)
        
        return mean_image
    
    def load(self, frame_slice):
        if self.real_time:
            self.update_real_time()
        
        if frame_slice is None:
            frame_slice = slice(0, None)
        elif type(frame_slice) is not slice:
            raise TypeError("MESc loader can only deal with slices as frame indices")
        else:
            if (frame_slice.step is not None) and (frame_slice.step != 1):
                raise ValueError("MESc loader can only deal with single-stepping slices")
            
            if frame_slice.start is None:
                frame_slice = slice(0, frame_slice.stop)
            
            # when not loading frame-by-frame, we don't wait for more frames; the requested frames must be among the ones already present
            if (frame_slice.start < 0) or ((frame_slice.stop is not None) and frame_slice.stop >= self.length):
                raise ValueError("Frame slice extends beyond actual frame range")
        
        unit_datasets = []
        for unit_index, unit_data in enumerate(self.units):
            # we compute the intersection of the frame range requested, and the frame range contained in the unit
            # then we convert the global frame indices to frame indices relative to the start of this unit
            unit_range_start = max(frame_slice.start, unit_data["start"]) - unit_data["start"]
            unit_range_end = (min(frame_slice.stop, unit_data["end"]) if (frame_slice.stop is not None) else unit_data["end"]) - unit_data["start"]
            
            # if the intersection is empty, then no frames are needed from this unit
            if unit_range_start >= unit_range_end:
                continue
            
            unit_range_length = unit_range_end - unit_range_start
            
            channel_id = "%d,%d,%d,%d" % (self.file_handle, self.session_handle, unit_data["handle"], self.channel_handle)
            if self.layers == 1:
                start_indices = "%d,%d,%d" % (0, 0, unit_range_start)
                tile_sizes = "%d,%d,%d" % (self.size_x, self.size_y, unit_range_length)
            else:
                start_indices = "%d,%d,%d,%d" % (0, 0, self.layer_index, unit_range_start)
                tile_sizes = "%d,%d,%d,%d" % (self.size_x, self.size_y, 1, unit_range_length)
            """multiproc
            self.mesc_api.conn.send(['read', channel_id, start_indices, tile_sizes])
            byte_array = self.mesc_api.conn.recv()
            """
            self.mesc_api.conn['send'] = ['read', channel_id, start_indices, tile_sizes]
            self.mesc_api.p.event.set()
            while self.mesc_api.p.event.is_set():
                time.sleep(10/1000)
            self.mesc_api.p.lock.acquire()
            byte_array = self.mesc_api.conn['rec']
            self.mesc_api.p.lock.release()
            
            #byte_array = femtoapi_wrapper.APIFunctions.readRawChannelDataToClientsBlob(self.mesc_api.conn, channel_id, start_indices, tile_sizes)
            loaded_dataset = np.flip(np.frombuffer(byte_array, dtype=np.uint16).reshape((unit_range_length, self.size_y, self.size_x)), axis = 1)
            if self.invert_data:
                loaded_dataset = 65535 - loaded_dataset
            
            unit_datasets.append(loaded_dataset)
        
        return np.concatenate(unit_datasets, axis=0)

    def load_iter(self, frame_slice):
        if frame_slice is None:
            frame_slice = slice(0, None)
        elif type(frame_slice) is not slice:
            raise TypeError("MESc loader can only deal with slices as frame indices")
        else:
            if (frame_slice.step is not None) and (frame_slice.step != 1):
                raise ValueError("MESc loader can only deal with single-stepping slices")
            
            if frame_slice.start is None:
                frame_slice = slice(0, frame_slice.stop)
            
            if (frame_slice.start < 0):
                raise ValueError("Frame slice must not start before the zeroth frame")
        
        frame_index = frame_slice.start
        while True:
            if (frame_slice.stop is not None) and (frame_index >= frame_slice.stop):
                return
            
            if frame_index >= self.length:
                if not self.real_time:
                    return
                
                if frame_index >= self.length_override:
                    print("Warning: trying to process more frames than the length override, but caiman wouldn't be able to handle this, so the rest of the frames won't be processed. Set the length override higher to avoid this.")
                    return
                
                # we wait until either we receive the next frame, or the recording is stopped
                # we need to refresh the index ranges etc. of the units
                # minor optimization: if the first update already gets the frame (or shows that the recording is stopped), we avoid the sleep
                self.update_real_time()
                while self.real_time and (frame_index >= self.length):
                    time.sleep(0.001)
                    self.update_real_time()
                
                # if the recording is stopped, and we still don't have more frames, we are finished
                if frame_index >= self.length:
                    return
            
            unit_index = self.unit_index_of_frame(frame_index)
            unit_data = self.units[unit_index]
            
            channel_id = "%d,%d,%d,%d" % (self.file_handle, self.session_handle, unit_data["handle"], self.channel_handle)
            if self.layers == 1:
                start_indices = "%d,%d,%d" % (0, 0, frame_index - unit_data["start"])
                tile_sizes = "%d,%d,%d" % (self.size_x, self.size_y, 1)
            else:
                start_indices = "%d,%d,%d,%d" % (0, 0, self.layer_index, frame_index - unit_data["start"])
                tile_sizes = "%d,%d,%d,%d" % (self.size_x, self.size_y, 1, 1)
            """multiproc
            self.mesc_api.conn.send(['read', channel_id, start_indices, tile_sizes])
            byte_array = self.mesc_api.conn.recv()
            """
            self.mesc_api.conn['send'] = ['read', channel_id, start_indices, tile_sizes]
            self.mesc_api.p.event.set()
            while self.mesc_api.p.event.is_set():
                time.sleep(10/1000)
            self.mesc_api.p.lock.acquire()
            byte_array = self.mesc_api.conn['rec']
            self.mesc_api.p.lock.release()
            
            #byte_array = femtoapi_wrapper.APIFunctions.readRawChannelDataToClientsBlob(self.mesc_api.conn, channel_id, start_indices, tile_sizes)
            loaded_frame = np.flip(np.frombuffer(byte_array, dtype=np.uint16).reshape((self.size_y, self.size_x)), axis = 0)
            if self.invert_data:
                loaded_frame = 65535 - loaded_frame
            
            yield loaded_frame
            
            frame_index += 1

