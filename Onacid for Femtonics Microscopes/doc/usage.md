### Modulok listája

 - `caiman_mesc/benchmark.py`: egyszerű objektum az átlagos framerate vagy a frame-enkénti átlagos idő kiírására minden n-edik frame után.
 - `caiman_mesc/gui.py`: a MESc GUI modul az inputfájlok listájának és az OnACID néhány alapvető beállításának bekérésére a futás elején.
 - `caiman_mesc/movies_common.py`: a MESc fájlok betöltéséhez használt néhány objektum és függvény, amit a közvetlen és az API-n keresztüli fájlhozzáférés közösen használ.
 - `caiman_mesc/movies_direct.py`: a közvetlen HDF5 olvasás-alapú implementáció MESc adatok olvasására.
 - `caiman_mesc/movies_mesc_api.py`: a MESc API-n keresztüli implementáció MESc adatok olvasására.
 - `caiman_mesc/movies_util.py`: pár hasznos függvény, amit a közvetlen és az API-n keresztüli fájlhozzáférés közösen használ.
 - `caiman_mesc/movies.py`: a CaImAn által hívott függvények megvalósítása MESc fájlokra, fallback-kel az API és a HDF5 alapú hozzáférés között.
 - `caiman_mesc/results.py`: az eredmények (pl. ROI-k koordinátái) feldolgozásával kapcsolatos függvények.
 - `caiman_mesc/visualization.py`: objektumok az OnACID futás eredményeinek menet közbeni folyamatos kirajzolására.

### Demo fájlok listája

A használat demonstrálásához két demo Python szkriptet használtam, mindkettő a CaImAn saját `demo_OnACID_mesoscope.py` szkriptjén alapul:

 - `caiman_demos/demo_mesc_full.py`: Egy teljes OnACID-futást végez egy MESc fájlon. A fájl elérési útvonalát és az OnACID algoritmus legfontosabb beállításait indítás után a GUI-n keresztül lehet megadni.
 - `caiman_demos/demo_mesc_motion_correct.py`: Kizárólag mozgáskorrekciót és a korrigált frame megjelenítését végzi, elsősorban benchmark célra használható.

### Hozzáférés a MESc-adatokhoz

A CaImAn-MESc csomagban kétféle fájlhozzáférés is implementálva van: direkt (a HDF5 fájlt közvetlenül megnyitva) és API-n keresztüli (a MESc-t az API-n keresztül utasítva a fájl megnyitására, majd az API-n keresztül olvasva belőle az adatokat). A modul úgy lett megírva, hogy betöltéskor megpróbál az API-hoz csatlakozni, és ha sikerül, akkor minden fájlt azon keresztül nyit meg, amennyiben nem (pl. mert nem fut a MESc), akkor pedig mindent közvetlen hozzáféréssel.

### Real-time adatok kezelése

A CaImAn fájlok kezelésére íródott, és a rendszerében mindenhol a fájlnévvel azonosítja a bemeneti adathalmazokat, viszont real-time adatok esetén még nem létezik a kész MESc fájl. Helyette a MESc GUI generál egy pszeudo-fájlnevet (pl. `<Choose a folder>/Untitled_20201001_151618.mesc`), és a rendszerben mindenhol ezzel kell azonosítani a real-time adathalmazt.

Mivel a CaImAn nem lett felkészítve real-time adatokra, ezért feltételezi, hogy előre ismert a frame-ek száma, és ezt fel is használja az OnACID bizonyos tömbök méretének inicializálásához. Real-time használat esetén két dolog kell ennek a megkerüléséhez:

 - Indításkor a CaImAn-nak egy elegendően nagy felső becslést kell adni az érkező frame-ek számára. Ezt a GUI `Max number of real-time frames` opciójával lehet beállítani.
 - Az OnACID futás után, de még az eredmények kiértékelése és elmentése előtt a CaImAn bizonyos tömbjeit át kell méretezni, hogy a dimenzióik passzoljanak a végül ténylegesen feldolgozott frame-ek számához. Erre egy példát mutat a `caiman_demos/demo_mesc_full.py` demó `cnm.fit_online()` utáni blokkja.

