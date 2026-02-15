import bcrypt
from datetime import datetime, timezone
import os
from pymongo import MongoClient

# Simple helper functions for user management used by server
client = MongoClient(os.environ.get('ev_mongo'))
db = client.user_storage_db
db.users.create_index("email", unique=True)
db.users.create_index("username", unique=True)


def create_user(username, email, password, role='viewer', cameras=None):
    cameras = cameras or []
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = db.users.insert_one({
        'username': username,
        'email': email,
        'password': hashed_pw,
        'role': role,
        'assigned_cameras': cameras,
        'created_at': datetime.now(timezone.utc)
    }).inserted_id

    return str(user_id)


def find_by_email(email):
    return db.users.find_one({'email': email})


def find_by_username(username):
    return db.users.find_one({'username': username})
