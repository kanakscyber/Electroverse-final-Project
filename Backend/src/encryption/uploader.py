import os
import time
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from gridfs import GridFSBucket
from bson import ObjectId


class VideoUploader:
    def __init__(
        self,
        watch_dir=os.environ.get('EV_ENC_DIR'),
        mongo_uri=os.environ.get('ev_mongo'),
        camera_id=os.environ.get('EV_CAMERA_ID', 'cam_01'),
        scan_interval=10,
        db_name=os.environ.get('EV_DB_NAME', 'video_storage_db')
    ):
        mongo_uri=os.environ.get('ev_mongo')
        self.watch_dir = Path(watch_dir)
        self.camera_id = camera_id
        self.scan_interval = scan_interval
        print(f"Mongo URI: {mongo_uri}")
        if not mongo_uri:
            raise ValueError("MongoDB URI required (set EV_MONGO)")

        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

        # Use GridFS for large files (avoids BSON 16MB limit and full-file reads)
        self.bucket = GridFSBucket(self.db)

        # Create helpful indexes in the files collection (GridFS uses <prefix>.files)
        # expireAfterSeconds on uploadDate is supported via files collection field 'uploadDate'
        try:
            self.db.fs.files.create_index('uploadDate', expireAfterSeconds=604800)
            self.db.fs.files.create_index('metadata.camera_id')
            self.db.fs.files.create_index('metadata.plate_numbers')
        except Exception:
            pass
        
    def wait_for_stable_file(self, filepath, wait_seconds=3):
        """Wait until file stops growing."""
        if not filepath.exists():
            return False
        
        size1 = filepath.stat().st_size
        time.sleep(wait_seconds)
        
        if not filepath.exists():
            return False
            
        size2 = filepath.stat().st_size
        return size1 == size2
    
    def upload_video(self, filepath):
        """Upload encrypted video to MongoDB."""
        try:
            # Stream the file into GridFS to avoid reading the whole file into memory
            metadata = {
                'camera_id': self.camera_id,
                'plate_numbers': [],
                'original_filename': filepath.name,
            }

            with open(filepath, 'rb') as fh:
                file_id = self.bucket.upload_from_stream(
                    filepath.name,
                    fh,
                    metadata=metadata,
                )

            # file_id is an ObjectId
            print(f"✓ Uploaded (GridFS): {filepath.name} -> {file_id}")

            # Insert a small metadata document into videos collection pointing to GridFS file
            try:
                file_size = filepath.stat().st_size if filepath.exists() else None
                doc = {
                    'filename': filepath.name,
                    'camera_id': self.camera_id,
                    'upload_date': datetime.utcnow(),
                    'plate_numbers': [],
                    'gridfs_id': file_id,
                    'file_size': file_size,
                }
                result = self.db.videos.insert_one(doc)
                print(f"✓ Metadata inserted: {result.inserted_id}")
            except Exception as e:
                print(f"⚠️ Failed to insert metadata doc: {e}")

            # Delete local file after successful upload
            try:
                filepath.unlink()
            except Exception:
                pass

            return result.inserted_id if 'result' in locals() else file_id
            
        except Exception as e:
            print(f"✗ Upload failed: {filepath.name} - {e}")
            return None
    
    def run(self):
        """Main upload loop."""
        print(f"Video uploader started")
        print(f"Watching: {self.watch_dir}")
        print(f"Camera ID: {self.camera_id}")
        print(f"Scan interval: {self.scan_interval}s")
        
        while True:
            try:
                # Find encrypted files
                files = sorted(self.watch_dir.glob("*.WattLagGyi"))
                
                for filepath in files:
                    # Wait for file to stabilize
                    if not self.wait_for_stable_file(filepath):
                        continue
                    
                    # Upload
                    self.upload_video(filepath)
                
            except Exception as e:
                print(f"Error in upload loop: {e}")
            
            time.sleep(self.scan_interval)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload encrypted videos to MongoDB')
    parser.add_argument('--watch-dir', default=os.environ.get('EV_WATCH_DIR', 'data/encrypted'), help='Directory to watch')
    parser.add_argument('--camera-id', default='cam_01', help='Camera identifier')
    parser.add_argument('--interval', type=int, default=10, help='Scan interval (seconds)')
    
    args = parser.parse_args()
    
    uploader = VideoUploader(
        watch_dir=args.watch_dir,
        camera_id=args.camera_id,
        scan_interval=args.interval
    )
    
    uploader.run()


if __name__ == '__main__':
    main()