MESc fájl feldolgozása esetén az eredmény-fájlok a bemenettel azonos mappába kerülnek. Mivel real-time adatok esetén ez nem áll rendelkezésre, ezért ilyenkor a GUI `Results folder for real-time data` opciója szabja meg, hogy hova kerülnek az eredmény-fájlok.

### Teljes OnACID-futtatás fontosabb részei

A futtatást befolyásolják bizonyos paraméterek a `caiman_mesc.movies.mesc_state.mesc_params` objektumban. Ezek többsége ki van vezetve a futás elején megjelenő GUI-ra, a többit vagy magában a modul forráskódjában (`caiman_mesc/movies_common.py`) lehet átírni, vagy a demó szkript elején módosítani. Mivel a GUI a kivezetett paraméterekhez a dokumentációt is tartalmazza, ezért itt csak a nem kivezetett paraméterek leírása szerepel.

 - `session_handle`: A MESc fájlok több mérési session-t is tartalmazhatnak, de a modul jelenleg csak egyet tud kezelni. Ez a paraméter adja meg a mérési session numerikus azonosítóját (általában 0).
 - `channel_handle`: Egy-egy felvétel több különböző színcsatornát tartalmazhat, de a modul ezek közül csak egyet tud kezelni. Ez a paraméter adja meg a színcsatorna numerikus azonosítóját. A legfontosabb csatornáé általában 0.
 - `do_benchmark`: A CaImAn kódjába beírt kódrészletek ez alapján döntik el, hogy meghívják-e a `caiman_mesc/benchmark.py` funkcióit minden frame után. Ez elsősorban a kód továbbfejlesztése és a performance mérése esetén érdekes, normál használatnál nem.
 - `show_caiman_diagrams`: A CaImAn-nak és a modulnak a működését nem befolyásolja; a demóknak ez alapján érdemes eldönteniük, hogy az OnACID futása után a CaImAn saját diagramjait kirajzoltatják-e.

