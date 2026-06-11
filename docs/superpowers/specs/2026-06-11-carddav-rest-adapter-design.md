# CardDAV-REST Adapter — Design dokumentum

**Dátum:** 2026-06-11
**Státusz:** Jóváhagyott

## Cél

Híd (BFF/adapter) létrehozása, amely egy modern automatizációs platform (n8n) számára
tiszta JSON REST API-t ad névjegyek kezelésére, miközben az adatok egy szabványos
CardDAV szerveren (Baïkal/SabreDAV) tárolódnak. Így a mobiltelefonok (iOS/Android)
natívan szinkronizálnak a CardDAV szerverrel, az n8n-nek pedig nem kell XML/WebDAV
protokollal foglalkoznia.

## Szereplők

| Komponens | Szerepkör | Technológia |
|---|---|---|
| Kliens | JSON kéréseket küld a REST API-nak | n8n (HTTP Request node) |
| Adapter | JSON ↔ VCF/XML konverzió, WebDAV hívások | Python (FastAPI) |
| Adatbázis | CardDAV kérések fogadása, névjegyek tárolása, mobil szinkron | Baïkal (SabreDAV) |

## Rögzített döntések

- **API védelem:** API kulcs `X-API-Key` headerben, `API_KEY` env változóból
- **Végpontok köre:** teljes CRUD (keresés, létrehozás, lekérés, módosítás, törlés UID alapján)
- **Duplikátumkezelés:** opcionális `check_duplicates` flag a létrehozás body-jában;
  email-egyezés esetén 409 Conflict a meglévő UID-dal
- **Image terjesztés:** kézi build + push, az image név a compose-ban változóból jön
  (`${ADAPTER_IMAGE}`); nincs CI pipeline az első verzióban
- **Címjegyzék:** egy fix címjegyzék, `BAIKAL_USER` + `BAIKAL_ADDRESSBOOK` env változókból
- **Mezőkészlet:** teljes vCard 3.0 támogatás (név, email, telefon, cím, cég, beosztás,
  születésnap, URL, fotó, megjegyzés, kategóriák)
- **Architektúra:** moduláris FastAPI csomag; `vobject` könyvtár a vCard
  konverzióhoz, kézzel (`xml.etree`) épített `addressbook-query` XML a kereséshez,
  `httpx` async kliens a WebDAV hívásokhoz

## Projektstruktúra

```
CardDAV-REST/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, API-kulcs middleware, router regisztráció, lifespan
│   ├── config.py        # Env változók beolvasása és validálása induláskor (fail fast)
│   ├── models.py        # Pydantic modellek (Contact, SearchRequest, válaszmodellek)
│   ├── vcard.py         # Contact modell ↔ vCard 3.0 konverzió (vobject), roundtrip-képes
│   ├── carddav.py       # CardDAV kliens: REPORT XML építés, PUT/GET/DELETE (httpx)
│   └── routers/
│       └── contacts.py  # /api/contacts végpontok
├── tests/               # pytest + respx (mockolt Baïkal válaszok)
├── Dockerfile
├── docker-compose.yml   # baikal + carddav-rest szolgáltatások
├── .env.example
├── requirements.txt
└── README.md
```

**Adatfolyam:** n8n → JSON + `X-API-Key` → FastAPI (Pydantic validálás) →
`carddav.py` WebDAV hívás (Basic Auth a Baïkal felé) → Baïkal `dav.php` →
XML/VCF válasz visszaalakítva JSON-ná.

## Környezeti változók

| Változó | Kötelező | Leírás |
|---|---|---|
| `BAIKAL_URL` | igen | pl. `http://baikal/dav.php` (belső Docker hálózaton) |
| `BAIKAL_USER` | igen | Baïkal felhasználó |
| `BAIKAL_PASS` | igen | Baïkal jelszó |
| `BAIKAL_ADDRESSBOOK` | nem (default: `default`) | címjegyzék azonosító |
| `API_KEY` | igen | az n8n → adapter hitelesítéshez |

Hiányzó kötelező változónál az app induláskor hibával leáll, nem az első kérésnél.
Jelszó vagy URL kódba/Dockerfile-ba égetése tilos.

## API végpontok

| Metódus | Útvonal | Leírás |
|---|---|---|
| `POST` | `/api/contacts/search` | Keresés dinamikus szűrőkkel |
| `POST` | `/api/contacts` | Létrehozás (opcionális duplikátum-ellenőrzéssel) |
| `GET` | `/api/contacts/{uid}` | Egy névjegy lekérése JSON-ként |
| `PUT` | `/api/contacts/{uid}` | Módosítás (ETag-kezeléssel) |
| `DELETE` | `/api/contacts/{uid}` | Törlés |
| `GET` | `/health` | Életjel a Docker healthcheckhez (API kulcs nélkül) |

### POST /api/contacts/search

Bemenet (minden mező opcionális, de legalább egy szűrő kötelező):

```json
{
  "email": "teszt@email.hu",
  "phone": "+36301234567",
  "name": "János",
  "match_condition": "allof"
}
```

- `match_condition`: `allof` (ÉS) vagy `anyof` (VAGY), default `allof`
- Match-type: email → `equals` (kisbetű-érzéketlen collation), név és telefon → `contains`
- A szűrők leképezése: `email` → `EMAIL` prop-filter, `phone` → `TEL`, `name` → `FN`

