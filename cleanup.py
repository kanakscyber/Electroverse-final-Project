from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.video_storage_db

def cleanup_orphaned_chunks():
    # 1. Get all file IDs that actually exist in fs.files
    valid_ids = db.fs.files.distinct("_id")
    
    # 2. Delete any chunks that DON'T belong to those IDs
    result = db.fs.chunks.delete_many({"files_id": {"$nin": valid_ids}})
    
    print(f"Cleanup complete. Removed {result.deleted_count} orphaned video chunks.")

if __name__ == "__main__":
    cleanup_orphaned_chunks()