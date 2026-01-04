## Toweb snapshot pipeline

Ebben a mappában egy kis teszt pipeline van, ami SQLite feladatok alapján
kis felbontású, kis méretű snapshot videókat készít az eredeti médiafájlokból.

## Fájlok

- `snapshot.py` fő konverziós script (SQLite-ból olvas, ffmpeg-et futtat).
- `seed_db.py` teszt adatbázis generátor (mintafeladatokkal).
- `create_db.py` létrehozza az SQLite sémát.
- `toweb.db` SQLite adatbázis (a `seed_db.py` hozza létre).
- `prompt.txt` az eredeti specifikáció szövege.

## Követelmények

- `python3`
- `ffmpeg` elérhető a PATH-on

## SQLite séma áttekintés

- `camera` kamera metaadatok és objektív tartományok.
- `media_file` eredeti és kimeneti fájlok (kimenet `parent_id`-vel hivatkozik).
- `poi` point-of-interest elemek az eredeti fájlhoz.
- `edit_point` összeköti az eredetit/kimenetet/poi-t/kamerát, és redundáns
  adatokat tárol feldolgozáshoz.
- `marker` idővonal annotációk (review/marker/subtitle/chapter).

Időbélyeg mezők (ISO 8601 stringek, PHP-ból módosíthatók):

- `media_file.raw_mtime` a nyers fájl utolsó ismert módosítása.
- `media_file.conv_mtime` az utolsó sikeres konverzió ideje.
- `media_file.poi_mtime` a POI lista legutóbbi változása (globális az eredetihez).
- `poi.updated_at` egyedi POI változás ideje.
- `marker.t` másodperc (lebegőpontos, ffmpeg-kompatibilis), `marker.type`, `marker.text`.

Formátum/konfiguráció mezők a `media_file` táblában (eredeti és kimenet):

- `width`, `height`, `frame_rate`, `codec`
- `duration`, `start_time`
- `cfg_start` és `cfg_max_duration` adja meg a konvertált szegmenst
  (`cfg_max_duration` NULL esetén a teljes fájl kerül konvertálásra).
- A kimeneti méret/kodek/frame rate a kimeneti `media_file` sorból jön.
- A hiányzó eredeti formátum mezőket az első futás `ffprobe`-ból tölti.

## Feldolgozási szabályok (röviden)

- Ha `conv_mtime` újabb, mint `raw_mtime`, `poi_mtime` és minden `poi.updated_at`,
  akkor nincs feladat.
- Ha a nyers fájl újabb, mint `conv_mtime`: készül egy vágatlan snapshot és az
  összes POI snapshot.
- Ha csak POI változott: csak a frissebb POI-k készülnek el (vagy az összes,
  ha `poi_mtime` újabb).

## Használat

Teszt adatbázis létrehozása:

```bash
python3 create_db.py --reset-db
python3 seed_db.py
```

Sikeresség törlése (újrafuttatáshoz):

```bash
python3 seed_db.py --clear-conv
```

Snapshot futtatás:

```bash
python3 snapshot.py --db toweb.db
```

Opcionális flag-ek:

- `--out-dir` kimeneti alapmappa (alapértelmezés: DB mappa).
- `--out-w`, `--out-h` kimeneti méret felülírás (ha a DB-ben nincs).
- `--duration` max hossz felülírás másodpercben (ha a DB-ben nincs).
- `--dry-run` csak kiírja az ffmpeg parancsokat.
