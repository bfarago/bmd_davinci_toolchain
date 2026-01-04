## POI vágás / újrakivágás

Ebben a mappában ugyanannak a folyamatnak két verziója van:

- `poi_crop.sh` (bash) csak `read` használatával, így működik a macOS bash 3.2-n is
- `poi_crop.py` (python3)

Mindkét script dinamikus crop-ot készít, ami időben követ egy POI (point of
interest) pályát, opcionális zoommal, majd fix kimeneti méretre skáláz.

## Követelmények

- `ffmpeg` elérhető a PATH-on.
- A bash verzióhoz elég a macOS alap bash.
- A Python verzióhoz `python3`.

## Bemeneti fájlok

- `in.mov` bemeneti videó (flaggel vagy alapértékkel módosítható).
- `poi.csv` POI kulcspontok.

A `poi.csv` formátuma (az első sor fejléc):

```
t,x,y,z
0.0,960,540,1.0
1.5,980,560,1.2
...
```

Megjegyzések:

- `t` idő másodpercben (ffmpeg kifejezésekhez).
- `x,y` pixel koordináták a forrás képen.
- `z` zoom (1.0 = nincs zoom, 2.0 = 2x).

## Kimenet

- `out_reframe.mp4` kimeneti videó (flaggel vagy alapértékkel módosítható).

## Használat (bash)

```bash
./poi_crop.sh
```

## Használat (python)

```bash
python3 poi_crop.py
```

Opcionális flag-ek (python):

- `--in`, `--poi`, `--out`
- `--out-w`, `--out-h`
- `--venc`, `--vb`
