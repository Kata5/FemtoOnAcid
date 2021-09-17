# FemtoOnAcid
Online Analysis of Calcium Imaging Data in Real Time for Femtonics Microscopes


Femtonics Real-time Analysis Package enables you online analyze your data measured with Femtonics AO microscope via FemtoAPI <<link>> while your measurement is still running. You can exploit the benefits of this great advantage when online information from network dynamic is essential (i.e.: when performing photoStimulation)

Fast and scalable algorithms are implemented for

    *online motion correction
    *automatic source extraction, cell detection
    *calculationg and stroring cell centroids in a txt file and on the clipboard
    *providing and visualizing Ca traces real-time

With the package the following measurements can be processed:

    2D High Speed Arbitrary Frames Scans (Raster Scans)
    3D VolumeScan and
    3D Multilayer 

The package is based on the popular CaImAn package of Flatiron Institute, a paper explaining most of the implementation details and benchmarking can be found here. The code can be updated with algorithm from GitHub any time while codes for accessing data measured with Femtonics microscopes will not be changed.

The algorithm can be either finetuned with a GUI containing parameters for the data, for algorithm, etc or without GUI with default parameters.


Ca traces are visualized real time and using the check boxes next to the cells a subpopulation of cells can be selected so as to forward them to further measurements (i.e. chessboard scanning)

Requirements

Femtonics Real-time Analysis Package is supported

    on Windows on Intel CPUs,
    CaImAn presently targets Python 3.7, parts of CaImAn are written in C++, but apart possibly during install, this is not visible to the user
    Conda
    FemtoAPI <<link>> from Femtonics Ltd is required for online analysis. At least 16G RAM is strongly recommended, and depending on datasets, 32G or more may be helpful.
