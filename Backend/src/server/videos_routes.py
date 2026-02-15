from flask import Blueprint, request, jsonify, current_app, Response
from bson.objectid import ObjectId
from src.server.auth import token_required
from src.encryption import decryption as decryption_mod
import os
from pathlib import Path
from gridfs import GridFSBucket
import tempfile

bp = Blueprint('videos', __name__)
@bp.route('/video/<video_id>')
@token_required
def stream_video(video_id):
    # Return decrypted stream by default for frontend compatibility
    db = current_app.config['DB']
    video = db.videos.find_one({'_id': ObjectId(video_id)})

    if not video:
        return jsonify({"error": "Video not found"}), 404

    cam_id = video.get('camera_id')
    user_payload = request.user
    if user_payload.get('role') != 'admin' and cam_id not in user_payload.get('assigned_cameras', []):
        return jsonify({"error": "Not authorized to view this camera's video"}), 403

    range_header = request.headers.get('Range', None)
    return _decrypted_response_for_video(db, video, range_header)


def _decrypted_response_for_video(db, video, range_header=None):
    """Helper: returns a Flask Response streaming the decrypted MP4 for the given video document.
    Supports Range requests by decrypting to a temp file when a Range header is present.
    """
    key = decryption_mod.load_key()

    def send_range_from_file(path):
        file_size = os.path.getsize(path)
        if not range_header:
            def gen():
                with open(path, 'rb') as f:
                    try:
                        while True:
                            chunk = f.read(64 * 1024)
                            if not chunk:
                                break
                            yield chunk
                    finally:
                        try:
                            os.remove(path)
                        except Exception:
                            pass

            return Response(gen(), status=200, mimetype='video/mp4', headers={
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes'
            })

        try:
            units, rng = range_header.split('=')
            start_str, end_str = rng.split('-')
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        except Exception:
            return jsonify({'error': 'Invalid Range header'}), 400

        if start >= file_size:
            return Response(status=416)

        end = min(end, file_size - 1)
        length = end - start + 1

        def partial_gen():
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                try:
                    while remaining > 0:
                        chunk_size = min(64 * 1024, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
                finally:
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
        }
        return Response(partial_gen(), status=206, mimetype='video/mp4', headers=headers)

    # Inline blob
    encrypted_data = video.get('video_data')
    if encrypted_data:
        tmp_mp4 = decryption_mod.decrypt_blob_to_path(encrypted_data, key)
        if not tmp_mp4 or not os.path.exists(tmp_mp4):
            return jsonify({"error": "Decryption failed"}), 500

        return send_range_from_file(tmp_mp4)

    # GridFS
    gridfs_id = video.get('gridfs_id')
    if gridfs_id:
        try:
            bucket = GridFSBucket(db)
            grid_out = bucket.open_download_stream(ObjectId(gridfs_id))

            if range_header:
                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tmpf.close()
                ok = decryption_mod.decrypt_stream_to_path(grid_out, tmpf.name, key)
                try:
                    grid_out.close()
                except Exception:
                    pass
                if not ok:
                    try:
                        os.remove(tmpf.name)
                    except Exception:
                        pass
                    return jsonify({"error": "Decryption failed"}), 500

                return send_range_from_file(tmpf.name)

            def decrypted_gen():
                try:
                    for chunk in decryption_mod.decrypt_stream_generator(grid_out, key):
                        yield chunk
                finally:
                    try:
                        grid_out.close()
                    except Exception:
                        pass

            return Response(decrypted_gen(), mimetype='video/mp4', headers={'Accept-Ranges': 'bytes'})
        except Exception:
            return jsonify({"error": "Decryption failed"}), 500

    # Disk fallback
    try:
        filename = video.get('filename')
        data_root = Path(__file__).resolve().parents[3] / 'data'
        encrypted_path = data_root / 'encrypted' / filename
        if encrypted_path.exists():
            fobj = open(encrypted_path, 'rb')

            if range_header:
                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tmpf.close()
                ok = decryption_mod.decrypt_stream_to_path(fobj, tmpf.name, key)
                try:
                    fobj.close()
                except Exception:
                    pass
                if not ok:
                    try:
                        os.remove(tmpf.name)
                    except Exception:
                        pass
                    return jsonify({"error": "Decryption failed"}), 500

                return send_range_from_file(tmpf.name)

            def decrypted_file_gen():
                try:
                    for chunk in decryption_mod.decrypt_stream_generator(fobj, key):
                        yield chunk
                finally:
                    try:
                        fobj.close()
                    except Exception:
                        pass

            return Response(decrypted_file_gen(), mimetype='video/mp4', headers={'Accept-Ranges': 'bytes'})
        else:
            return jsonify({"error": "Video data not found"}), 404
    except Exception:
        return jsonify({"error": "Video not found"}), 404
    
    
