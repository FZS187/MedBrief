# MedBrief

Konzolna aplikacija v Pythonu za povezovanje podatkov o pacientih, dokumentih in laboratorijskih meritvah iz datotek XML. Omogoča filtriranje po pacientu ali manjkajočih podatkih ter izvoz rezultatov v JSON in XML.

Aplikacija predstavlja začetno podatkovno fazo projekta MedBrief, katerega dolgoročni cilj je AI podpora pri pripravi zdravstvene dokumentacije. Vsi uporabljeni podatki so sintetični.

## Zagon

Potreben je **Python 3.9 ali novejši**. Aplikacija uporablja samo standardne module `xml.etree.ElementTree`, `pathlib` in `json`, zato dodatnih paketov ni treba nameščati.

Klonirajte repozitorij in zaženite aplikacijo:

```bash
git clone https://github.com/FZS187/MedBrief.git
cd MedBrief
python py_xml/reading_xml.py
```

Če vaše okolje uporablja ukaz `python3`, zadnjo komando zamenjajte z:

```bash
python3 py_xml/reading_xml.py
```

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
