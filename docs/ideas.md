# Ötletek

## Kényelmi funkciók

- [x] **`GET /api/contacts/{uid}/vcard`** — nyers vCard letöltés, ha n8n-ből vagy más eszközből kell az eredeti fájl
- [x] **Pagination a listázáshoz** — `GET /api/contacts?limit=50&offset=0`, ha nagy a névjegykönyv
- [x] **Gyors keresés query param-mal** — `GET /api/addressbooks/{book}/contacts?q=anna` a külön POST search endpoint helyett, egyszerűbb esetekre

## Adatminőség

- [x] **Telefonnormalizálás** — beíráskor automatikusan egységes formátumra hozza a számokat (pl. `06301234567` → `+36301234567`)
- [x] **Kötelező mező konfiguráció** — `REQUIRED_FIELDS=emails,phones` env var: ha a megadott mezők nélkül próbálnak kontaktot létrehozni/módosítani, 422-vel visszautasítja

## Műveletek

- [ ] **`POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}`** — két duplikált kontakt összevonása (megtartja az egyiket, törli a másikat)
- [x] **`PATCH /api/addressbooks/{book}/contacts/{uid}`** — részleges frissítés csak a megadott mezőkre, szemben a PUT teljes felülírásával

## Megfigyelhetőség

- [ ] **`GET /api/stats`** — kontaktok száma, utolsó módosítás (hasznos n8n dashboardhoz)
- [ ] **`GET /api/config`** — visszaadja az aktív `required_fields`, `default_region`, `name_format` beállításokat, hogy egy n8n node dinamikusan tudjon formot építeni (a `REQUIRED_FIELDS` jelenleg nem látszik az OpenAPI sémában)
