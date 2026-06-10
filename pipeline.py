# Bronze
# Partie 1 : Installer, importer les modules et charger acces.log
import re                           # Expressions régulières
import os                           # Accès fichiers système
import csv
from datetime import datetime       # Conversion et extraction de dates
from pymongo import MongoClient     # Connexion et opérations MongoDB

import geoip2 as geo
import pandas as pd

# GeoIP : lookup pays depuis IP
try:
    from geolite2 import geolite2
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False # Mode simulation activé

# Pandas : option pour les agrégations Gold
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Extraction par Regex
# Féterminer le chemin du fichier log (même racine que le programme)
CHEMIN_LOG  = "access.log"
CHEMIN_EXTRANT = "extraction_log.csv"

# Partie 2 : Regex

# Déterminer le pattern regex pour extraire les valeurs
# On teste avec "IP" pour commencer, bonifier par la suite!
# Intéressant, on apprend beaucoup en décortiquant un pattern regex!
# ip_pattern = "(?P<ip>:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
LOG_PATTERN = re.compile(
    #r"\b(?P<ip_1>:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.(?P<ip_2>:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.(?P<ip_3>:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.(?P<ip_4>:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\b\s(?P<identd>\S+)\s(?P<user>\S+)\s\[(?P<raw_timestamp>.+?)\]\s\"(?P<method>\S+)\s(?P<URL>\S+)\s(?P<protocol>[^\"\s]+)\"\s(?P<status_code>\d{3})\s(?P<size>\d+|-)\s\"(?P<referrer>[^\"\s]+)\"\s\"(?P<user_agent>[^\"\s]+)"
    r"\b(?P<ip>((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b\s(?P<identd>\S+)\s(?P<user>\S+)\s\[(?P<raw_timestamp>.+?)\]\s\"(?P<method>\S+)\s(?P<URL>\S+)\s(?P<protocol>[^\"\s]+)\"\s(?P<status_code>\d{3})\s(?P<size>\d+|-)\s\"(?P<referrer>[^\"\s]+)\"\s\"(?P<user_agent>[^\"\s]+)"
)

# Extraire les données du log
def  parse_log(chemin_log, chemin_extrant):
    liste_donnees_extraites = []
    
    # Lire le log
    with open(CHEMIN_LOG, "r", encoding="utf-8") as file:
        for line in file:
            match = LOG_PATTERN.match(line.strip())

            if match:
                # Les amener dans un dictionnaire
                liste_donnees_extraites.append(match.groupdict())

    # Amener les données dans un fichier .csv
    if liste_donnees_extraites:
        # Obtenir les clés à inclure comme colonne .csv
        headers = liste_donnees_extraites[0].keys()

        with open(
            CHEMIN_EXTRANT, "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(liste_donnees_extraites)

        print(f"Extraction de {len(liste_donnees_extraites)} lignes vers {CHEMIN_EXTRANT}")
    else:
        print(f"Échec d'extraction de données du fichier log {CHEMIN_LOG}")

def creer_dictionnaire(input_file):
    # Créer un dictionnaire à partir du fichier intrant
    # input_file constitue un path
    with open(input_file, mode="r", encoding="utf-8") as file:
        log_dict = csv.DictReader(file)
        return list(log_dict)

def convert_timestamp(raw_ts):
    format_string_from_str = "%d/%b/%Y:%H:%M:%S %z"
    format_string_from_timestamp = "%Y-%m-%d %H:%M:%S"
    # Convertir la date dans un format 2024-10-10 13:55:36' ou none si malformé
    for item in raw_ts: # En fait le dictionnaire... le timestamp sera ciblé
        #print(item["raw_timestamp"])
        # En premier lieu, convertir le string dans un format datetime
        # Puis, si bonne donnée, la retransformer dans le format désiré
        try:
            date_obj = datetime.strptime(item["raw_timestamp"], format_string_from_str)
            item["raw_timestamp"] = date_obj.strftime(format_string_from_timestamp)
        except:
            item["raw_timestamp"] = "none"

    #return la liste de dictionnaires une fois traitée
    return raw_ts

def main():
        work_dict = []

        parse_log(CHEMIN_LOG, CHEMIN_EXTRANT)
        work_dict = creer_dictionnaire("extraction_log.csv")
       
        work_dict = convert_timestamp(work_dict)
        print(f"Résultat: {work_dict}")

if __name__ == "__main__":
    main()
