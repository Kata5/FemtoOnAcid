# FemtoOnAcid
Online Analysis of Calcium Imaging Data in Real Time for Femtonics Microscopes.
This project has been partially funded through the Hungarian Brain Research Program.


Femtonics Real-time Analysis Package enables you online analyze your data measured with Femtonics AO microscope via [FemtoAPI](https://github.com/Femtonics/FemtoAPI) while your measurement is still running. You can exploit the benefits of this great advantage when online information from network dynamic is essential (i.e.: when performing photoStimulation)

Fast and scalable algorithms are implemented for

- online motion correction
- automatic source extraction, cell detection
- calculationg and stroring cell centroids in a txt file and on the clipboard
- providing and visualizing Ca traces real-time

With the package the following measurements can be processed:

- 2D High Speed Arbitrary Frames Scans (Raster Scans)
- 3D VolumeScan and
- 3D Multilayer 

The package is based on the popular CaImAn package of Flatiron Institute, a paper explaining most of the implementation details and benchmarking can be found here. The code can be updated with algorithm from GitHub any time while codes for accessing data measured with Femtonics microscopes will not be changed.

The algorithm can be either finetuned with a GUI containing parameters for the data, for algorithm, etc or without GUI with default parameters.

<img src="https://github.com/Kata5/FemtoOnAcid/blob/main/images/image02.png" align="center">

Ca traces are visualized real time and using the check boxes next to the cells a subpopulation of cells can be selected so as to forward them to further measurements (i.e. chessboard scanning)

<img src="https://github.com/Kata5/FemtoOnAcid/blob/main/images/image01.png" align="center">

Requirements

Femtonics Real-time Analysis Package is supported

- on Windows on Intel CPUs,
- CaImAn presently targets Python 3.7, parts of CaImAn are written in C++, but apart possibly during install, this is not visible to the user
Conda
- [FemtoAPI](https://github.com/Femtonics/FemtoAPI) from  [Femtonics Ltd](https://femtonics.eu) is required for online analysis. At least 16G RAM is strongly recommended, and depending on datasets, 32G or more may be helpful.

This package uses [Caiman package](https://github.com/flatironinstitute/CaImAn) from [Flatiron Institute](https://github.com/flatironinstitute). 

### Main paper
A paper explaining most of the implementation details and benchmarking can be found [here](https://elifesciences.org/articles/38173).

```
@article{giovannucci2019caiman,
  title={CaImAn: An open source tool for scalable Calcium Imaging data Analysis},
  author={Giovannucci, Andrea and Friedrich, Johannes and Gunn, Pat and Kalfon, Jeremie and Brown, Brandon L and Koay, Sue Ann and Taxidis, Jiannis and Najafi, Farzaneh and Gauthier, Jeffrey L and Zhou, Pengcheng and Khakh, Baljit S and Tank, David W and Chklovskii, Dmitri B and Pnevmatikakis, Eftychios A},
  journal={eLife},
  volume={8},
  pages={e38173},
  year={2019},
  publisher={eLife Sciences Publications Limited}
}
```

Main developers:
Katalin Ócsai
Kis Gergely
