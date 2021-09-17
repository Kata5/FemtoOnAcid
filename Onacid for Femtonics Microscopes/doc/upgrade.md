### Újabb CaImAn verzió telepítése

Az Anaconda új környezet felépítése esetén a kért csomagból a legújabbat próbálja feltenni. Tehát ha a [telepítési útmutatóban](./install.md) a `conda install caiman=1.8.5 -c conda-forge` parancs helyett a `conda install caiman -c conda-forge` parancsot adjuk ki, akkor az új környezetbe a legújabb (conda-forge-ból elérhetó) CaImAn verzió installálódik. **FONTOS**: ebben az esetben a `h5py` csomagból nem biztos, hogy megfelelő a 2.10.0-s verzió, emiatt pedig elképzelhető, hogy a CaImAn-MESc kód HDF5-öt kezelő részein is módosítani kell.

Meglévő környezetben a CaImAn frissítése komplikáltabb lehet a csomagkompatibilitások miatt, ezt a `conda update caiman` paranccsal lehet.

### CaImAn patchelése újabb verzió esetén

Újabb CaImAn verzió esetén hibákat okozhatna a fájlok felülírása, ezért kézzel kell a megfelelő kódrészleteket átírni:

 - `~/anaconda3/envs/caiman_env/Lib/site-packages/caiman/base/movies.py`
   - A fájl elejére az `import`-ok közé be kell írni, hogy `import caiman_mesc.movies`
   - A `load()` és `load_iter()` függvényekben az `if os.path.exists(file_name):` sort `if True:`-val kell helyettesíteni (mivel real-time futás esetén nem létezik az a kvázi-fájlnév, amivel a MESc API azonosítja az aktuális felvételt).
   - A `load()` függvényben az `else: raise Exception('Unknown file type')` elé a kiterjesztés szerinti szétválasztásba be kell írni egy
     ```python
     elif extension == '.mesc': input_arr = caiman_mesc.movies.load(file_name, subindices)
     ```
     ágat.
   - A `load_iter()` függvényben az `else:  # fall back to memory inefficient version` elé a kiterjesztés szerinti szétválasztásba be kell írni egy
     ```python
     elif extension == '.mesc':
         yield from caiman_mesc.movies.load_iter(file_name, subindices)
     ```
     ágat.

 - `~/anaconda3/envs/caiman_env/Lib/site-packages/caiman/source_extraction/online_cnmf.py`
   - A fájl elejére az `import`-ok közé be kell írni:
     ```python
     import caiman_mesc.movies
     import caiman_mesc.visualization
     import caiman_mesc.benchmark
     import caiman_mesc.results
     ```
   - Az `initialize_online()` függvényben az
     ```python
     if opts['show_movie']:
         self.bnd_Y = np.percentile(Y,(0.001,100-0.001))
     ```
     blokk feltételét át kell írni `if opts['show_movie'] or caiman_mesc.movies.mesc_state.mesc_params.show_plots:`-ra.
   - A `fit_online()` függvényben az `# Iterate through the epochs` elé be kell írni:
     ```python
    if caiman_mesc.movies.mesc_state.mesc_params.do_benchmark:
        benchmark = caiman_mesc.benchmark.SimpleOnACIDBenchmark(10)
    if caiman_mesc.movies.mesc_state.mesc_params.show_plots:
        component_coloring_scheme = caiman_mesc.visualization.ComponentColoringScheme()
        contour_plot = caiman_mesc.visualization.ContourPlot(component_coloring_scheme)
        activity_plot = caiman_mesc.visualization.ActivityPlot(component_coloring_scheme)
    if caiman_mesc.movies.mesc_state.mesc_params.export_centers:
        center_exporter = caiman_mesc.results.CenterExporter()
     ```
   - A `fit_online()` függvényben a `self.fit_next(t, frame_cor.reshape(-1, order='F'))` után be kell írni:
     ```python
    if caiman_mesc.movies.mesc_state.mesc_params.do_benchmark:
        benchmark.print_benchmark(t - init_batch + 1)
    
    if caiman_mesc.movies.mesc_state.mesc_params.show_plots:
        frame_normalized = (frame_cor - self.bnd_Y[0]) / np.diff(self.bnd_Y)
        contour_plot.show(frame_normalized, t + 1, self.estimates.Ab, self.N)
        activity_plot.show(self.estimates.C_on, self.estimates.noisyC, t + 1, self.N, self.params.get('init', 'nb'))
    
    if caiman_mesc.movies.mesc_state.mesc_params.export_centers:
        center_exporter.export_periodically(ffll, frame.shape, t + 1, self.estimates.Ab, self.N, False)
     ```

 - `~/anaconda3/envs/caiman_env/Lib/site-packages/caiman/source_extraction/utilities.py`
   - A fájl elejére az `import`-ok közé be kell írni, hogy `import caiman_mesc.movies`
   - A `get_file_size()` függvényben az `if os.path.exists(file_name):` sort `if True:`-val kell helyettesíteni.
