from flask import Flask, request, Response, jsonify
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from cleanup import cleanup_orphaned_chunks
app = Flask(__name__)

# 1. Connect to Mongo
client = MongoClient("mongodb://localhost:27017/")
db = client.video_storage_db
#Clean data after 7 days
db.fs.files.create_index("uploadDate",expireAfterSeconds=604800)
fs = gridfs.GridFS(db)

# 2. Set upload limit (e.g., 500MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

@app.route('/')
def home():
    return "Video Server is Running"

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['video']
    
    # GridFS stores the file and returns a unique ID
    file_id = fs.put(file, filename=file.filename, content_type=file.content_type)
    
    return jsonify({"video_id": str(file_id)}), 201

# Playing the video
@app.route('/video/<video_id>')
def stream_video(video_id):
    try:
        # Fetch file from GridFS
        video_file = fs.get(ObjectId(video_id))
        
        # Stream it chunk by chunk
        def generate():
            for chunk in video_file:
                yield chunk

        return Response(generate(), mimetype='video/mp4')
    except:
        return "Video not found", 404

# Updates number plate to db
@app.route('/update_plate/<video_id>', methods=['PATCH'])
def update_plate(video_id):
    # Get the extracted text from the OCR person's request
    data = request.get_json()
    plate_number = data.get('plate_number')

    if not plate_number:
        return jsonify({"error": "No plate number provided"}), 400

    # Find the video in MongoDB and update its metadata
    result = db.fs.files.update_one(
        {"_id": ObjectId(video_id)},
        {"$set": {"metadata.plate_number": plate_number}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Video not found"}), 404

    return jsonify({"message": "Plate number updated successfully"}), 200

#Searching by number plate
@app.route('/search/<plate>')
def search_by_plate(plate):
    # Search inside the metadata object we created
    video = db.fs.files.find_one({"metadata.plate_number": plate})
    
    if video:
        return jsonify({
            "video_id": str(video['_id']),
            "filename": video['filename'],
            "upload_date": video['uploadDate']
        })
    return jsonify({"error": "No video found for this plate"}), 404


if __name__ == '__main__':
    #Cleaning the remaining chunks
    cleanup_orphaned_chunks()
    app.run(debug=True)
