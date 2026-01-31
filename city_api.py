"""
City Scoring API - Version Flask Simple (pour n8n)
API REST simple pour intégration facile avec n8n
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

DATA_FILE = Path(__file__).parent / "cities_data.json"
CITIES_DATA = {}
COUNTRIES = {}


def load_cities_data():
    global CITIES_DATA, COUNTRIES
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            countries_list = json.load(f)
        
        for country_data in countries_list:
            country = country_data["country"]
            COUNTRIES[country] = []
            
            for city_data in country_data["cities"]:
                city_name = city_data["city"]
                city_key = f"{city_name}, {country}"
                
                CITIES_DATA[city_key] = {
                    "city": city_name,
                    "country": country,
                    **city_data
                }
                COUNTRIES[country].append(city_name)
        
        print(f"Données chargées: {len(CITIES_DATA)} villes dans {len(COUNTRIES)} pays")
        
    except FileNotFoundError:
        print(f"Erreur: Le fichier {DATA_FILE} n'existe pas")
    except Exception as e:
        print(f"Erreur lors du chargement des données: {e}")



load_cities_data()


def search_city(city_name: str):
    city_lower = city_name.lower()
    matches = []
    
    for city_key, data in CITIES_DATA.items():
        if city_lower in data["city"].lower():
            matches.append((city_key, data))
    
    return matches


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "cities_loaded": len(CITIES_DATA),
        "countries": len(COUNTRIES)
    })


@app.route('/city/score', methods=['POST'])
def find_city_score():
    """
    Endpoint pour obtenir le score d'une ville
    
    Body JSON:
    {
        "city_name": "Berlin",
        "country": "Germany" (optionnel)
    }
    """
    data = request.get_json()
    city_name = data.get('city_name', '')
    country = data.get('country', '')
    
    if not city_name:
        return jsonify({"error": "city_name requis"}), 400
    
    if not CITIES_DATA:
        return jsonify({
            "error": "Aucune donnée chargée",
            "city": city_name,
            "found": False
        }), 500
    
    matches = search_city(city_name)
    
    if not matches:
        return jsonify({
            "error": "Ville non trouvée",
            "city": city_name,
            "found": False
        }), 404

    if country:
        matches = [m for m in matches if country.lower() in m[1]["country"].lower()]
        if not matches:
            return jsonify({
                "error": f"Ville '{city_name}' non trouvée dans le pays '{country}'",
                "city": city_name,
                "country": country,
                "found": False
            }), 404

    key, city_data = matches[0]

    stage_score = (
        city_data['qualityOfLifeIndex'] * 0.25 +
        city_data['safetyIndex'] * 0.20 +
        city_data['purchasingPowerIndex'] * 0.15 +
        (100 - city_data['costOfLivingIndex']) * 0.15 +
        city_data['healthCareIndex'] * 0.10 +
        (100 - city_data['pollutionIndex']) * 0.10 +
        city_data['climateIndex'] * 0.05
    )

    if stage_score >= 120:
        recommendation = "Excellent choix"
        recommendation_level = "excellent"
    elif stage_score >= 100:
        recommendation = "Bon choix"
        recommendation_level = "good"
    elif stage_score >= 80:
        recommendation = "Choix correct"
        recommendation_level = "average"
    else:
        recommendation = "À considérer avec précaution"
        recommendation_level = "poor"

    return jsonify({
        "found": True,
        "city": city_data['city'],
        "country": city_data['country'],
        "scores": {
            "qualityOfLife": round(city_data['qualityOfLifeIndex'], 1),
            "purchasingPower": round(city_data['purchasingPowerIndex'], 1),
            "safety": round(city_data['safetyIndex'], 1),
            "healthCare": round(city_data['healthCareIndex'], 1),
            "costOfLiving": round(city_data['costOfLivingIndex'], 1),
            "propertyPriceToIncome": round(city_data['propertyPriceToIncomeRatio'], 1),
            "trafficCommuteTime": round(city_data['trafficCommuteTimeIndex'], 1),
            "pollution": round(city_data['pollutionIndex'], 1),
            "climate": round(city_data['climateIndex'], 1)
        },
        "internshipScore": round(stage_score, 1),
        "recommendation": recommendation,
        "recommendationLevel": recommendation_level
    })


@app.route('/cities/list', methods=['GET'])
def list_cities():
    """
    Endpoint pour lister les villes
    
    Query params:
    - country: Filtrer par pays (optionnel)
    - min_quality: Qualité de vie minimale (optionnel)
    - max_cost: Coût de vie maximum (optionnel)
    - limit: Nombre de résultats (défaut: 20)
    """
    country = request.args.get('country', '')
    min_quality = float(request.args.get('min_quality', 0))
    max_cost = float(request.args.get('max_cost', 200))
    limit = int(request.args.get('limit', 20))
    
    if not CITIES_DATA:
        return jsonify({"error": "Aucune donnée chargée", "cities": []}), 500
    
    filtered = []
    
    for key, data in CITIES_DATA.items():
        if country and country.lower() not in data['country'].lower():
            continue
        if data['qualityOfLifeIndex'] < min_quality:
            continue
        if data['costOfLivingIndex'] > max_cost:
            continue
        
        filtered.append({
            "city": data['city'],
            "country": data['country'],
            "qualityOfLife": round(data['qualityOfLifeIndex'], 1),
            "costOfLiving": round(data['costOfLivingIndex'], 1),
            "safety": round(data['safetyIndex'], 1)
        })

    filtered.sort(key=lambda x: x['qualityOfLife'], reverse=True)
    filtered = filtered[:limit]
    
    return jsonify({
        "total": len(filtered),
        "cities": filtered
    })


@app.route('/countries', methods=['GET'])
def get_countries():
    """Endpoint pour obtenir la liste des pays"""
    if not COUNTRIES:
        return jsonify({"error": "Aucune donnée chargée", "countries": []}), 500
    
    countries_list = [
        {
            "country": country,
            "cityCount": len(cities)
        }
        for country, cities in sorted(COUNTRIES.items(), key=lambda x: len(x[1]), reverse=True)
    ]
    
    return jsonify({
        "total": len(COUNTRIES),
        "totalCities": len(CITIES_DATA),
        "countries": countries_list
    })


if __name__ == "__main__":
    if not CITIES_DATA:
        print("\nERREUR: Impossible de démarrer le serveur")
        print(f"   Le fichier {DATA_FILE} est manquant ou vide")
        exit(1)
    
    print(f"\nDémarrage de l'API City Scoring")
    print(f"{len(CITIES_DATA)} villes chargées dans {len(COUNTRIES)} pays")
    print(f"\nEndpoints disponibles:")
    print(f"   GET  /health           - Health check")
    print(f"   POST /city/score       - Obtenir le score d'une ville")
    print(f"   GET  /cities/list      - Lister les villes")
    print(f"   GET  /countries        - Lister les pays")
    print(f"\nAPI démarrée sur http://localhost:8000")
    print(f"Test: curl http://localhost:8000/health\n")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