Ez a leírás a `caiman_demos/demo_mesc_full.py` demó fontosabb részeit emeli ki és magyarázza el. A modul más szkriptből való használata esetén ezeket nagyobbrészt változatlanul lehet érdemes átemelni.

 - CaImAn-MESc importálása: a futás elején a CaImAn saját moduljain kívül a CaImAn-MESc néhány modulját is importálni kell, tipikusan a `caiman_mesc.gui` és `caiman_mesc.movies` modulokat.
 - GUI konstruálása a paraméterek bekéréséhez: a `gui = caiman_mesc.gui.GUI()` sor megjeleníti a MESc GUI ablakát, amiben a CaImAn néhány paraméterét be lehet állítani, közte a fájlok listáját. Bár a CaImAn több fájlt is tud kezelni, de a modul csak egy-fáljos futtatásokkal lett tesztelve.
   - A GUI a beállított adatokat a demo szkript mellé `mesc_params.json` néven tárolja el, és indításkor innen tölti be. Amelyik paraméternek nincs megadva az értéke a JSON fájlban, annak a kezdeti értéke a `gui.py`-ben a `GUI.params` dictionary-ben megadott default lesz.
   - A GUI megjelenítése kikapcsolható a demo szkript `-nogui` opcióval indításával. Ebben az esetben a paraméterek értéke fixen a JSON-ból betöltött illetve a default érték lesz.
 - A CaImAn-MESc modul legtöbb paramétere le van kérve a GUI-ból, és át van adva a `caiman_mesc.movies.mesc_state.mesc_params` objektumnak.
 - A CaImAn felparaméterezése: a `params_dict = {...}` és `opts = cnmf.params.CNMFParams(params_dict=params_dict)` kódrészletek elkészítenek egy paraméter-struktúrát a CaImAn-nak. Itt kell a GUI objektumból lekérni az ott beállított paramétereket, és betenni a `params_dict`-be, pl. `'decay_time': gui.decay_time,`.
 - A CaImAn paraméterei közt van néhány, amelyiket nem lehet a GUI-n megadni, viszont fontos kézzel beégetni a kódba:
   - `'show_movie': False,`: ez kikapcsolja a CaImAn saját OnACID-közbeni megjelenítőjét, mivel az egyrészt lassú, másrészt interferálhat a CaImAn-MESc megjelenítő függvényeivel, harmadrészt a QT-konfliktus miatt akár le is fagyaszthatja a futást.
   - `'fr': 31,`: a felvétel framerate-je nem található meg a MESc fájlokban, ezért azt az értéket írtam be ide, ami az általam kapott eredeti példakódban szerepelt. Elképzelhető, hogy bizonyos felvételek esetén más értéket kell használni.
   - A többi fixen beégetett paraméterhez vagy az általam kapott eredeti példakódban, vagy a CaImAn saját demójában szereplő értékeket használtam, ezeket szintén elképzelhető, hogy hangolni kell.
 - OpenCV2 szálak számának beállítása: annak érdekében, hogy a futás minél gyorsabb legyen, érdemes kihasználni az OpenCV2 képfeldolgozó modul beépített párhuzamosítási képességeit, mivel a CaImAn és a CaImAn-MESc is használ költséges képfeldolgozó függvényeket belőle. A CaImAn alapból letiltja ezt, hogy ne interferáljon a saját párhuzamosítási stratégiájával, viszont utóbbit az OnACID során nem lehet kihasználni, ezért érdemes visszakapcsolni: `cv2.setNumThreads(16)`, ahol `16` helyett a processzor magjainak a számát érdemes írni.
 - Feldolgozandó layer-ek listájának összeállítása: a GUI `Which layers to process` opciójában kétféle érték adható meg: ha egész számok vesszővel elválasztott listája szerepel, akkor csak azokat a layer-eket dolgozza fel a kód, ha a speciális "*" érték, akkor az összes layer-t. A GUI-n és a kimeneti fájlok neveiben is 1-alapú indexek azonosítják a layer-eket, de belül 0-alapú indexeket használ a kód.
 - Iteráció a layer-eken: a CaImAn nincs felkészítve olyan bemeneti fájlokra, ahol több felvétel fut párhuzamosan. Ezért minden layer feldolgozásához újra kell konstruálni az OnACID objektumot és újra lefuttatni a számítást, ezért van a demó nagy része a `for layer_index in layer_indices:` ciklus belsejében. Mivel a bemenetből a frame-ek lekérése a CaImAn belsejében történik, így nem lehet ott átadni az aktuális layer indexét, hanem helyette a CaImAn-MESc globális állapotában van tárolva, hogy éppen melyik layer-rel dolgozzon, ezt állítja be a `caiman_mesc.movies.mesc_state.set_layer_index(layer_index)` sor.
 - Időbeli átlagképek számítása: amennyiben engedélyezve van (`if caiman_mesc.movies.mesc_state.mesc_params.compute_mean_images:`), kiszámítja az idő mentén vett átlagát minden layer-nek külön, és azt elmenti képként.
 - OnACID objektum konstruálása és OnACID végigfuttatása: `cnm = cnmf.online_cnmf.OnACID(params=opts)` illetve `cnm.fit_online()`.
 - CaImAn tömbjeinek átméretezése: mivel a CaImAn nem lett felkészítve olyan adatok kezelésére, ahol az OnACID elején még nem ismert a frame-ek teljes száma, ezért real-time futás esetén a modul egy beépített felső korlátot ad át frame-számként. A CaImAn ez alapján konstruálja meg a tömbjeit, így a felvétel vége után, amikor már ismert a frame-ek valódi száma, azokat át kell méretezni, hogy konzisztensek legyenek az adatokkal. Ezt végzi az `array_names = ["C", "f", "YrA", "F_dff", "R", "S", "noisyC", "C_on"]` illetve a `list_names = ["shifts"]` utáni kódrészlet. Az átméretezendő adattagok listáját később esetleg szükséges lehet bővíteni, mivel a CaImAn Estimates struktúrájának tagjai nincsenek jól dokumentálva.
 - CaImAn saját végeredmény-kiértékelő diagramjainak megjelenítése: a `if caiman_mesc.movies.mesc_state.mesc_params.show_caiman_diagrams:` utáni kódrészlet a CaImAn saját demójából átemelt komponens-, aktivitás- és profiling-diagramokat jeleníti meg.
 - CaImAn eredményének elmentése: az `if caiman_mesc.movies.mesc_state.mesc_params.save_results:` utáni kódrészlet az OnACID futás során kiszámított tömböket elmenti egy HDF5 fájlba.

