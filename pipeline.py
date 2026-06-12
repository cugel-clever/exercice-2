# Bronze
# Partie 1 : Installer, importer les modules et charger acces.log
import re                           # Expressions régulières
import os                           # Accès fichiers système
import csv
from datetime import datetime       # Conversion et extraction de dates
from pymongo import MongoClient     # Connexion et opérations MongoDB
from typing import List, Dict, Any
import logging

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
LOG_PATTERN = re.compile(
    r"\b(?P<ip>((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b\s(?P<identd>\S+)\s(?P<user>\S+)\s\[(?P<raw_timestamp>.+?)\]\s\"(?P<method>\S+)\s(?P<URL>\S+)\s(?P<protocol>[^\"\s]+)\"\s(?P<status_code>\d{3})\s(?P<size>\d+|-)\s\"(?P<referrer>[^\"\s]+)\"\s\"(?P<user_agent>[^\"\s]+)"
)

def  parse_log(chemin_log, chemin_extrant):
    # Extraire les données du log
    liste_donnees_extraites = []
    
    # Lire le log
    with open(CHEMIN_LOG, "r", encoding="utf-8") as file:
        for line in file:
            match = LOG_PATTERN.match(line.strip())

            if match:
                # Les amener dans un dictionnaire
                # Les occurrences erronées ne seront pas incluses
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

def convert_timestamp(input_dict):
    format_string_from_str = "%d/%b/%Y:%H:%M:%S %z"
    format_string_from_timestamp = "%Y-%m-%d %H:%M:%S"
    # Convertir la date dans un format 2024-10-10 13:55:36' ou none si malformé
    for item in input_dict: # Le timestamp sera ciblé
        # En premier lieu, convertir le string dans un format datetime
        # Puis, si bonne donnée, la retransformer dans le format désiré
        try:
            date_obj = datetime.strptime(item["raw_timestamp"], format_string_from_str)
            item["raw_timestamp"] = date_obj.strftime(format_string_from_timestamp)
        except:
            item["raw_timestamp"] = "None"

    # Retourner la liste de dictionnaires une fois traitée
    return input_dict

def extract_hour(input_dict):
    # Extraire l'heure pour permettre l'agrégation temporelle en couche Gold.
    # Implique d'ajouter une colonne au dictionnaire

    HOUR_PATTERN = re.compile(
       r"(?<=\s)\d{1,2}(?=:)"
    )

    for item in input_dict: # Le timestamp sera ciblé
        match = re.search(HOUR_PATTERN, item["raw_timestamp"])

        if match:
            item["hour"] = match.group(0)
        else:
            item["hour"] = "None"

    # Retourner la liste de dictionnaires une fois traitée
    return input_dict

def get_status_category(input_dict):
    # Méthode pour produire le statut d'un code http
    # Division entière du code, puis selon la valeur obtenue,
    # insertion de la chaîne de caractère dans une nouvelle
    # colonne "status_category"
    for item in input_dict:
        code = int(item["status_code"] ) // 100
        if code == 2:
            code_str = "Success"
        elif code == 3:
            code_str = "Redirection"
        elif code == 4:
            code_str = "Client Error"
        elif code == 5:
            code_str = "Server _Error"
        else:
            code_str = "Unknown status code"
        
        item["status_category"] = code_str

    # Retourner la liste de dictionnaires une fois traitée
    return input_dict

def create_csv_file(input_dict):

    # Le fichier à produire
    csv_file = "output_logs.csv"

    # Extraire les noms des colonnes
    keys = input_dict[0].keys()

    # Ouvrir le fichier et inscrire les occurrences
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        
        # Ajouter les colonnes
        writer.writeheader()
        
        # Pousser le dictionnaire en un bloc
        writer.writerows(input_dict)

    print(f"Extraction de {len(input_dict)} lignes vers {csv_file}!")

