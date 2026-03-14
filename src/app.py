import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Planet, Character, FavoriteCharacter, FavoritePlanet
import requests

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code


@app.route('/')
def sitemap():
    return generate_sitemap(app)


@app.route('/users', methods=['GET'])
def get_users():
    users_query = User.query.all()
    results = list(map(lambda item: item.serialize(), users_query))
    return jsonify(results), 200


@app.route('/people', methods=['GET'])
def get_character():
    character_query = Character.query.all()
    results = list(map(lambda item: item.serialize(), character_query))
    return jsonify(results), 200


@app.route('/people/<int:people_id>', methods=['GET'])
def get_character_id(people_id):
    character = Character.query.get(people_id)
    if character is None:
        return jsonify({"msg": "Ese personaje no existe en nuestra galaxia"}), 404
    return jsonify(character.serialize()), 200


@app.route('/planets', methods=['GET'])
def get_planets():
    planets_query = Planet.query.all()
    results = list(map(lambda item: item.serialize(), planets_query))
    return jsonify(results), 200


@app.route('/planets/<int:planets_id>', methods=['GET'])
def get_planet_id(planets_id):
    planet = Planet.query.get(planets_id)
    if planet is None:
        return jsonify({"msg": "Ese planeta no existe en nuestra galaxia"}), 404
    return jsonify(planet.serialize()), 200


@app.route('/users/favorites', methods=['GET'])
def get_user_favorites():
    user = User.query.get(1)
    if user is None:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    fav_characters = [fav.serialize() for fav in user.favorite_characters]
    fav_planets = [fav.serialize() for fav in user.favorite_planets]
    return jsonify({
        "favorite_characters": fav_characters,
        "favorite_planets": fav_planets
    }), 200


@app.route('/favorite/people/<int:people_id>', methods=['POST'])
def add_favorite_people(people_id):
    character = Character.query.get(people_id)
    if character is None:
        return jsonify({"msg": "El personaje no existe"}), 404
    new_fav_char = FavoriteCharacter(user_id=1, character_id=people_id)
    db.session.add(new_fav_char)
    db.session.commit()

    return jsonify({"msg": f"Personaje {character.name} añadido a favoritos"}), 200


@app.route('/favorite/planet/<int:planet_id>', methods=['POST'])
def add_favorite_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if planet is None:
        return jsonify({"msg": "El planeta no existe"}), 404
    new_favorite = FavoritePlanet(user_id=1, planet_id=planet_id)
    db.session.add(new_favorite)
    db.session.commit()
    return jsonify({"msg": f"Planeta {planet.name} añadido a favoritos"}), 200


@app.route('/favorite/planet/<int:planet_id>', methods=['DELETE'])
def delete_favorite_planet(planet_id):
    favorite = FavoritePlanet.query.filter_by(
        user_id=1, planet_id=planet_id).first()

    if favorite is None:
        return jsonify({"msg": "Ese planeta no está en tus favoritos"}), 404
    db.session.delete(favorite)
    db.session.commit()

    return jsonify({"msg": "Planeta eliminado de favoritos"}), 200


@app.route('/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_people(people_id):
    favorite = FavoriteCharacter.query.filter_by(
        user_id=1, character_id=people_id).first()

    if favorite is None:
        return jsonify({"msg": "Ese personaje no está en tus favoritos"}), 404
    db.session.delete(favorite)
    db.session.commit()

    return jsonify({"msg": "Personaje eliminado de favoritos"}), 200


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)


@app.route('/swapi/people', methods=['GET'])
def get_swapi_people():
    response = requests.get("https://swapi.tech/api/people")

    if response.status_code == 200:
        data = response.json()
        return jsonify(data["results"]), 200

    return jsonify({"msg": "Error al conectar con SWAPI"}), 500


@app.route('/swapi/populate/people', methods=['POST'])
def populate_people():
    response = requests.get("https://swapi.tech/api/people")
    data = response.json()
    characters_list = data["results"]

    for item in characters_list:
        detail_response = requests.get(item["url"])
        detail_data = detail_response.json()
        props = detail_data["result"]["properties"]

        new_char = Character(
            name=props["name"],
            birth_year=props["birth_year"],
            gender=props["gender"],
            description=detail_data["result"]["description"]
        )
        db.session.add(new_char)
    
    db.session.commit()
    return jsonify({"msg": f"Se han importado {len(characters_list)} personajes con detalles"}), 200

@app.route('/swapi/populate/planets', methods=['POST'])
def populate_planets():
    response = requests.get("https://swapi.tech/api/planets")
    data = response.json()
    planets_list = data["results"]

    for item in planets_list:
        detail_response = requests.get(item["url"])
        detail_data = detail_response.json()
        props = detail_data["result"]["properties"]
        pop = int(props["population"]) if props["population"].isnumeric() else 0

        new_planet = Planet(
            name=props["name"],
            climate=props["climate"],
            population=pop
        )
        db.session.add(new_planet)
    
    db.session.commit()
    return jsonify({"msg": f"Se han importado {len(planets_list)} planetas con detalles"}), 200