# n8n-nodes-carddav-rest

n8n community node a [CardDAV REST](https://github.com/mark/CardDAV-REST) adapterhez. Lehetővé teszi Baïkal-ban tárolt névjegyek kezelését n8n workflow-kból — HTTP Request node-ok kézzel írása nélkül.

## Telepítés

### n8n-ből

**Settings → Community Nodes → Install** → csomagnév: `n8n-nodes-carddav-rest`

### Helyi fejlesztéshez

```bash
cd n8n-node
npm install
npm run dev
```

Ez elindít egy n8n példányt a node-dal betöltve (`http://localhost:5678`).

Alternatív Docker-alapú telepítés:

```bash
docker run -it --rm \
  -p 5678:5678 \
  -v "$(pwd)/n8n-node:/home/node/.n8n/custom/n8n-nodes-carddav-rest" \
  -e N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom \
  n8nio/n8n
```

## Hitelesítés

A node a **CardDAV REST API** credential-t használja, amelynek két mezője van:

| Mező | Leírás |
|------|--------|
| Base URL | A CardDAV REST adapter URL-je (pl. `http://localhost:8000`) |
| API Key | Az `X-API-Key` headerbe kerülő kulcs |

## Erőforrások és műveletek

### Contact (Névjegy)

Minden névjegy-művelethez kötelező az **Address Book** kiválasztása (dinamikus legördülő).

| Művelet | Leírás |
|---------|--------|
| **List** | Névjegyek listázása (lapozható, gyors kereséssel) |
| **Get** | Egy névjegy lekérése UID alapján |
| **Create** | Új névjegy létrehozása |
| **Update (Full Replace)** | Névjegy összes mezőjének felváltása |
| **Update Fields** | Csak a megadott mezők módosítása (PATCH) |
| **Delete** | Névjegy törlése |
| **Search** | Keresés név, e-mail vagy telefonszám alapján (AND/OR logika) |
| **Merge Duplicates** | Két névjegy összevonása (duplikált törlése) |
| **Move to Addressbook** | Névjegy áthelyezése másik címjegyzékbe |
| **Download vCard** | Névjegy letöltése `.vcf` fájlként (bináris kimenet) |

### Addressbook (Címjegyzék)

| Művelet | Leírás |
|---------|--------|
| **List** | Az összes elérhető címjegyzék listázása |

### Stats (Statisztika)

| Művelet | Leírás |
|---------|--------|
| **Get** | Névjegyszám, utolsó/legrégebbi módosítás, fájlméret minden címjegyzékre |

### Config (Konfiguráció)

| Művelet | Leírás |
|---------|--------|
| **Get** | Aktív szerver konfiguráció lekérése (`name_format`, `default_region`, `required_fields`) |

## Névjegy mezők

### Alapmezők (Create / Update)

| Mező | Kötelező | Leírás |
|------|----------|--------|
| First Name | igen* | *Legalább kereszt- vagy vezetéknév kötelező |
| Last Name | nem | |
| Phone Numbers | nem | Több szám, típusonként (cell/home/work/other) |
| Email Addresses | nem | Több cím, típusonként (home/work/other) |
| Addresses | nem | Több lakcím (utca, város, irányítószám, megye, ország) |
| Additional Fields | nem | Születésnap, kategóriák, megjegyzés, szervezet, cím, stb. |

> A szerver `REQUIRED_FIELDS` konfigurációja alapján további mezők is kötelezővé válhatnak (pl. `phones`, `emails`). Hiányzó kötelező mező esetén a szerver 422-es hibával válaszol.

### Update Fields (PATCH) — csak a megadott mezők módosulnak

A `Fields to Update` kollekcióban add meg, mit szeretnél változtatni. A többi mező érintetlen marad.

### Search paraméterek

- **Name** — részleges egyezés (többszavas keresés szórend-független)
- **Email** — pontos egyezés
- **Phone** — részleges egyezés
- **Match Condition** — `All Of (AND)` / `Any Of (OR)`

## Hibakezelés

| HTTP státusz | n8n viselkedés |
|-------------|---------------|
| 401 | Hibás API kulcs |
| 404 | Névjegy nem található |
| 409 | Duplikált névjegy vagy egyidejű módosítás |
| 422 | Validációs hiba (pl. hiányzó kötelező mező) |
| 502 | A Baïkal szerver nem érhető el |

## Fejlesztés

```bash
cd n8n-node
npm install
npm test          # Jest tesztcsomag futtatása
npm run build     # TypeScript fordítása dist/-be
npm run dev       # n8n indítása hot reload-dal
npm run lint      # ESLint ellenőrzés
npm run lint:fix  # Automatikus javítás
```

## Közzététel npm-re

A csomag közzétételéhez frissítsd a `package.json` következő mezőit:

- `author.name` / `author.email`
- `homepage`
- `repository.url`

Majd:

```bash
npm run build
npm publish
```

## Kapcsolódó projekt

- [CardDAV REST adapter](../README.md) — a FastAPI-alapú Baïkal adapter, amelyet ez a node hív

## Licenc

[MIT](LICENSE.md)
