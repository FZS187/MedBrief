import xml.etree.ElementTree as ET
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent

PACIENTI_PATH = BASE_DIR / "data" / "pacienti.xml"
DOKUMENTI_PATH = BASE_DIR / "data" / "dokumenti.xml"
MERITVE_PATH = BASE_DIR / "data" / "meritve.xml"

def proveri_veze(pacienti, dokumenti, meritve):
    pacient_ids = {p["id"] for p in pacienti}
    dokument_ids = {d["id"] for d in dokumenti}

    for dokument in dokumenti:
        if dokument["pacientId"] not in pacient_ids:
            raise ValueError(
                f"Dokument {dokument['id']}: "
                f"pacient {dokument['pacientId']} ne obstaja."
            )

    for meritev in meritve:
        if meritev["dokumentId"] not in dokument_ids:
            raise ValueError(
                f"Meritev {meritev['id']}: "
                f"dokument {meritev['dokumentId']} ne obstaja."
            )


def ucitaj_paciente(putanja):
    stablo = ET.parse(putanja)
    koren = stablo.getroot()

    pacienti = []
    vidjeni_id = set() #prazan skup napravis 

    for element in koren.findall('pacient'):
        pacient_id = element.get("id")

        if pacient_id in vidjeni_id:
            raise ValueError(f"Podvojen ID pacienta: {pacient_id}")

        vidjeni_id.add(pacient_id)

        pacient = {
            "id": element.get("id"),
            "ime": element.findtext("ime"),
            "priimek": element.findtext("priimek"),
            "datumRojstva": element.findtext("datumRojstva")
        }
        pacienti.append(pacient)

    return pacienti




def ucitaj_dokumente(putanja):
    stablo = ET.parse(putanja)
    koren = stablo.getroot()

    dokumenti = []
    vidjeni_id = set()

    for element in koren.findall('dokument'):

        dokument_id = element.get("id")

        if dokument_id in vidjeni_id:
            raise ValueError(f"Podvojen ID dokumenta: {dokument_id}")

        vidjeni_id.add(dokument_id)

        dokument = {
            "id": element.get("id"),
            "pacientId": element.get("pacientId"),
            "naziv": element.findtext("naziv"),
            "vrsta": element.findtext("vrsta"),
            "datum": element.findtext("datum")
        }
        dokumenti.append(dokument)

    return dokumenti 



def ucitaj_meritve(putanja):
    stablo = ET.parse(putanja)
    koren = stablo.getroot()

    meritve = []
    vidjeni_id = set()


    for element in koren.findall('meritev'):
        meritev_id  = element.get("id")
        if meritev_id in vidjeni_id:
            raise ValueError(f"Podvojen ID meritve: {meritev_id}")

        vidjeni_id.add(meritev_id)
        
        meritev = {
            "id": element.get("id"),
            "dokumentId": element.get("dokumentId"),
            "naziv": element.findtext("naziv"),
            "vrednost": element.findtext("vrednost"),
            "enota": element.findtext("enota"),
            "stran": element.findtext("stran")

        }
        meritve.append(meritev)

    return meritve

def povezi_podatke(pacienti, dokumenti, meritve):
    pacienti_po_id = {
        pacient["id"]: pacient   # uzmi samo kljuc iz vrednosti pacient
        for pacient in pacienti
    }    
    dokumenti_po_id = {
        dokument["id"]:dokument
        for dokument in dokumenti
    }

    rezultati = []

    for meritev in meritve:
        dokument = dokumenti_po_id[meritev["dokumentId"]]  #spojis po FK iz meritve
        pacient = pacienti_po_id[dokument["pacientId"]]

        rezultat = {
            "pacientId": pacient["id"],
            "ime": pacient["ime"],
            "priimek": pacient["priimek"],
            "dokumentId": dokument["id"],
            "dokumentNaziv": dokument["naziv"],
            "datum": dokument["datum"],
            "meritevId": meritev["id"],
            "naziv": meritev["naziv"],
            "vrednost": meritev["vrednost"],
            "enota": meritev["enota"],
            "stran": meritev["stran"]
        }

        rezultati.append(rezultat)

    return rezultati

def filtriraj_po_pacijentu(povezani_podatki, pacient_id):
    filtrirano = []

    for zapis in povezani_podatki:
        if zapis["pacientId"] == pacient_id:
            filtrirano.append(zapis)
    return filtrirano

def filtriraj_nepopolne(povezani_podatki):
    filtrirano = []

    for zapis in povezani_podatki:
        if not zapis['vrednost'] or not zapis['enota']:
            filtrirano.append(zapis)
    return filtrirano
    




def izvezi_json(podatki, putanja):
    with open(putanja, "w", encoding='utf-8') as fajl:
        json.dump(podatki, fajl, ensure_ascii=False, indent=4)

def izvezi_xml(podatki, putanja):
    koren = ET.Element("meritve")

    for zapis in podatki:
        meritev = ET.SubElement(
            koren, "meritev", id=zapis["meritevId"]
        )

        for kljuc, vrednost in zapis.items():
            if kljuc == "meritevId":
                continue

            polje = ET.SubElement(meritev, kljuc)
            polje.text = "" if vrednost is None else str(vrednost)

    ET.indent(koren, space="    ")

    stablo = ET.ElementTree(koren)
    stablo.write(
        putanja,
        encoding="utf-8",
        xml_declaration=True
    )



pacienti = ucitaj_paciente(PACIENTI_PATH)
dokumenti = ucitaj_dokumente(DOKUMENTI_PATH)
meritve = ucitaj_meritve(MERITVE_PATH)
proveri_veze(pacienti, dokumenti, meritve)

povezani_podatki = povezi_podatke(pacienti,dokumenti, meritve)
# print(povezani_podatki[0])




# for pacient in pacienti:
#     print(f"Pacient: {pacient}\n")

# for doc in dokumenti:
#     print(f"Dokument: {doc} \n")

# for mer in meritve:
#     print(f"Meritev: {mer} \n")

print("1 - Meritve izbranega pacienta")
print("2 - Meritve z manjkajočo vrednostjo ali enoto")

izbor = input("Izberite filter (1/2): ").strip()

if izbor == '1':
    pacient_id = input("Vnesite ID pacienta:").strip().upper()

    filtrirano = filtriraj_po_pacijentu(povezani_podatki, pacient_id)


elif izbor == '2':
    filtrirano = filtriraj_nepopolne(povezani_podatki)
else:
    raise SystemExit("Neveljavna izbira.")


for zapis in filtrirano:
    print(zapis)

if not filtrirano:
    print("Za izbranega pacienta ni meritev.")

    
izvezi_json(filtrirano, BASE_DIR / "filtered" /  "filtrirano.json")
izvezi_xml(filtrirano, BASE_DIR / "filtered" / "filtrirano.xml")
