

# Bevezetés

Ez a dokumentum részletesen bemutatja a projekt működését, amely egy automatizált rendszer létrehozására irányul, amely jogdíjmentes elektronikus zenéket keres a SoundCloudon, majd ezekhez animációs videókat készít, és feltölti őket a YouTube csatornára. A projekt célja, hogy nagy mennyiségű tartalom gyors előállításával széles közönséget érjen el.

# SoundCloud Zene Keresése és Metaadatok Kinyerése

A jogdíjmentes zenék azonosítása Pythonban írt program segítségével történik, amely Selenium alapú web scraperrel pásztázza végig előre megadott előadók számait a SoundCloudon. A program kinyeri a zenékhez kapcsolódó metaadatokat. Az előadókat és lejátszási listákat manuálisan lehet megadni, de a jövőben tervezett a keresési folyamat továbbfejlesztése a trendek figyelembevételével, vagy akár specifikus SoundCloud keresések végrehajtásával is.

# Audiovizualizációs Videók Készítése

Jelenleg az animációk elkészítése After Effects segítségével történik, egy előre elkészített sablon alapján. A sablonban csak ki kell cserélni a hátteret, a zenét, a zene címét, és az animáció színét a zene műfajának megfelelően, majd az elkészült animációt kirenderelni. Ezt egy ExtendScript automatizáció végzi. A jövőben tervben van áttérni a DaVinci Resolve Fusion használatára, amely jövőállóbb és komplexebb animációk készítését teszi lehetővé. Azonban ennek automatizálása még további kutatást és fejlesztést igényel.

# Technológiai Megoldások és Erőforrások Kezelése

A program alapvetően Pythonra épül, a különböző modulok összekapcsolását és az adatok áramlását pedig egy SQLite adatbázis segítségével tervezik megoldani. A kész videók nagy mérete miatt egy hálózati tárolón kerülnek elhelyezésre, strukturált fájlrendszerben. A rendszer két különböző számítógépen fut: egy kisebb erőforrású gépen, amely folyamatosan fut és végzi a feladatokat, valamint egy nagyobb teljesítményű számítógépen, amely a renderelési feladatokat látja el. Az audiovizualizációhoz jelenleg az After Effects Trapcode Particles effekt könyvtárát használják, de a jövőben más megoldásokra, például a Resolve Fusionre történő áttérés is tervben van.

# Zene Kategorizálása

A zenék kategorizálása EDM al-műfajok alapján történik. Az animáció színe is ezt jelzi. A kategorizálást egy algoritmus végzi, amely először a zene metaadatait elemzi, hogy tartalmaznak-e utalást a műfajra. Ha nem, akkor egy AI-alapú eszköz segítségével próbálja meg meghatározni a zene műfaját.

# YouTube Feltöltési Folyamat és Szerzői Jogok Ellenőrzése

A rendszer YouTube API-t használ a videók feltöltésére és ütemezésére. Az összes videó először privátként kerül feltöltésre, majd ellenőrzésre, hogy kapott-e szerzői jogi követelést. Ha igen, a videó nem kerül nyilvánosságra, vagy egyéni elbírálás tárgya lesz. A szöveges tartalmak generálása AI segítségével történik, például ChatGPT API hívásokon keresztül. A feltöltések időzítése konzisztens, így a videók mindig ugyanazokban az időpontokban kerülnek ki, figyelembe véve a statisztikailag legnagyobb nézettséget biztosító időszakokat.

# Skálázhatóság és Versenystratégia

A rendszer automatizálásának köszönhetően nagyon nagy mennyiségű videó előállítására képes. A cél az, hogy a jól befutott, hasonló tematikájú YouTube csatornák, mint például az NCS vagy a TrapNation, több éves munkájával szemben versenyelőnyt szerezzen azzal, hogy ugyanannyi videót jóval rövidebb idő alatt tölt fel. A mennyiségre fókuszálva a csatorna kevésbé népszerű előadók számait is tömegével tölti fel, így létrehozva egy óriási elektronikus zene "adatbázist".

# Célközönség

A projekt szélesebb közönséget céloz meg, hiszen a nagy mennyiségű zeneszám elérhetősége révén szinte minden keresett elektronikus zenei műfajban található tartalom. Ezáltal több felhasználó találhat rá a csatornára, függetlenül attól, hogy milyen konkrét stílust keresnek.