# Ötletek

## Kényelmi funkciók

- [x] **`GET /api/contacts/{uid}/vcard`** — nyers vCard letöltés, ha n8n-ből vagy más eszközből kell az eredeti fájl
- [x] **Pagination a listázáshoz** — `GET /api/contacts?limit=50&offset=0`, ha nagy a névjegykönyv
- [ ] **Gyors keresés query param-mal** — `GET /api/contacts?q=anna` a külön POST search endpoint helyett, egyszerűbb esetekre

## Adatminőség

- [ ] **Telefonnormalizálás** — beíráskor automatikusan egységes formátumra hozza a számokat (pl. `06301234567` → `+36301234567`)
- [ ] **Kötelező mező konfiguráció** — `REQUIRED_FIELDS=email` env var: ha nincs email a kontakton, 422-vel visszautasítja

## Műveletek

- [ ] **`POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}`** — két duplikált kontakt összevonása (megtartja az egyiket, törli a másikat)
- [ ] **`PATCH /api/contacts/{uid}`** — részleges frissítés csak a megadott mezőkre, szemben a PUT teljes felülírásával

## Megfigyelhetőség

- [ ] **`GET /api/stats`** — kontaktok száma, utolsó módosítás (hasznos n8n dashboardhoz)
