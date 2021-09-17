#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tkinter
from datetime import date, datetime
import math

import numpy as np
import cv2
import matplotlib.pyplot as plt
import caiman.utils.visualization
import time
from tkinter import messagebox

from matplotlib.widgets import CheckButtons

from . import movies

# a class to generate random colors for each ROI, and then store them so that they are consistent across frames and the different plots
class ComponentColoringScheme:
    def __init__(self, random_seed=1234):
        self.random_seed = random_seed
        self.rngs = []
        self.colors = []

    def __getitem__(self, key):
        layer_index = movies.mesc_state.mesc_params.layer_index
        while layer_index >= len(self.colors):
            self.rngs.append(np.random.default_rng(self.random_seed + len(self.colors)))
            self.colors.append([])
        
        while key >= len(self.colors[layer_index]):
            self.colors[layer_index].append(self.random_nongreen_color2(self.rngs[layer_index]))
        
        return self.colors[layer_index][key]

    def random_color(self, rng):
        r = int(rng.integers(256))
        g = int(rng.integers(256))
        b = int(rng.integers(256))
        return (r, g, b)

    def random_saturated_color(self, rng):
        val1 = int(rng.integers(6))
        val2 = int(rng.integers(255))
        if val1 == 0:
            color = (255, val2, 0)
        elif val1 == 1:
            color = (255 - val2, 255, 0)
        elif val1 == 2:
            color = (0, 255, val2)
        elif val1 == 3:
            color = (0, 255 - val2, 255)
        elif val1 == 4:
            color = (val2, 0, 255)
        else:
            color = (255, 0, 255 - val2)

        return color
    
    def random_nongreen_saturated_color(self, rng):
        val1 = int(rng.integers(2))
        val2 = int(rng.integers(256))
        if val1 == 0:
            color = (0, val2, 255)
        else:
            color = (255, val2, 0)

        return color
    
    def random_nongreen_color(self, rng):
        val1 = int(rng.integers(256))
        val2 = int(rng.integers(256))
        color = (val1, val2, 255 - val1)

        return color
    
    def random_nongreen_color2(self, rng):
        val1 = int(rng.integers(256))
        val2 = int(rng.integers(val1 + 1))
        color = (val1, 255 - val2, 255 - val1 + val2)
        
        return color