Válasz:

```json
{
  "exists": true,
  "match_count": 1,
  "matches": [
    {"uid": "123e4567", "fn": "Teszt János", "emails": [...], "phones": [...]}
  ],
  "searched_params": {...}
}
```

### POST /api/contacts

Bemenet — teljes vCard mezőkészlet, minden opcionális, kivéve hogy legalább egy
névmező kell (az `FN` ebből áll össze):

- `firstname`, `lastname`, `middlename`, `prefix`, `suffix`
- `emails: [{type, value}]`, `phones: [{type, value}]` (type: work/home/cell/...)
- `addresses: [{type, street, city, zip, state, country}]`
- `org`, `title`, `birthday` (ISO dátum), `urls: [string]`, `note`,
  `photo` (base64 string → beágyazott `PHOTO;ENCODING=b`, vagy http(s) URL →
  `PHOTO;VALUE=uri` hivatkozásként tárolva, az adapter nem tölti le), `categories: [string]`
- `check_duplicates` (bool, default false): ha igaz és email-egyezés van,
  409 Conflict a meglévő UID-dal

Működés: UUID generálás → vCard 3.0 összeállítás (`VERSION:3.0`, `UID`, `FN`, `N`
kötelező; `\r\n` sortörések — a vobject kezeli) → `PUT` a
`{BAIKAL_URL}/addressbooks/{user}/{addressbook}/{uid}.vcf` útvonalra
`If-None-Match: *` headerrel.

Válasz (201): `{"status": "success", "uid": "123e4567", "filename": "123e4567.vcf"}`

### GET /api/contacts/{uid}

A `.vcf` letöltése, vobject-tel parszolás, teljes Contact JSON visszaadása
(+ `etag` mező informatívan).

### PUT /api/contacts/{uid}

1. `GET` a meglévő vCard-ra + ETag
2. A változások beleírása a **meglévő** vCard-ba (a nem kezelt property-k —
   pl. mobilról jött X- mezők — megmaradnak)
3. `PUT` `If-Match: {etag}` headerrel
4. Ha a szerver 412-t ad (közben módosult), a válasz 409 Conflict

### DELETE /api/contacts/{uid}

Közvetlen `DELETE` a `.vcf` útvonalra; 404 továbbítva. Siker: 200,
`{"status": "deleted", "uid": "..."}`.

## CardDAV kommunikáció

- A keresés `REPORT` kérés `addressbook-query` body-val a címjegyzék gyűjteményre,
  `Depth: 1` headerrel; az XML `xml.etree`-vel épül (nincs string-összefűzés,
  nincs injection veszély)
- A `multistatus` válaszból a `response` elemek `address-data` tartalmát vobject
  parszolja — innen a `matches` lista; a `response` jelenléte = találat
- A UID és a fájlnév mindig megegyezik (létrehozáskor mi generáljuk), így a
  CRUD műveletek közvetlenül címezhetők keresés nélkül
- A httpx async kliens az app lifespan-jához kötött, connection pooling-gal,
  default 10 s timeouttal

## Hibakezelés

| Helyzet | Válasz |
|---|---|
| Baïkal nem elérhető (connection error / timeout) | 502, beszédes JSON üzenet |
| Baïkal 401/403 (rossz credential) | 502; részletek csak a logban, a kliens felé nem |
| Névjegy nem található | 404 |
| ETag ütközés / már létező UID (412 a szervertől) | 409 |
| Duplikátum `check_duplicates` mellett | 409 a meglévő UID-dal |
| Hibás bemenet | 422 (Pydantic) |
| Hiányzó/rossz API kulcs | 401 |

## Docker és infra

- **Dockerfile:** `python:3.12-slim`, non-root user, uvicorn a 8000-es porton
- **docker-compose.yml:**
  - `baikal`: `ckulka/baikal:nginx` image, named volume-ok (config + adat),
    80-as port kivezetve az első beállításhoz és a mobil szinkronhoz
  - `carddav-rest`: `image: ${ADAPTER_IMAGE}` (nem helyi build), 8000-as port
    kivezetve az n8n-nek, env változók a compose-ból / `.env`-ből
  - közös belső hálózat; az adapter `http://baikal` néven éri el a szervert
  - healthcheck mindkét konténeren, `depends_on` a Baïkal-ra
- `.env.example` dokumentálja a változókat; a valódi `.env` gitignore-olva

## Tesztelés

- **Unit:** vCard ↔ JSON roundtrip tesztek; XML-építő tesztek (email/phone/name
  szűrők és allof/anyof kombinációk)
- **API:** FastAPI `TestClient` + `respx`, valódi SabreDAV válasz-mintákkal;
  minden végpont happy path + hibaágak (412→409, 404, 502)
- **Kézi integráció:** a compose-zal felhúzott valódi Baïkal elleni curl-példák
  a README-ben

## Nem cél (YAGNI)

- Több címjegyzék / több felhasználó kezelése
- CI/CD pipeline
- Rate limiting, audit log
- CalDAV (naptár) támogatás
- Webhook / change feed a Baïkal-ból n8n felé
