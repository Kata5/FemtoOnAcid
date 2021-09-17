### CaImAn telepítése

A fő útmutató itt található: <https://caiman.readthedocs.io/en/master/Installation.html> ez a leírás nagyjából annak a lépéseit követi néhány plusz tapasztalat és a MESc-specifikus plusz dolgok figyelembevételével. A patch-elés megkönnyítése érdekében fixen az **1.8.5-ös verzióhoz** írtam az útmutatót; az [upgrade-elési útmutatóban](./upgrade.md) van leírva, hogy mi a teendő, ha később újabb CaImAn verzió kell.

 - Le kell tölteni az Anaconda-t innen: <https://docs.continuum.io/anaconda/install/windows/> és felinstallálni.

 - Miután az Anaconda fennvan, minden további lépést (és a CaImAn összes futtatását) a Windows sima parancssora helyett az Anaconda saját shell-jével kell csinálni. Ezt az installáláskor automatikusan beteszi a Start menübe "Anaconda Prompt (anaconda3)" néven.

 - Az Anaconda shell-jében létre kell hozni egy Anaconda környezetet: `conda create -n caiman_env` Itt a `caiman_env` helyett bármilyen név állhat, a későbbiekben mindig ezt kell használni a környezet aktiválásához.

 - A létrehozott környezetet aktiválni kell: `conda activate caiman_env`

 - Fel kell installálni a CaImAn csomagot a conda-forge csatornáról:
   ```bash
   conda install caiman=1.8.5 -c conda-forge
   ```
   - A csomag installálása elég hosszú ideig tarthat, a "Solving environment" lépés többször 10 perc szokott lenni. Ilyenkor határozza meg az Anaconda, hogy melyik csomagból melyik verziót tegye fel, hogy minden mindennel kompatibilis legyen.
   - Amennyiben már volt korábban telepítve CaImAn ugyanannak az Anaconda példánynak egy másik környezetébe, és az patch-elve lett (lásd lejjebb), akkor a conda warning-ot fog adni arról, hogy nem stimmelnek a patch-elt fájlok méretei. Ez normális, és nem kell vele foglalkozni.
   
 - A demók és a MESc illesztőkód működéséhez van pár plusz függőség, illetve az egyik csomagot kompatibilitási problémák miatt vissza kell állítani korábbi verzióra:
   ```bash
   conda install h5py=2.10.0 -c conda-forge --override-channels
   conda install natsort -c conda-forge --override-channels
   conda install pyperclip -c conda-forge --override-channels
   pip3 install femtoapi
   pip3 install tkscrolledframe
   ```

 - Amennyiben a CaImAn videójának az elmentését be akarjuk kapcsolni (vagy a CaImAn "Incorrect library version loaded" warning-ját megoldani), akkor szükség van az OpenH264-re is. Ezt innen lehet letölteni: https://github.com/cisco/openh264/releases és a kicsomagolt `.dll`-t tetszőleges helyre tehetjük, azt a CaImAn egy környezeti változó alapján (lásd később) találja meg.

### Környezeti változók beállítása

A CaImAn működéséhez bizonyos környezeti változók kellenek; ezeket a `~/anaconda3/envs/caiman_env/etc/conda/activate.d/caiman_activate.bat`-ban érdemes átírni, így a környezet aktiválásakor automatikusan beállítódnak.

 - A CaImAn alapból letiltja a lineáris algebra párhuzamosítását, de ezt az online feldolgozás esetén hatékonyabb visszakapcsolni, és átírni a `set MKL_NUM_THREADS=1` sort `set MKL_NUM_THREADS=x`-re, ahol `x` a gépben lévő processzormagok száma.

 - A default conda-forge környezet MKL-t használ a lineáris algebrára, emiatt a `set OPENBLAS_NUM_THREADS=1` sornak nincs hatása. Amennyiben valami miatt MKL helyett OpenBLAS (és azt használó numpy verzió) van feltéve a környezetbe, akkor ezt kell ugyanúgy átírni a processzormagok számára, mint az MKL környezeti változóját. Bizonyos esetekben (pl. AMD processzor) az OpenBLAS implementációja hatékonyabb lehet, mivel az MKL-t az Intel a saját processzoraira optimalizálja.

 - A MESc-kezelő plusz plusz modulok könyvtárát be kell tenni a `PYTHONPATH` környezeti változóba. Pl. ha a `caiman_mesc` alkönyvtár a `c:/users/dzsi/mesc`-ben van, akkor `set PYTHONPATH=c:/users/dzsi/mesc` kell.

 - A CaImAn magától nem találja meg a saját járulékos adatfájljait (pl. a neurális háló modelleket), ezért ezeknek a helyét be kell tenni a `CAIMAN_DATA` változóba. Pl. ha az Anaconda a `c:/users/dzsi/anaconda3`-ba lett telepítve, akkor `set CAIMAN_DATA=c:/users/dzsi/anaconda3/envs/caiman_env/share/caiman/` kell.

 - Amennyiben a CaImAn videójának az elmentését be akarjuk kapcsolni (vagy a CaImAn "Incorrect library version loaded" warning-ját megoldani), akkor az OpenH264 DLL-jének elérési útját be kell tenni az `OPENH264_LIBRARY` környezeti változóba, pl. `set OPENH264_LIBRARY=c:/users/dzsi/mesc/openh264-1.8.0-win64.dll`

- Amennyiben szeretnénk, hogy a parancssor az Anaconda környezet deaktiválása után tovább használható legyen, és az általunk beállított környezeti változó-értékek törölve legyenek, akkor a `~/anaconda3/envs/caiman_env/etc/conda/deactivate.d/caiman_deactivate.bat`-ba kell a megfelelő sorokat betenni, pl. `set "MKL_NUM_THREADS="`.

### CaImAn patch-elése

Mivel a CaImAn nem lett bővíthetőre megírva (pl. egy fix switch-case kezeli a különböző fájlkiterjesztéseket), ezért magába a CaImAn forrásfájljaiba is bele kell írni a `.mesc` fájlok kezeléséhez.

**FIGYELEM**: bár az Anaconda környezetei elvileg egymástól függetlenek, de a gyakorlatban a hely- és hálózati forgalom-takarékosság érdekében amit egyszer letöltött és telepített bármelyik környezetbe, azt cache-eli és hardlinkeli, ha egy másik környezetbe is telepítve van ugyanaz. Emiatt ha egy Anaconda installációban bármelyik környezet CaImAn-ja patch-elve van, az az **összes** környezet CaImAn-ját megváltoztatja (és praktikusan nem lehet két különböző környezetben párhuzamosan használni az eredetit és a patch-eltet). Emiatt új környezetbe telepítés esetén (lásd fejlebb) a conda warning-ot adhat, hogy nem stimmelnek bizonyos fájlok méretei.

A CaImAn 1.8.5-ös verziójának patch-eléséhez készen megvannak a patch-elt fájlok, amikkel egyszerűen felül kell írni az eredetit:
 - `caiman_patch/movies.py` -> `~/anaconda3/envs/caiman_env/Lib/site-packages/caiman/base/movies.py`
 - `caiman_patch/online_cnmf.py` -> `~/anaconda3/envs/caiman_env/Lib/site-packages/caiman/source_extraction/online_cnmf.py`
 - `caiman_patch/utilities.py` -> `~/anaconda3/envs/caiman_env/Lib/site-packages/caiman/source_extraction/utilities.py`

Más CaImAn verzió esetén kézzel kell átemelni a változtatásokat; ennek leírása az [upgrade-elési útmutatóban](./upgrade.md) van.