# a class to show the current movie frame overlaid with colored contours of each ROI
class ContourPlot:
    def __init__(self, component_coloring_scheme, resize_factor=1.0):
        self.window_name = "Component contours"
        
        self.frame_color_map = np.empty([256, 1, 3], dtype=np.uint8)
        for i in range(0, 256):
            # creating a colormap ranging from black to green
            self.frame_color_map[i, 0, :] = [0, i, 0] # opencv uses a BGR ordered tuple for colors
        
        self.resize_factor = resize_factor
        self.recompute_countours_modulo = -1  # contours are recomputed every this many frames. set to zero or negative to disable recomputing completely
        self.component_coloring_scheme = component_coloring_scheme
        self.contour_line_width = 2
        self.contours = []
        self.window_shape = None

        self.first_run = True

        self.label_position = {}

        self.selected_roi_x = -1
        self.selected_roi_y = -1

        self.exit_program = False
    
    # mouse callback function
    def select_ROI(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK: # or event == cv2.EVENT_LBUTTONDOWN:
            self.selected_roi_x = x
            self.selected_roi_y = y
            print("x, y = ", x, y)

    def get_exitprogram(self):
        return self.exit_program

    def reset(self):
        self.contours = []

    def compute_label_position(self, contour):
        x_min = np.inf
        x_max = -np.inf
        y_min = np.inf
        y_max = -np.inf
        for loop in contour:
            x_min = min(x_min, np.amin(loop[:, :, 0]))
            x_max = max(x_max, np.amax(loop[:, :, 0]))
            y_min = min(y_min, np.amin(loop[:, :, 1]))
            y_max = max(y_max, np.amax(loop[:, :, 1]))
        
        # we place the label in the upper right corner
        # in opencv's coordinates, the origin is the upper left corner, so the upper right corner is (x_max, y_min)
        return (x_max, y_min)

    def confirm_exit(self):
        if messagebox.askyesno("Confirm",
                               "By closing the window would you like to stop the algorithm as well?"):
            self.exit_program = True

    def show(self, frame, frame_count, components, component_count):
        # we need to convert the frame to 8-bit unsigned ints for opencv
        frame_processed = (255 * np.clip(frame, 0, 1)).astype(np.uint8)

        # if recompute_countours_modulo is zero or negative, we keep the original contours forever
        # otherwise, after every recompute_countours_modulo frames we reset the cached contours, which triggers a recompute of everything
        if (self.recompute_countours_modulo > 0) and ((frame_count - 1) % self.recompute_countours_modulo == 0):
            self.contours = []

        new_component_count = component_count - len(self.contours)
        if new_component_count > 0:
            # the component array contains both the foreground and the background components
            # the last columns are the foreground components, and we only need to compute the contour for the last component_count columns,
            # since the earlier ones have already been there in the previous frames, and we have already stored the contour for them
            # the thr_method and thr params are from caiman's own plot_contours function
            new_contours = caiman.utils.visualization.get_contours(components[:, -new_component_count:],
                                                                   np.shape(frame_processed), thr_method='max', thr=0.2)

            for contour in new_contours:
                # the component might be non-contiguous, which means the contour may be multiple disconnected loops
                # for each region (thus, contour loop) the coordinates array contains a block of points, delimited by NaNs. the first and last rows are also NaNs.
                # so we split the array by those NaNs, and store the loops in an array
                coords = contour["coordinates"]
                indices = np.where(np.any(np.isnan(coords), axis=1))[0]

                contour_processed = []
                for i in range(0, len(indices) - 1):
                    contour_processed.append((coords[None, (indices[i] + 1):(indices[i + 1]), :] * self.resize_factor).astype(int))

                self.contours.append(contour_processed)

        # to draw colored contours on the frame, we have to convert the frame to a color image,
        # and we don't necessarily want to stick to simple grayscale, so we use a general colormap
        frame_with_contours = cv2.applyColorMap(frame_processed, self.frame_color_map)
        self.window_shape = (int(frame.shape[0] * self.resize_factor), int(frame.shape[1] * self.resize_factor))
        if self.resize_factor != 1.0:
            frame_with_contours = cv2.resize(frame_with_contours, self.window_shape)
        
        for index, contour in enumerate(self.contours):
            # the components are colored differently, but if a component is disconnected (thus, the contour has multiple loops), we draw each loop with the same color
            color = self.component_coloring_scheme[index]
            color_bgr = (color[2], color[1], color[0])  # opencv expects the color as a BGR ordered tuple
            frame_with_contours = cv2.drawContours(frame_with_contours, contour, -1, color_bgr, self.contour_line_width)

            # save the coordinates of the new POIs: first run or new point added
            if index not in self.label_position or self.first_run:
                self.label_position[index] = self.compute_label_position(contour)
            
            frame_with_contours = cv2.putText(frame_with_contours, str(index + 1), self.label_position[index], cv2.FONT_HERSHEY_TRIPLEX, 1, color_bgr, 1)

        if not self.first_run:
            prop = cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE)
            if prop == 0:
                self.confirm_exit()
                
        cv2.startWindowThread()
        cv2.namedWindow(self.window_name)
        cv2.imshow(self.window_name, frame_with_contours)
        cv2.waitKey(1)

        # if first run set mouse callback
        if self.first_run:
            cv2.setMouseCallback(self.window_name, self.select_ROI)
            self.first_run = False

        # ugly hack to ensure that this works both with and without the dummy Qt app needed by the MESc API
        if not movies.mesc_state.has_qapp():
            cv2.waitKey(1)


