import os
from pymongo import MongoClient

mongo_url = os.environ.get('EV_MONGO')
print(f"Connecting to: {mongo_url}")

client = MongoClient(mongo_url)
db = client.video_storage_db

print(f"\nDatabase: {db.name}")
print(f"Collections: {db.list_collection_names()}")
print(f"\nfs.files count: {db.fs.files.count_documents({})}")
print(f"fs.chunks count: {db.fs.chunks.count_documents({})}")

if db.fs.files.count_documents({}) > 0:
    print("\n--- Sample documents in fs.files ---")
    for doc in db.fs.files.find().limit(3):
        print(f"\nID: {doc['_id']}")
        print(f"Filename: {doc['filename']}")
        print(f"Upload Date: {doc['uploadDate']}")
        print(f"Metadata: {doc.get('metadata')}")
else:
    print("\n✗ No files found in GridFS!")