### Futás kimeneteinek megjelenítése és mentése

A kimeneti fájloknál konvenció, hogy a bemeneti fájl (kiterjesztés nélküli) nevéhez van hozzáfűzve valamilyen utótag.

Az OnACID futásnak három típusú kimenete van:
 - Előfeldolgozás során, pusztán a bemeneti fájlból előállított segéd-adatok:
   - A bemeneti fájl egyes layer-einek átlagképe: ezt a GUI `Save mean images` opciójával lehet bekapcsolni. Az átlagképek `<filename>_layerN_mean.png` néven vannak mentve.
 - Futás során megjelenített adatok:
   - Kontúr-plot: az aktuális frame-re vannak rátéve az eddig megtalált ROI-k kontúrjai, a GUI `Show CaImAn-MESc plots` opciója vezérli. A megjelenített frame átméretezhető a GUI `Contour plot rescale factor` opciójával.
   - Aktivitás-plot: az eddig megtalált ROI-k aktivitása van megjelenítve, mind az eredeti, mind a CNMF által zajszűrt verzió. Fontos: a detrend-elt aktivitások nincsenek megjelenítve, mivel azt a CaImAn nem számolja menet közben, csak az utófeldolgozás során. Szintén a GUI `Show CaImAn-MESc plots` opciója vezérli.
   - ROI-k formázott koordinátái: 100 frame-enként az aktuális ROI-k koordinátái a globális koordinátarendszerbe vannak transzformálva, és ez a vágólapra van helyezve olyan formátumban, hogy a MESc fel tudja dolgozni. A GUI `Put ROI centers on clipboard` opciója vezérli.
 - Futás végén fájlba mentett adatok:
   - ROI-k formázott koordinátái: a futás végén a végső ROI-koordináták ismét a vágólapra vannak téve, illetve a konzolra is kiíródnak. Szintén a GUI `Put ROI centers on clipboard` opciója vezérli.
   - A CaImAn teljes eredmény-struktúrája: a GUI `Save OnACID results` opciója vezérli. A majdnem-teljes `OnACID` objektum, azon belül is különösen az `estimates` objektum kerül egy HDF5 fájlba a CaImAn saját formátumában. A fájlok `<filename>_layerN_results.hdf5` néven vannak mentve.
   - ROI-k a MESc GUI formátumában: a GUI `Save contours as .mescroi` opciója vezérli. A ROI-k lokális koordinátarendszerbe transzformálva, a MESc GUI `.mescroi` JSON formátumában vannak elmentve. A fájlok neve `<filename>_layerN.mescroi`

### Ismert problémák, korlátok

 - Bizonyos esetekben a MESc azt válaszolja az API-n keresztül, hogy végzett a fájl betöltésével, viszont a következő státuszlekéréskor még nem szerepel a fájl a megnyitottak közt, ezért "Cannot find index for file handle" hibát dob a modul. Ez a probléma ritka, és a szkript újrafuttatása általában megoldja.
 - Mivel real-time feldolgozás esetén csak 1 epoch-kal lehet futtatni az OnACID-ot, ezért a vizualizáció nem lett több epoch esetén tesztelve. Amiatt, ahogyan az OnACID a frame-ek számát kezeli, nem biztos, hogy több epoch esetén is megfelelően működik a vizualizáció.
 - Mivel a modul a mérési unit-okat összefűzve, folytonosan kezeli, ezért csak olyan MESc fájlokat tud kezelni, amikben a mérési unit-ok főbb paraméterei (képméret, mérés típusa, layer-ek száma) minden unit-ra azonosak.
 - Bár a CaImAn több fájlt is képes kezelni (azokat virtuálisan összefűzve), de a modul csak egy fájllal lett tesztelve.
