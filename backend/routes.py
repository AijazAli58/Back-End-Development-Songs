from . import app
import os
import json
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

mongodb_service = os.environ.get('MONGODB_SERVICE', '127.0.0.1')
mongodb_username = os.environ.get('MONGODB_USERNAME', None)
mongodb_password = os.environ.get('MONGODB_PASSWORD', None)

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service is None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}/?authSource=admin"
else:
    url = f"mongodb://{mongodb_service}"

print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
    db = client.songs
    db.songs.drop()
    db.songs.insert_many(songs_list)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")
    sys.exit(1)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# RETURN HEALTH OF THE APP
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK"}), 200

######################################################################
# COUNT THE NUMBER OF DOCUMENTS IN THE SONGS COLLECTION
######################################################################
@app.route("/count", methods=["GET"])
def count():
    try:
        count = db.songs.count_documents({})
        return jsonify({"count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

######################################################################
# GET ALL SONGS
######################################################################
@app.route("/song", methods=["GET"])
def get_songs():
    try:
        songs = list(db.songs.find({}))
        return jsonify({"songs": parse_json(songs)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

######################################################################
# GET A SONG BY ID
######################################################################
@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    try:
        song = db.songs.find_one({"id": id})
        if song:
            return jsonify(parse_json(song)), 200
        else:
            return jsonify({"message": "song with id not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

######################################################################
# CREATE A SONG
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    try:
        if not request.json or 'id' not in request.json:
            abort(400, "Bad request. JSON data and 'id' field are required.")
        
        new_song = request.json
        if db.songs.find_one({"id": new_song["id"]}):
            return jsonify({"Message": f"song with id {new_song['id']} already present"}), 302

        result = db.songs.insert_one(new_song)
        return jsonify({"inserted id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

######################################################################
# UPDATE A SONG
######################################################################
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    try:
        if not request.json:
            abort(400, "Bad request. JSON data is required.")

        song = db.songs.find_one({"id": id})
        if song:
            updated_song = request.json
            result = db.songs.update_one({"id": id}, {"$set": updated_song})
            if result.modified_count == 0:
                return jsonify({"message": "song found, but nothing updated"}), 200
            else:
                return jsonify(parse_json(db.songs.find_one({"id": id}))), 200
        else:
            return jsonify({"message": "song with id not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

######################################################################
# DELETE A SONG
######################################################################
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    try:
        result = db.songs.delete_one({"id": id})
        if result.deleted_count == 0:
            return jsonify({"message": "song not found"}), 404
        else:
            return '', 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("songs application.")
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=True)  # Launch built-in web server and run this Flask webapp