@bp.route('/video/decrypted/<video_id>')
@token_required
def stream_decrypted(video_id):
    db = current_app.config['DB']
    video = db.videos.find_one({'_id': ObjectId(video_id)})

    if not video:
        return jsonify({"error": "Video not found"}), 404

    cam_id = video.get('camera_id')
    user_payload = request.user
    if user_payload.get('role') != 'admin' and cam_id not in user_payload.get('assigned_cameras', []):
        return jsonify({"error": "Not authorized to view this camera's video"}), 403

    key = decryption_mod.load_key()

    range_header = request.headers.get('Range', None)

    def send_range_from_file(path):
        file_size = os.path.getsize(path)
        if not range_header:
            def gen():
                with open(path, 'rb') as f:
                    try:
                        while True:
                            chunk = f.read(64 * 1024)
                            if not chunk:
                                break
                            yield chunk
                    finally:
                        try:
                            os.remove(path)
                        except Exception:
                            pass

            return Response(gen(), status=200, mimetype='video/mp4', headers={
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes'
            })

        # Parse range
        try:
            units, rng = range_header.split('=')
            start_str, end_str = rng.split('-')
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        except Exception:
            return jsonify({'error': 'Invalid Range header'}), 400

        if start >= file_size:
            return Response(status=416)

        end = min(end, file_size - 1)
        length = end - start + 1

        def partial_gen():
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                try:
                    while remaining > 0:
                        chunk_size = min(64 * 1024, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
                finally:
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
        }
        return Response(partial_gen(), status=206, mimetype='video/mp4', headers=headers)

    # If encrypted blob stored directly on document (legacy), decrypt to temp file for range support
    encrypted_data = video.get('video_data')
    if encrypted_data:
        tmp_mp4 = decryption_mod.decrypt_blob_to_path(encrypted_data, key)
        if not tmp_mp4 or not os.path.exists(tmp_mp4):
            return jsonify({"error": "Decryption failed"}), 500

        return send_range_from_file(tmp_mp4)

    # If stored in GridFS, for Range requests decrypt to temp file; otherwise stream decrypt on-the-fly
    gridfs_id = video.get('gridfs_id')
    if gridfs_id:
        try:
            bucket = GridFSBucket(db)
            grid_out = bucket.open_download_stream(ObjectId(gridfs_id))

            if range_header:
                # decrypt whole stream to temp file then serve range
                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tmpf.close()
                ok = decryption_mod.decrypt_stream_to_path(grid_out, tmpf.name, key)
                try:
                    grid_out.close()
                except Exception:
                    pass
                if not ok:
                    try:
                        os.remove(tmpf.name)
                    except Exception:
                        pass
                    return jsonify({"error": "Decryption failed"}), 500

                return send_range_from_file(tmpf.name)

            # No Range header: stream decrypted bytes on-the-fly
            def decrypted_gen():
                try:
                    for chunk in decryption_mod.decrypt_stream_generator(grid_out, key):
                        yield chunk
                finally:
                    try:
                        grid_out.close()
                    except Exception:
                        pass

            return Response(decrypted_gen(), mimetype='video/mp4', headers={'Accept-Ranges': 'bytes'})
        except Exception:
            return jsonify({"error": "Decryption failed"}), 500

    # Fallback: encrypted file on disk
    try:
        filename = video.get('filename')
        data_root = Path(__file__).resolve().parents[3] / 'data'
        encrypted_path = data_root / 'encrypted' / filename
        if encrypted_path.exists():
            fobj = open(encrypted_path, 'rb')

            if range_header:
                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tmpf.close()
                ok = decryption_mod.decrypt_stream_to_path(fobj, tmpf.name, key)
                try:
                    fobj.close()
                except Exception:
                    pass
                if not ok:
                    try:
                        os.remove(tmpf.name)
                    except Exception:
                        pass
                    return jsonify({"error": "Decryption failed"}), 500

                return send_range_from_file(tmpf.name)

            def decrypted_file_gen():
                try:
                    for chunk in decryption_mod.decrypt_stream_generator(fobj, key):
                        yield chunk
                finally:
                    try:
                        fobj.close()
                    except Exception:
                        pass

            return Response(decrypted_file_gen(), mimetype='video/mp4', headers={'Accept-Ranges': 'bytes'})
        else:
            return jsonify({"error": "Video data not found"}), 404
    except Exception:
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