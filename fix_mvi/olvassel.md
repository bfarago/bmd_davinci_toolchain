## MVI MP4 hibás frame ellenőrzés és javítás

Ezek a scriptek egy olyan projekt miatt készültek, ahol sok videófájlnál hibás
frame-ek jelentek meg egy rossz SD-kártya miatt. A hibás frame-ek nem voltak
feltűnőek normál lejátszás közben, de a DaVinci Resolve a renderelésnél megáll,
amikor hibás frame-et talál. A scriptek segítenek az érintett fájlok
azonosításában és opcionálisan javításában.

## Követelmények

- `ffmpeg` elérhető a PATH-on.

## Működés (mindkét script)

- Másold a scriptet abba a mappába, ahol a `MVI_*.MP4` nevű videófájlok vannak.
- A scriptet ebben a mappában futtasd.
- A scriptek `ffmpeg`-et futtatnak figyelmeztetés módban, kiszűrik a nem kritikus
  figyelmeztetéseket, és akkor jelölnek hibásnak egy fájlt, ha a szűrt logban
  szerepel a `corrupt` szó.

A riportok ide készülnek:

- `out_bad.txt` a hibás fájlok listája (soronként egy fájl).
- `bad_report.txt` részletes riport a hibás fájlokról.
- `ok_report.txt` részletes riport a hibátlan fájlokról.

## scan_mvi.sh (csak ellenőrzés)

Ez a script megkeresi és riportolja a hibás fájlokat, de nem módosítja a
videókat.

Futtatás:

```bash
./scan_mvi.sh
```

## fix_mvi.sh (ellenőrzés + javítás)

Ez a script megkeresi és kijavítja a hibás fájlokat. A javítás úgy történik,
hogy a videó újrakódolásra kerül H.264-re (CRF 18, slow preset), miközben a hang
változatlanul marad, majd a konténer újraírásra kerül `-movflags +faststart`
opcióval.

Futtatás:

```bash
./fix_mvi.sh
```

Hibás fájloknál a viselkedés:

- Az eredeti fájl átnevezése `CORRUPT_<eredeti_nev>` formára.
- A javított fájl az eredeti fájlnéven kerül vissza.
- A riportok frissülnek a fentiek szerint.

Mentési hely:

- Alapból a hibás eredetik ugyanabban a mappában maradnak.
- Ez módosítható a `fix_mvi.sh` tetején lévő `backup_dir` változóval.
