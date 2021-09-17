#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tkinter import *
from tkinter import filedialog
from collections import OrderedDict
from tkscrolledframe import ScrolledFrame
import json
import re
import os.path

class GUI():

    # Define settings upon initialization. Here you can specify
    def __init__(self, master=None, nogui=False):
        self.params = {
            "files": {
                "name": "MESc input files",
                "type": "filelist",
                "default_value": [],
                "description": "",
            },
            "decay_time": {
                "name": "Decay Time",
                "type": float,
                "default_value": 0.4,
                "description": "Length of a typical transient in seconds. decay_time is an approximation of the time scale over which to expect a significant shift in the calcium signal during a transient. It defaults to 0.4, which is appropriate for fast indicators (GCaMP6f), slow indicators might use 1 or even more. However, decay_time does not have to precisely fit the data, approximations are enough.",
            },
            "gSig": {
                "name": "Half-Size of Neurons",
                "type": "pair",
                "default_value": [6, 6],
                "description": "Expected half-size of neurons in pixels [rows X columns]. CRUCIAL parameter for proper component detection.",
            },
            "p": {
                "name": "Order of AR Indicator Dynamics",
                "type": int,
                "default_value": 2,
                "description": "Order of the autoregressive model. p = 0 turns deconvolution off. If transients in your data rise instantaneously, set p = 1 (occurs at low sample rate or slow indicator). If transients have visible rise time, set p = 2. If the wrong order is chosen, spikes are extracted unreliably.",
            },
            "ds_factor": {
                "name": "Spatial Downsampling Factor",
                "type": int,
                "default_value": 1,
                "description": "Spatial downsampling factor (increases speed but may lose some fine structure).",
            },
            "gnb": {
                "name": "Number of Background Components",
                "type": int,
                "default_value": 2,
                "description": "Number of global background components. This is a measure of the complexity of your background noise. Defaults to nb = 2, assuming a relatively homogeneous background. nb = 3 might fit for more complex noise, nb = 1 is usually too low. If nb is set too low, extracted traces appear too noisy, if nb is set too high, neuronal signal starts getting absorbed into the background reduction, resulting in reduced transients.",
            },
            "online_MC": {
                "name": "Enable Online Motion Correction",
                "type": bool,
                "default_value": True,
                "description": "Flag for online motion correction.",
            },
            "pw_rigid": {
                "name": "Enable PW-Rigid Motion Correction",
                "type": bool,
                "default_value": False,
                "description": "Flag for pw-rigid motion correction (slower but potentially more accurate).",
            },
            "max_shifts_online": {
                "name": "Maximum Shift",
                "type": int,
                "default_value": 60,
                "description": "Maximum shifts for motion correction during online processing.",
            },
            "thresh_CNN_noisy": {
                "name": "Online CNN Threshold",
                "type": float,
                "default_value": 0.7,
                "description": "Threshold for the online CNN classifier. Greater thresholds find better components but may not find as many components. Set to 0.5 for higher recall values, but at the expense of lower precision. Set to 0.7 for higher precision values, but at the expense of lower recall.",
            },
            "min_SNR": {
                "name": "Min Signal-Noise-Ratio (SNR)",
                "type": float,
                "default_value": 1.5,
                "description": "Minimum SNR Threshold for detecting new components. Peak SNR is calculated from strong calcium transients and the noise estimate. Set to 1.0 for higher recall values, but at the expense of lower precision. Set to 1.5 for higher precision values, but at the expense of lower recall.",
            },
            "min_num_trial": {
                "name": "Min Number of Candidates",
                "type": int,
                "default_value": 5,
                "description": "Number of candidate components to be considered at each timestep. Set to 10 for higher recall values, but at the expense of lower precision. Set to 5 for higher precision values, but at the expense of lower recall.",
            },
            "epochs": {
                "name": "Epochs",
                "type": int,
                "default_value": 1,
                "description": "Number of passes over the data. This increases the time per MUnit but is beneficial for finding more components, especially in the strict regime or high acceptance thresholds.",
            },
            "rval_thr": {
                "name": "Spatial Footprint Consistency",
                "type": float,
                "default_value": 0.8,
                "description": "The spatial footprint of the component is compared with the frames where this component is active. Other component’s signals are subtracted from these frames, and the resulting raw data is correlated against the spatial component. This ensures that the raw data at the spatial footprint aligns with the extracted trace.",
            },
            "init_batch": {
                "name": "Frames for Initialization",
                "type": int,
                "default_value": 100,
                "description": "Number of frames for initialization.",
            },
            "K": {
                "name": "Initial Number of Components",
                "type": int,
                "default_value": 5,
                "description": "Initial number of components.",
            },
            "layer_names": {
                "name": "Which layers to process",
                "type": str,
                "default_value": "*",
                "description": "Which layers to process from MESc files. If set to a comma-separated list of (one-based) layer indices, then only those layers will be processed. If set to the special value '*', every layer is processed.",
            },
            "compute_mean_images": {
                "name": "Save mean images",
                "type": bool,
                "default_value": False,
                "description": "If set, then the CaImAn-MESc module will compute the average of all frames for each layer before processing that layer and save them in the output folder.",
            },
            "show_plots": {
                "name": "Show CaImAn-MESc plots",
                "type": bool,
                "default_value": True,
                "description": "If set, then the CaImAn MESc module will visualize the partial results during the OnACID. Currently, two plots are shown: a plot with the ROI contours overlaid on the current frame, and a plot showing the activity of each component.",
            },
            "contour_plot_scale": {
                "name": "Contour plot rescale factor",
                "type": float,
                "default_value": 1.0,
                "description": "The contour plot window is rescaled by this factor.",
            },
            "export_centers": {
                "name": "Put ROI centers on clipboard",
                "type": bool,
                "default_value": True,
                "description": "If set, then the CaImAn MESc module will put the current ROI centers on the clipboard every 100 frames during OnACID. The format is consistent with the one used by MESc.",
            },
            "save_results": {
                "name": "Save OnACID results",
                "type": bool,
                "default_value": False,
                "description": "If set, then the OnACID results will be dumped as a separate .hdf5 file for each layer. The HDF5 structure is CaImAn's own, and is based on the fields of the OnACID Python object.",
            },
            "save_mescroi": {
                "name": "Save contours as .mescroi",
                "type": bool,
                "default_value": False,
                "description": "If set, then the contours of the ROIs will be saved as a separate .mescroi file for each layer so they can be imported into the MESc GUI.",
            },
            "length_override": {
                "name": "Max number of real-time frames",
                "type": int,
                "default_value": 1000,
                "description": "CaImAn needs the total number of frames in advance to preallocate its arrays. When processing real-time data, this is not available, so we pass an upper estimate to CaImAn, and after the run, we truncate the arrays to the actual movie length. Has no effect when not running in real time.",
            },
            "real_time_save_dir": {
                "name": "Results folder for real-time data",
                "type": "dir",
                "default_value": "",
                "description": "When working from a file, all results are saved into the same directory as the input. When using real-time data, the the \"input file\" is just a quasi-path provided by the MESc GUI, so results will be saved into this directory instead. Has no effect when not running in real time.",
            },
            "activity_plot_rows": {
                "name": "Activity plot rows",
                "type": int,
                "default_value": 5,
                "description": "Number of rows for the CaImAn-MESc activity plot.",
            },
            "activity_plot_cols": {
                "name": "Activity plot columns",
                "type": int,
                "default_value": 8,
                "description": "Number of columns for the CaImAn-MESc activity plot.",
            },
            
            # NOTE: these are commented out because they don't correspond to any CaImAn parameter
            #"component_area_thr": {
                #"name": "Component Area Threshold",
                #"type": int,
                #"default_value": 100,
                #"description": "Sets the minimum area threshold (in pixels) in which components (ROIS) much be larger than to be accepted.",
            #},
            #"generate_dff": {
                #"name": "Generate DFF traces",
                #"type": bool,
                #"default_value": True,
                #"description": "",
            #},
        }
        
        self.sections = [
            {
                "label": "Please select MESc file(s):",
                "params": ["files"],
            },
            {
                "label": "DATA PARAMETERS",
                "params": ["decay_time", "gSig", "p", "ds_factor", "gnb"],
            },
            {
                "label": "MOTION CORRECTION",
                "params": ["online_MC", "pw_rigid", "max_shifts_online"],
            },
            {
                "label": "ALGORITHM PARAMETERS",
                "params": ["thresh_CNN_noisy", "min_SNR", "min_num_trial", "epochs", "rval_thr", "init_batch", "K"],
            },
            {
                "label": "MESC-SPECIFIC PARAMETERS",
                "params": ["layer_names", "compute_mean_images", "show_plots", "contour_plot_scale", "export_centers", "save_results", "save_mescroi", "length_override", "real_time_save_dir", "activity_plot_rows", "activity_plot_cols"],
            },
            
            # NOTE: these are commented out because they don't correspond to any CaImAn parameter
            #{
                #"label": "EVALUATION PARAMETERS",
                #"params": ["component_area_thr", "generate_dff"],
            #},
        ]
        
        # a small self-check to ensure that params added in the future are also added to a section
        for param in self.params:
            found = False
            for section in self.sections:
                if param in section["params"]:
                    found = True
            
            if not found:
                raise RuntimeError("The MESc GUI param '" + param + "' was specified but not added to any of the sections!")
        
        self.values = {}
        for param in self.params:
            self.values[param] = self.params[param]["default_value"]
        
        self.load_params()
        
        # we have the param values set up from the json and/or the defaults; if the program was started with the "nogui" option, then we are done
        if nogui:
            return

        self.init_window()
        self.build_gui()
        self.set_field_values()

        # bring window to the front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)

        self.root.mainloop()
    
    # Creation of init_window
    def init_window(self):
        self.root = Tk()
        self.root.title("MESc OnACID")
        self.root.geometry("650x950")

        # Create a ScrolledFrame widget
        sf = ScrolledFrame(self.root)
        sf.pack(side="top", expand=1, fill="both")

        # Bind the arrow keys and scroll wheel
        sf.bind_arrow_keys(self.root)
        sf.bind_scroll_wheel(self.root)

        # Create a frame within the ScrolledFrame
        self.inner_frame = sf.display_widget(Frame)

    def build_gui(self):
        self.gui_elements = []
        self.input_variables = {}
        
        current_row = 0
        for section in self.sections:
            label = Label(self.inner_frame, text = section["label"], font = 'BOLD')
            label.grid(column = 0, row = current_row)
            self.gui_elements.append(label)
            
            current_row += 1
            
            for param in section["params"]:
                if self.params[param]["type"] == "filelist":
                    self.input_variables[param] = []
                    
                    file_count = len(self.values[param])
                    for index in range(0, file_count):
                        input_variable = StringVar()
                        self.input_variables[param].append(input_variable)
                        
                        input_field = Entry(self.inner_frame, width = 50, textvariable = input_variable)
                        input_field.grid(column = 1, row = current_row, columnspan = 2)
                        self.gui_elements.append(input_field)
                        
                        browse_button = Button(self.inner_frame, text = "...", command = lambda param=param, index=index: self.open_file_browser(param, index))
                        browse_button.grid(column = 3, row = current_row)
                        self.gui_elements.append(browse_button)
                        
                        current_row += 1
                    
                    add_file_button = Button(self.inner_frame, text = "+", command = lambda param=param: self.add_file_input(param))
                    add_file_button.grid(column = 2, row = current_row, sticky = E)
                    self.gui_elements.append(add_file_button)
                    
                    remove_file_button = Button(self.inner_frame, text = "-", command = lambda param=param: self.remove_file_input(param))
                    remove_file_button.grid(column = 3, row = current_row, sticky = W)
                    self.gui_elements.append(remove_file_button)
                    
                    current_row += 1
                elif self.params[param]["type"] == "dir":
                    label = Label(self.inner_frame, text = (self.params[param]["name"] + ": "))
                    label.grid(column = 1, row = current_row, sticky = E)
                    self.gui_elements.append(label)
                    
                    input_variable = StringVar()
                    self.input_variables[param] = input_variable
                    
                    input_field = Entry(self.inner_frame, width = 20, textvariable = input_variable)
                    input_field.grid(column = 2, row = current_row, sticky = W)
                    self.gui_elements.append(input_field)
                    
                    browse_button = Button(self.inner_frame, text = "...", command = lambda param=param: self.open_directory_chooser(param))
                    browse_button.grid(column = 3, row = current_row)
                    self.gui_elements.append(browse_button)
                    
                    current_row += 1
                else:
                    label = Label(self.inner_frame, text = (self.params[param]["name"] + ": "))
                    label.grid(column = 1, row = current_row, sticky = E)
                    self.gui_elements.append(label)
                    
                    if self.params[param]["type"] == int:
                        input_variable = IntVar()
                        input_field = Entry(self.inner_frame, width = 5, textvariable = input_variable)
                    elif self.params[param]["type"] == float:
                        input_variable = DoubleVar()
                        input_field = Entry(self.inner_frame, width = 5, textvariable = input_variable)
                    elif self.params[param]["type"] == bool:
                        input_variable = BooleanVar()
                        input_field = Checkbutton(self.inner_frame, variable = input_variable)
                    elif self.params[param]["type"] == str:
                        input_variable = StringVar()
                        input_field = Entry(self.inner_frame, width = 5, textvariable = input_variable)
                    elif self.params[param]["type"] == "pair":
                        input_variable = StringVar()
                        input_field = Entry(self.inner_frame, width = 5, textvariable = input_variable)
                    else:
                        raise RuntimeError("Unknown param type")
                    
                    self.input_variables[param] = input_variable
                    input_field.grid(column = 2, row = current_row, sticky = W)
                    self.gui_elements.append(input_field)
                    
                    info_button = Button(self.inner_frame, text = "?", command = lambda param=param: self.show_param_description(param))
                    info_button.grid(column = 3, row = current_row)
                    self.gui_elements.append(info_button)
                    
                    current_row += 1
        
        run_button = Button(self.inner_frame, text="RUN PROGRAM", font=("Helvetica", 12), command = self.run_program, height = 2, width = 15, bg = "gray64")
        run_button.grid(column = 2, row = current_row, sticky = W)
        self.gui_elements.append(run_button)
        
        current_row += 1
    
    def clear_gui(self):
        for gui_element in self.gui_elements:
            gui_element.destroy()
        
        self.gui_elements = []
        self.input_variables = []
    
    def get_field_values(self):
        for param in self.params:
            param_value = None
            
            if self.params[param]["type"] == "filelist":
                param_value = []
                for input_variable in self.input_variables[param]:
                    param_value.append(input_variable.get())
            else:
                input_field_value = self.input_variables[param].get()
                
                if self.params[param]["type"] == int:
                    param_value = input_field_value
                elif self.params[param]["type"] == float:
                    param_value = input_field_value
                elif self.params[param]["type"] == bool:
                    param_value = input_field_value
                elif self.params[param]["type"] == str:
                    param_value = input_field_value
                elif self.params[param]["type"] == "pair":
                    result = re.match("\\[(\\d+)\\s*,\\s*(\\d+)\\]", input_field_value)
                    if result:
                        param_value = [int(result.group(1)), int(result.group(2))]
                    else:
                        raise RuntimeError("Invalid value entered for param " + param)
                elif self.params[param]["type"] == "dir":
                    param_value = input_field_value
                else:
                    raise RuntimeError("Unknown parameter type")
            
            self.values[param] = param_value
    
    def set_field_values(self):
        for param in self.params:
            param_value = self.values[param]
            
            if self.params[param]["type"] == "filelist":
                for index, input_variable in enumerate(self.input_variables[param]):
                    input_variable.set(param_value[index])
            else:
                input_variable = self.input_variables[param]
                
                if self.params[param]["type"] == int:
                    input_variable.set(param_value)
                elif self.params[param]["type"] == float:
                    input_variable.set(param_value)
                elif self.params[param]["type"] == bool:
                    input_variable.set(param_value)
                elif self.params[param]["type"] == str:
                    input_variable.set(param_value)
                elif self.params[param]["type"] == "pair":
                    input_variable.set("[%d, %d]" % (param_value[0], param_value[1]))
                elif self.params[param]["type"] == "dir":
                    input_variable.set(param_value)
                else:
                    raise RuntimeError("Unknown param type")
    
    def open_file_browser(self, param, index):
        current_file = self.input_variables[param][index].get()
        current_dir = os.path.dirname(current_file)
        new_file = filedialog.askopenfilename(initialdir = current_dir, title = "Select file", filetypes = (("MESc files", "*.mesc"), ("all files", "*.*")))
        if new_file:
            self.input_variables[param][index].set(new_file)
    
    def open_directory_chooser(self, param):
        current_dir = self.input_variables[param].get()
        new_dir = filedialog.askdirectory(initialdir = current_dir, title = "Select directory")
        if new_dir:
            self.input_variables[param].set(new_dir)
    
    def add_file_input(self, param):
        self.get_field_values()
        self.clear_gui()
        
        self.values[param].append("")
        
        self.build_gui()
        self.set_field_values()
    
    def remove_file_input(self, param):
        self.get_field_values()
        self.clear_gui()
        
        self.values[param].pop()
        
        self.build_gui()
        self.set_field_values()

    def run_program(self):
        self.get_field_values()
        self.save_params()
        
        # we destroy everything and terminate the main loop
        self.root.destroy()
        self.root.quit()

    def show_param_description(self, param):
        description_window = Toplevel()
        description_window.geometry('400x200')
        description_window.attributes('-topmost', 'true')
        
        display = Label(description_window, text = self.params[param]["description"], wraplength = 380, anchor = 'w', font = 'TkDefaultFont 11')
        display.pack()
    
    def load_params(self):
        json_data = {}
        try:
            with open("mesc_params.json", "r") as f:
                json_data = json.load(f)
        except Exception as e:
            print("Warning: no mesc_params.json was found, falling back to default parameter values")
        
        # we iterate over the params we know about, and only use the values for valid params
        for param in self.params:
            if param in json_data:
                self.values[param] = json_data[param]
        
    def save_params(self):
        try:
            with open("mesc_params.json", "w") as f:
                json.dump(self.values, f, indent = 4)
        except Exception as e:
            print("Warning: failed to write parameter values to mesc_params.json")
