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


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code


@app.route('/')
def sitemap():
    return generate_sitemap(app)


@app.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    output = [user.serialize() for user in users]
    return jsonify(output), 200


@app.route('/people', methods=['GET'])
def get_character():
    character_query = Character.query.all()
    results = [item.serialize() for item in character_query]
    return jsonify(results), 200


@app.route('/people/<int:people_id>', methods=['GET'])
def get_character_id(people_id):
    character = Character.query.get(people_id)
    if character is None:
        return jsonify({"msg": "Ese personaje no existe en nuestra galaxia"}), 404
    return jsonify(character.serialize()), 200


@app.route('/people', methods=['POST'])
def add_new_character():
    body = request.get_json()
    new_char = Character(
        name=body.get("name"),
        birth_year=body.get("birth_year"),
        gender=body.get("gender"),
        description=body.get("description")
    )
    db.session.add(new_char)
    db.session.commit()
    return jsonify({"msg": f"Personaje {new_char.name} creado con éxito"}), 201


@app.route('/planets', methods=['GET'])
def get_planets():
    planets_query = Planet.query.all()
    results = [item.serialize() for item in planets_query]
    return jsonify(results), 200


@app.route('/planets/<int:planets_id>', methods=['GET'])
def get_planet_id(planets_id):
    planet = Planet.query.get(planets_id)
    if planet is None:
        return jsonify({"msg": "Ese planeta no existe en nuestra galaxia"}), 404
    return jsonify(planet.serialize()), 200


@app.route('/planets', methods=['POST'])
def add_new_planet():
    body = request.get_json()
    new_planet = Planet(
        name=body.get("name"),
        climate=body.get("climate"),
        population=body.get("population")
    )
    db.session.add(new_planet)
    db.session.commit()
    return jsonify({"msg": f"Planeta {new_planet.name} creado con éxito"}), 201


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


@app.route('/swapi/populate/people', methods=['POST'])
def populate_people():
    response = requests.get("https://swapi.tech/api/people")
    data = response.json()
    for item in data["results"]:
        detail = requests.get(item["url"]).json()["result"]["properties"]
        new_char = Character(
            name=detail["name"],
            birth_year=detail["birth_year"],
            gender=detail["gender"],
            description="Personaje de SWAPI"
        )
        db.session.add(new_char)
    db.session.commit()
    return jsonify({"msg": "Personajes importados"}), 200


@app.route('/swapi/populate/planets', methods=['POST'])
def populate_planets():
    response = requests.get("https://swapi.tech/api/planets")
    data = response.json()
    for item in data["results"]:
        detail = requests.get(item["url"]).json()["result"]["properties"]
        pop = int(detail["population"]
                  ) if detail["population"].isnumeric() else 0
        new_planet = Planet(
            name=detail["name"], climate=detail["climate"], population=pop)
        db.session.add(new_planet)
    db.session.commit()
    return jsonify({"msg": "Planetas importados"}), 200


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=True)
