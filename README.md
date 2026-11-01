# MedBrief

Konzolna aplikacija v Pythonu za povezovanje podatkov o pacientih, dokumentih in laboratorijskih meritvah iz datotek XML. Omogoča filtriranje po pacientu ali manjkajočih podatkih ter izvoz rezultatov v JSON in XML.

Aplikacija predstavlja začetno podatkovno fazo projekta MedBrief, katerega dolgoročni cilj je AI podpora pri pripravi zdravstvene dokumentacije. Vsi uporabljeni podatki so sintetični.

## Zagon

Potreben je **Python 3.9 ali novejši**. XML aplikacija uporablja samo standardne module `xml.etree.ElementTree`, `pathlib` in `json`. Odvisnosti za skripto v mapi `scraping/` (`beautifulsoup4` in `requests`) so navedene v `requirements.txt`.

Klonirajte repozitorij in enkrat ustvarite virtualno okolje `.venv` v korenu projekta:

```bash
git clone https://github.com/FZS187/MedBrief.git
cd MedBrief
python -m venv .venv
```

Če vaše okolje uporablja ukaz `python3`, okolje ustvarite z `python3 -m venv .venv`.

Aktivirajte okolje v terminalu, ki ga uporabljate:

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**

```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS (bash ali zsh):**

```bash
source .venv/bin/activate
```

V aktiviranem okolju namestite odvisnosti in zaženite aplikacijo:

```bash
python -m pip install -r requirements.txt
python py_xml/reading_xml.py
```

Ob vsakem novem terminalu ponovno aktivirajte obstoječe okolje. Namestitev ponovite, ko se spremeni `requirements.txt`. Za izhod iz okolja uporabite:

```bash
deactivate
```

Mapa `.venv/` je vključena v `.gitignore` in se ne shranjuje v Git. Vsak razvijalec ustvari svoje okolje iz `requirements.txt`.

## Running the public research app (SearXNG + Streamlit)

This optional research tool is separate from the XML console app above. It uses
Streamlit and Frankensurf in WSL, with SearXNG running in Docker Desktop.
Python packages are installed from the two requirements files; Docker reads
`compose.yaml` to start SearXNG. There is currently no combined launcher script.

### First-time setup

Requirements: Docker Desktop running Linux containers, Ubuntu in WSL, and Python
3.12 or newer inside Ubuntu. Keep the Windows `.venv` separate from the WSL
environment.

Open Ubuntu from **PowerShell**:

```powershell
wsl -d Ubuntu
```

Run the following commands **inside WSL**, from the project folder. Adjust the
path if your checkout is elsewhere:

```sh
cd /mnt/c/Users/User/MedBrief
python3 --version
```

Create the Linux environment only if `.research-dev/venv-wsl` does not already
exist:

```sh
python3 -m venv .research-dev/venv-wsl
```

If Ubuntu reports that `ensurepip` is unavailable, install its venv support with
`sudo apt install python3-venv`, then repeat the creation command.

Install both sets of Python dependencies into that same Linux environment:

```sh
./.research-dev/venv-wsl/bin/python -m pip install -r requirements.txt -r scraping/research/requirements.txt
```

Directly naming the Linux interpreter avoids accidentally using Windows Python.
Repeat installation when either requirements file changes.

Compose needs a local `.env` file in the project root containing
`SEARXNG_SECRET=<random value>`. This is an internal SearXNG key, not a paid API
key. If `.env` is missing, create it once **inside WSL**:

```sh
if [ ! -f .env ]; then
    python3 -c "import secrets; from pathlib import Path; Path('.env').write_text('SEARXNG_SECRET=' + secrets.token_hex(32) + '\n', encoding='utf-8')"
fi
```

The `.env` file is ignored by Git. SearXNG settings are in
`searxng/settings.yml`; HTML and JSON responses are enabled.

### Start SearXNG

Open Docker Desktop. In **PowerShell**, from the project root, run:

```powershell
docker compose up -d searxng
docker compose ps
```

The `-d` option runs SearXNG in the background, so this terminal can be closed.
Open <http://localhost:8088> to check its interface. To inspect service messages:

```powershell
docker compose logs --tail=80 searxng
```

### Start the research app

In **WSL**, from the project root, run:

```sh
cd /mnt/c/Users/User/MedBrief
./.research-dev/venv-wsl/bin/python -m streamlit run scraping/research/app.py --server.address 127.0.0.1
```

Keep this terminal open and visit <http://localhost:8501>, or the address printed
by Streamlit. Search requires at least two letters. A new search replaces the
previous results and clears selection; selecting rows updates the counter
without starting another search. Article export is not implemented yet.

The adapter uses automatic routing restricted to free sources, with paid
fallbacks disabled. It can use the local Docker SearXNG instance. Its internal
state is stored under `~/.local/share/medbrief/frankensurf` in WSL, outside the
Windows-mounted project, to avoid filesystem ownership errors.

If search fails, distinguish these cases:

- `No results found.`: the search returned no usable results without a reported failure.
- Partial coverage: useful results were kept, but some sources failed.
- CAPTCHA or access denied: an upstream source refused the request; restarting
  Docker does not guarantee that the source will accept another request.
- `PROVIDER_DOWN`: check the container and whether WSL can reach
  `http://127.0.0.1:8088`. Opening it from Windows alone does not prove WSL access.

### Stop and update

Stop Streamlit with **Ctrl+C** in its WSL terminal. Stop SearXNG from the project
root in PowerShell:

```powershell
docker compose stop searxng
```

Start it again with `docker compose up -d searxng`. To fetch a newer SearXNG image
and recreate the container while keeping its settings and data:

```powershell
docker compose pull searxng
docker compose up -d searxng
```

The `latest` image tag does not automatically update an already downloaded image.

## Uporaba

Ob zagonu aplikacija prebere tri vhodne datoteke, preveri podvojene ID-je in povezave med zapisi ter prikaže meni:

```text
1 - Meritve izbranega pacienta
2 - Meritve z manjkajočo vrednostjo ali enoto
Izberite filter (1/2):
```

### 1. Filtriranje po pacientu

Izberite možnost `1` in vnesite ID pacienta:

```text
Izberite filter (1/2): 1
Vnesite ID pacienta:P001
```

Pri priloženih podatkih filter vrne tri meritve pacienta Marka Novaka:

| Meritev | Dokument | Naziv   | Vrednost | Enota  |
| ------- | -------- | ------- | -------- | ------ |
| `M001`  | `D001`   | HbA1c   | 7.2      | %      |
| `M002`  | `D001`   | Glukoza | 8.1      | mmol/L |
| `M003`  | `D002`   | HbA1c   | 6.8      | %      |

Program rezultate v konzoli izpiše kot slovarje. Sprejet je tudi vnos `p001`, ker se ID pretvori v velike črke.

### 2. Filtriranje nepopolnih meritev

Izberite možnost `2`:

```text
Izberite filter (1/2): 2
```

Filter poišče meritve, pri katerih manjka vrednost ali merska enota. Pri priloženih podatkih vrne:

| Meritev | Manjkajoči podatek |
| ------- | ------------------ |
| `M005`  | Vrednost           |
| `M007`  | Merska enota       |
| `M010`  | Vrednost           |
| `M013`  | Merska enota       |

Neveljavna izbira menija zaključi program s sporočilom `Neveljavna izbira.`

## Podatki in povezave

Vsaka vhodna datoteka vsebuje **15 zapisov**:

| Datoteka             | Vsebina                                                 |
| -------------------- | ------------------------------------------------------- |
| `data/pacienti.xml`  | ID, ime, priimek in datum rojstva pacienta              |
| `data/dokumenti.xml` | ID, pacientId, naziv, vrsta in datum dokumenta          |
| `data/meritve.xml`   | ID, dokumentId, naziv, vrednost, enota in stran meritve |

Vsak zapis ima enolični atribut `id`. Dokument prek atributa `pacientId` pripada pacientu, meritev pa prek atributa `dokumentId` pripada dokumentu.

En pacient ima lahko več dokumentov, en dokument pa več meritev. Aplikacija podatke poveže prek ID-jev in za vsako meritev sestavi zapis s podatki o pacientu ter izvornem dokumentu.

Datoteke vsebujejo besedilna in številčna polja, datume v obliki `YYYY-MM-DD` ter namenoma prazne vrednosti za preizkus filtriranja.

## Izvoz rezultatov

Po izbiri filtra se isti rezultati izpišejo v konzolo in shranijo v:

- [`filtered/filtrirano.json`](filtered/filtrirano.json) — seznam objektov JSON;
- [`filtered/filtrirano.xml`](filtered/filtrirano.xml) — elementi `<meritev>` znotraj korenskega elementa `<meritve>`.

Vsak izvoženi zapis vsebuje podatke o pacientu, meritvi in izvornem dokumentu, vključno z njegovo stranjo. Prazni podatki ostanejo prazni.

Priložena primera izhoda vsebujeta štiri nepopolne meritve, pridobljene z drugim filtrom. Ob naslednjem izvozu se datoteki prepišeta z rezultati nove izbire.

Če filter ne vrne rezultatov, se izvozi prazen seznam JSON in XML brez posameznih meritev. Mapa `filtered/` mora obstajati in je vključena v repozitorij.

## Preverjanje identifikatorjev in povezav

Program prekine izvajanje z napako `ValueError`, če zazna:

- podvojen ID pacienta, dokumenta ali meritve znotraj iste vrste entitet;
- dokument z referenco na neobstoječega pacienta;
- meritev z referenco na neobstoječ dokument.

Manjkajoča vrednost ali enota meritve je dovoljena in se obravnava kot nepopoln podatek.

## Organizacija projekta

| Pot                                      | Namen                                                                |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `py_xml/reading_xml.py`                  | Izvorna koda: branje, preverjanje, povezovanje, filtriranje in izvoz |
| `data/`                                  | Tri vhodne datoteke XML                                              |
| `filtered/`                              | Primera izhoda in rezultati naslednjih zagonov                       |
| `project_info/Predstavitev_Projekta.pdf` | Predstavitev širše projektne ideje                                   |
| `README.md`                              | Opis aplikacije in navodila za uporabo                               |

## Nadaljnji razvoj

Širša zamisel projekta je opisana v [predstavitvi projekta](project_info/Predstavitev_Projekta.pdf). Predvidene nadgradnje vključujejo pridobivanje dokumentov prek Google Drive API-ja, obdelavo PDF-jev, pripravo povzetkov z navedbo virov prek Gemini API-ja ter uporabniški vmesnik za pregled in potrditev rezultatov.

Te funkcionalnosti v trenutni različici še niso implementirane.

## Avtor

Filip Sekulović  
Univerza v Mariboru, FERI  
Informatika in podatkovne tehnologije
