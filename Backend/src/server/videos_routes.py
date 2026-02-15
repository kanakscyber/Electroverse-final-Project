from flask import Blueprint, request, jsonify, current_app, Response
from bson.objectid import ObjectId
from src.server.auth import token_required
from src.encryption import decryption as decryption_mod
import os
from pathlib import Path

bp = Blueprint('videos', __name__)
@bp.route('/video/<video_id>')
@token_required
def stream_video(video_id):
    try:
        db = current_app.config['DB']
        video = db.videos.find_one({'_id': ObjectId(video_id)})
        
        if not video:
            return jsonify({"error": "Video not found"}), 404
            
        cam_id = video.get('camera_id')
        user_payload = request.user
        if user_payload.get('role') != 'admin' and cam_id not in user_payload.get('assigned_cameras', []):
            return jsonify({"error": "Not authorized to view this camera's video"}), 403

        video_data = video.get('video_data')
        if not video_data:
            # Fallback: try to load encrypted file from backend/data/encrypted
            try:
                filename = video.get('filename')
                data_root = Path(__file__).resolve().parents[3] / 'data'
                encrypted_path = data_root / 'encrypted' / filename
                if encrypted_path.exists():
                    with open(encrypted_path, 'rb') as f:
                        video_data = f.read()
                else:
                    return jsonify({"error": "Video data not found"}), 404
            except Exception:
                return jsonify({"error": "Video data not found"}), 404

        return Response(video_data, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": "Video not found"}), 404
    
    
@bp.route('/video/decrypted/<video_id>')
@token_required
def stream_decrypted(video_id):
    try:
        db = current_app.config['DB']
        video = db.videos.find_one({'_id': ObjectId(video_id)})
        
        if not video:
            return jsonify({"error": "Video not found"}), 404
            
        cam_id = video.get('camera_id')
        user_payload = request.user
        if user_payload.get('role') != 'admin' and cam_id not in user_payload.get('assigned_cameras', []):
            return jsonify({"error": "Not authorized to view this camera's video"}), 403

        encrypted_data = video.get('video_data')
        if not encrypted_data:
            # Fallback: try to load encrypted file from backend/data/encrypted
            try:
                filename = video.get('filename')
                data_root = Path(__file__).resolve().parents[3] / 'data'
                encrypted_path = data_root / 'encrypted' / filename
                if encrypted_path.exists():
                    with open(encrypted_path, 'rb') as f:
                        encrypted_data = f.read()
                else:
                    return jsonify({"error": "Video data not found"}), 404
            except Exception:
                return jsonify({"error": "Video data not found"}), 404

        key = decryption_mod.load_key()
        tmp_mp4 = decryption_mod.decrypt_blob_to_path(encrypted_data, key)
        if not tmp_mp4 or not os.path.exists(tmp_mp4):
            return jsonify({"error": "Decryption failed"}), 500

        def generate_file():
            try:
                with open(tmp_mp4, 'rb') as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        yield chunk
            finally:
                try:
                    os.remove(tmp_mp4)
                except Exception:
                    pass

        return Response(generate_file(), mimetype='video/mp4')
    except Exception as e:
        return jsonify({"error": "Video not found"}), 404

# In videos_routes.py - MODIFY the search_videos function

@bp.route('/search')
@token_required
def search_videos():
    plate = request.args.get('plate')
    date_str = request.args.get('date')
    camera_id = request.args.get('camera_id')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    query = {}
    
    # Build query only if filters provided
    if plate:
        query['plate_numbers'] = plate
    if camera_id:
        query['camera_id'] = camera_id

    if date_str:
        try:
            from datetime import datetime, timedelta
            base_date = datetime.strptime(date_str, '%Y-%m-%d')
            if start_time_str and end_time_str:
                t_start = datetime.strptime(start_time_str, '%H:%M:%S').time()
                t_end = datetime.strptime(end_time_str, '%H:%M:%S').time()
                ist_start = datetime.combine(base_date, t_start)
                ist_end = datetime.combine(base_date, t_end)
            else:
                ist_start = base_date
                ist_end = ist_start + timedelta(days=1)
            utc_start = ist_start - timedelta(hours=5, minutes=30)
            utc_end = ist_end - timedelta(hours=5, minutes=30)
            query['upload_date'] = {'$gte': utc_start, '$lt': utc_end}
        except ValueError:
            return jsonify({'error': 'Invalid format. Use Date: YYYY-MM-DD, Time: HH:MM:SS'}), 400

    db = current_app.config['DB']
    
    # Query count for logging
    total_count = db.videos.count_documents({})
    filtered_count = db.videos.count_documents(query) if query else total_count
    
    print(f"[SEARCH] Total videos: {total_count}, Filtered: {filtered_count}, Query: {query}")
    
    # Exclude video_data from results + sort by newest first + limit to 100
    cursor = db.videos.find(query, {'video_data': 0}).sort('upload_date', -1).limit(100)
    
    results = []
    from datetime import timedelta
    for video in cursor:
        utc_time = video.get('upload_date')
        if utc_time:
            ist_time = utc_time + timedelta(hours=5, minutes=30)
            upload_str = ist_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            upload_str = 'Unknown'
            
        results.append({
            'video_id': str(video['_id']),
            'filename': video.get('filename', 'Unknown'),
            'camera_id': video.get('camera_id', 'Unknown'),
            'upload_date_ist': upload_str,
            'plates_found': video.get('plate_numbers', []),
            'file_size': video.get('file_size', 0)
        })
    
    return jsonify({
        'total': total_count,
        'filtered': filtered_count,
        'results': results
    }), 200

@token_required
def update_plate(video_id):
    payload = request.user
    db = current_app.config['DB']
    user = db.users.find_one({'username': payload.get('username')})
    
    if not user or user.get('role') not in ['uploader', 'admin']:
        return jsonify({'error': 'No permission to update metadata'}), 403
    
    data = request.get_json() or {}
    plate_numbers = data.get('plate_numbers')
    if not plate_numbers:
        return jsonify({'error': 'No plate number provided'}), 400
    
    result = db.videos.update_one(
        {'_id': ObjectId(video_id)}, 
        {'$push': {'plate_numbers': plate_numbers}}
    )
    
    if result.matched_count == 0:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify({'message': 'Plate added to metadata'}), 200