def get_country(input_dict):
    # Si IP privée (10.x, 192.168.x, 172.16-31.x, 127.x) ==> 'Private/Local'
    # Sinon utiliser geolite2.reader().get(ip)
    import geoip2.database
    
    with geoip2.database.Reader("GeoLite2-Country.mmdb") as reader:
        for item in input_dict:
            # IP privées
            if match := re.match(r"10.", item["ip"]):
                ip_country = "Private/Local"
            elif match := re.match(r"1.1.1.1", item["ip"]):
                ip_country = "Cloudflare DNS"
            elif match := re.match(r"192.168.", item["ip"]):
                ip_country = "Private/Local"
            elif match := re.match(r"172.16.31.", item["ip"]):
                ip_country = "Private/Local"
            elif match := re.match(r"127.", item["ip"]):
                ip_country = "Private/Local"
            else: # Ici ce sont les ip qui sont à géolocaliser
                try:
                    response = reader.country(item["ip"])
                    ip_country = response.country.name
                except:
                    ip_country = "Adresse IP inconnue"

            item["country"] = ip_country

    return input_dict

def normalize_url(input_dict):
    for item in input_dict:
        base_url = item["URL"].split('?')[0]
        item["URL"] = base_url

    # Retourner la liste de dictionnaires une fois traitée
    return input_dict

def clean_transform(input_dict):
    # Contrairement à ce qui est inscrit dans l'énoncé du tp, pas
    # d'orchestration, mais on remplacera les "-" par "None" pour
    # tous les champs qui en ont.
    # ip: OK
    # identd : À nettoyer
    # user : À nettoyer
    # raw_timestamp : OK
    # method : OK
    # URL : OK
    # protocol : OK
    # status : OK
    # size : À nettoyer
    # referrer : À nettoyer
    # user_agent : À nettoyer
    # hour : OK
    # country : OK

    for item in input_dict:
        if item["identd"] == "-":
            none_value = "None"
            item["identd"] = none_value

        if item["user"] == "-":
            none_value = "None"
            item["user"] = none_value       

        if item["size"] == "-":
            none_value = "None"
            item["size"] = none_value       

        if item["referrer"] == "-":
            none_value = "None"
            item["referrer"] = none_value       

        if item["user_agent"] == "-":
            none_value = "None"
            item["user_agent"] = none_value       

    # Retourner la liste de dictionnaires une fois traitée
    return input_dict

def final_transform(input_dict):
        # Ok, ici on ne conserve que les colonnes requises
        # Colonne exclue : "identd"
        # Colonne à renommer: raw_timestamp --> timestamp
        # Colonne à renommer: URL --> url
        

    for item in input_dict:
        if "identd" in item:
            item.pop("identd")
        
        if "raw_timestamp" in item:
            item["timestamp"] = item.pop("raw_timestamp")

        if "URL" in item:
            item["url"] = item.pop("URL")

    # Réordonnancer les colonnes
    ordre_souhaite = ["ip", "user", "timestamp", "hour", "method", "url", "protocol", "status_code", "status_category", "size", "referrer", "user_agent", "country"]
    work_dict2 = []

    # Boucle pour ordonnancer le tout
    for item2 in input_dict:
        nouveau_dict = {}

        # Recréer le dictionnaire
        for key in ordre_souhaite:
            if key in item2:
                nouveau_dict[key] = item2[key]

        work_dict2.append(nouveau_dict)

    return work_dict2

def load_to_mongodb(data: List[Dict[str, Any]]) -> None:
    # Configuration MongoDB
    MONGO_URI = "mongodb://localhost:27017/"  # À changer si remote DB
    DB_NAME = "weblog_db"
    COLLECTION_SILVER_NAME = "access_logs"

    # Créer et configurer le logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if not data:
        logger.info("Aucune donnée à amener dans MongoDB.")
        return

    try:
        # Connection à MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_SILVER_NAME]

        # Insérer les données
        result = collection.insert_many(data)
        logger.info("✅ Insertion réussie de ", len(result.inserted_ids), "occurrences dans ",DB_NAME,"\s",{COLLECTION_SILVER_NAME})
        client.close()

    except Exception as e:
        logger.error("Failed to save data to MongoDB: ", e)
        raise

def main():
        work_dict = []

        parse_log(CHEMIN_LOG, CHEMIN_EXTRANT)
        work_dict = creer_dictionnaire("extraction_log.csv")
       
        work_dict = convert_timestamp(work_dict)

        work_dict = extract_hour(work_dict)

        work_dict = get_status_category(work_dict)
        
        work_dict = get_country(work_dict)

        work_dict = normalize_url(work_dict)

        work_dict = clean_transform(work_dict)

        dict_final = final_transform(work_dict)

        #create_csv_file(dict_final)

        load_to_mongodb(dict_final)
        
if __name__ == "__main__":
    main()
