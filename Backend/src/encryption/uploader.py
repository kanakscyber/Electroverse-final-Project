import os
import time
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from bson import Binary


class VideoUploader:
    def __init__(
        self,
        watch_dir=os.environ.get('EV_ENC_DIR'),
        mongo_uri="mongodb+srv://sahilagarwal20052005_db_user:vbIHjKrDK0ptYEjm@cluster0.jaadrfz.mongodb.net/",
        camera_id=os.environ.get('EV_CAMERA_ID', 'cam_01'),
        scan_interval=10,
        db_name=os.environ.get('EV_DB_NAME', 'electroverse')
    ):
        self.watch_dir = Path(watch_dir)
        self.camera_id = camera_id
        self.scan_interval = scan_interval
        print(f"Mongo URI: {mongo_uri}")
        if not mongo_uri:
            raise ValueError("MongoDB URI required")
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.videos_collection = self.db.videos
        
        # Create indexes
        self.videos_collection.create_index('upload_date', expireAfterSeconds=604800)
        self.videos_collection.create_index('camera_id')
        self.videos_collection.create_index('plate_numbers')
        
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
            # Read encrypted file
            with open(filepath, 'rb') as f:
                video_data = f.read()
            
            # Create document
            doc = {
                'filename': filepath.name,
                'camera_id': self.camera_id,
                'upload_date': datetime.utcnow(),
                'plate_numbers': [],
                'video_data': Binary(video_data),
                'file_size': len(video_data)
            }
            
            # Insert to MongoDB
            result = self.videos_collection.insert_one(doc)
            
            print(f"✓ Uploaded: {filepath.name} ({len(video_data)} bytes) -> {result.inserted_id}")
            
            # Delete local file after successful upload
            filepath.unlink()
            
            return result.inserted_id
            
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