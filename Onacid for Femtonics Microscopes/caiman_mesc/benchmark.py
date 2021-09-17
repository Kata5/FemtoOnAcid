#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

class SimpleOnACIDBenchmark:
    def __init__(self, print_modulo):
        self.start_time = time.time()
        self.print_modulo = print_modulo # framerate/time is only printed every print_modulo frames; set to zero or negative to print every frame
    
    def print_benchmark(self, frame_count):
        if (self.print_modulo <= 0) or (frame_count % self.print_modulo == 0):
            print("Average framerate: ", frame_count / (time.time() - self.start_time))
            #print("Average time: ", (time.time() - self.start_time) / frame_count)