# a class to show the raw and inferred activities of each ROI
class ActivityPlot:
    def __init__(self, component_coloring_scheme):
        self.component_coloring_scheme = component_coloring_scheme
        self.linewidth_raw = 3
        self.linewidth_inferred = 1
        self.rows = movies.mesc_state.mesc_params.activity_plot_rows
        self.cols = movies.mesc_state.mesc_params.activity_plot_cols
        self.xoffset = movies.mesc_state.mesc_params.activity_plot_x_offset

        # self.fig = None
        self.figList = []
        self.outer_gridList = []
        self.axes = []
        self.lines = []
        self.chekboxList = []

        self.saved_component_count = 0

        self.exit_program = False

    def __del__(self):
        for fig in self.figList:
            fig.clear()
        
    def reset(self):
        for fig in self.figList:
            fig.clf()
        self.figList = []
        self.outer_gridList = []
        self.axes = []
        self.lines = []
        self.chekboxList = []

        self.saved_component_count = 0

    def get_exitprogram(self):
        return self.exit_program

    def confirm_exit(self, event):
        if messagebox.askyesno("Confirm",
                               "By closing the window would you like to stop the algorithm as well?"):
            self.exit_program = True
        self.reset()

    def show(self, C, noisyC, frame_count, component_count, background_component_count):
        # checkbox callback
        def func(label):
            print("label %s" % (label))

        component_count_to_plot = min(component_count, self.rows * self.cols)

        # temporary solution: sometimes the component_count increases
        if self.saved_component_count == 0 or component_count_to_plot != self.saved_component_count:
            self.saved_component_count = component_count_to_plot
        #elif component_count_to_plot != self.saved_component_count:
            #self.reset()
            #return
        else:
            component_count = self.saved_component_count

        plot_num = component_count // component_count_to_plot + 1
        if component_count % component_count == 0:
            plot_num = plot_num - 1

        if len(self.figList) == 0:
            for i in range(0, plot_num):
                caption = "Component activity "
                if plot_num > 1:
                    caption = caption + str(i + 1)
                self.figList.append(plt.figure(caption, figsize=(self.rows * 2, self.cols), constrained_layout=False))
                self.outer_gridList.append(self.figList[i].add_gridspec(self.rows, self.cols, wspace=0, hspace=0))
                self.figList[i].canvas.mpl_connect('close_event', self.confirm_exit)

        # we construct and store axes and line objects for the new components, if there are any
        # for index in range(len(self.lines), component_count_to_plot):
        localrow = 0
        localcol = 0

        a = 0
        b = 0
        graphindex = 1

        if len(self.lines) > 0:
            for index in range(len(self.lines)):
                graphindex += 1

                a += 1
                if a == self.cols:
                    a = 0
                    b += 1
                if b == self.rows:
                    b = 0

        for index in range(len(self.lines), component_count_to_plot):
            plot_index = index // component_count_to_plot

            # checkbox : graph size = 1:3
            kw = dict(
                wspace=0,
                hspace=0,
                width_ratios=[1, 3],
                # height_ratios=height_ratios,
            )

            inner_grid = self.outer_gridList[plot_index][b, a].subgridspec(1, 2, **kw)

            axes = None
            with plt.style.context("seaborn-white"):
                plt.rcParams["axes.linewidth"] = 0

                axes = inner_grid.subplots()
                localcol = localcol + 1

                color = self.component_coloring_scheme[index]
                color_float = (color[0] / 255, color[1] / 255,
                               color[2] / 255)  # pyplot expects color components as floats in the [0,1] range
                line_raw2, = axes[1].plot([], [], color=color_float, linewidth=self.linewidth_raw)
                line_inferred2, = axes[1].plot([], [], color='k', linewidth=self.linewidth_inferred)

                # no border, bottom: show axis units, top: space for upper axis numbers
                plt.subplots_adjust(left=0, right=.99, top=.98, bottom=0.05)
                self.lines.append({"raw": line_raw2, "inferred": line_inferred2})

            labels = [str(graphindex)]
            graphindex += 1
            visibility = [False]
            check = CheckButtons(axes[0], labels, visibility)
            self.chekboxList.append(check)
            check.on_clicked(func)

            localrow = localrow + 0.5
            if localrow == self.rows:
                localrow = 0
            localcol = localcol + 1
            if localcol == (self.cols * 2):
                localcol = 0
            self.axes.append(axes[0])
            self.axes.append(axes[1])

            a += 1
            if a == self.cols:
                a = 0
                b += 1
            if b == self.rows:
                b = 0

        for index in range(0, self.saved_component_count):
            # onacid stores the background components first, then the neurons
            # so the first non-background components has the index background_component_count
            component_index = background_component_count + index

            graph_index = index * 2 + 1

            if self.xoffset == 0:
                self.lines[index]["raw"].set_xdata(np.arange(frame_count))
                self.lines[index]["inferred"].set_xdata(np.arange(frame_count))
            else:
                self.lines[index]["raw"].set_xdata(np.arange((frame_count - self.xoffset), frame_count))
                self.lines[index]["inferred"].set_xdata(np.arange((frame_count - self.xoffset), frame_count))

            if self.xoffset == 0:
                self.lines[index]["raw"].set_ydata(noisyC[component_index, 0:frame_count])
                self.lines[index]["inferred"].set_ydata(C[component_index, 0:frame_count])
            else:
                self.lines[index]["raw"].set_ydata(noisyC[component_index, (frame_count - self.xoffset):frame_count])
                self.lines[index]["inferred"].set_ydata(C[component_index, (frame_count - self.xoffset):frame_count])

            # we could also do self.axes[index].relim() followed by self.axes[index].autoscale_view()
            # but computing the limits manually is more efficient

            padding_x = 0
            if self.xoffset == 0:
                padding_x = 0.05 * frame_count
            else:
                padding_x = 0.05 * self.xoffset

            if self.xoffset == 0:
                self.axes[graph_index].set_xlim((0 - padding_x, frame_count + padding_x))
                # self.axes[graph_index].axvline(x=0, color='k')
            else:
                self.axes[graph_index].set_xlim((frame_count - padding_x - self.xoffset, frame_count + padding_x))
                # self.axes[graph_index].axvline(x=frame_count - self.xoffset, color='k')

            self.axes[graph_index].axhline(y=0, color='k')

            # TODO: potential room for optimization: store the min/max values, and only take the min/max with the newest array elements
            C_min = 0
            noisyC_min = 0

            C_max = 0
            noisyC_max = 0
            
            if self.xoffset == 0:
                C_min = float(np.amin(C[component_index, 0:frame_count]))
                noisyC_min = float(np.amin(noisyC[component_index, 0:frame_count]))

                C_max = float(np.amax(C[component_index, 0:frame_count]))
                noisyC_max = float(np.amax(noisyC[component_index, 0:frame_count]))
            else:
                C_min = float(np.amin(C[component_index, (frame_count - self.xoffset):frame_count]))
                noisyC_min = float(np.amin(noisyC[component_index, (frame_count - self.xoffset):frame_count]))

                C_max = float(np.amax(C[component_index, (frame_count - self.xoffset):frame_count]))
                noisyC_max = float(np.amax(noisyC[component_index, (frame_count - self.xoffset):frame_count]))

            value_min = min(C_min, noisyC_min)
            value_max = max(C_max, noisyC_max)

            padding_y = 0.05 * (value_max - value_min)
            self.axes[graph_index].set_ylim((value_min - padding_y, value_max + padding_y))

            step = 1
            if math.floor(value_min) == 0:
                step = math.ceil(value_max / 4)
            else:
                step = math.ceil((math.ceil(value_max) - math.floor(value_min)) / 4)
            if step == 0:
                step = 1
            self.axes[graph_index].set_yticks(np.arange(math.floor(value_min) - 1, math.ceil(value_max) + 1, step))

        # ugly hack to ensure that this works both with and without the dummy Qt app needed by the MESc API
        if not movies.mesc_state.has_qapp():
            for i in range(0, plot_num):
                self.figList[i].canvas.draw_idle()
                self.figList[i].canvas.flush_events()
