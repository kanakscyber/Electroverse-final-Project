import React, { useRef, useState, useContext } from "react";
import AuthContext from './AuthContext.jsx';
import apiFetch from './api';

function Player() {
  const videoRef = useRef(null);
  const { user, isAuthenticated } = useContext(AuthContext);

  const [videoUrl, setVideoUrl] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [query, setQuery] = useState({ date: '', start_time: '', end_time: '', camera_id: '', plate: '' });

  const performSearch = async (e) => {
    e && e.preventDefault();
    const params = new URLSearchParams();
    Object.entries(query).forEach(([k, v]) => { if (v) params.append(k, v); });

    try {
      const res = await apiFetch('/search?' + params.toString());
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.message || err.error || 'Search failed');
        return;
      }

      const data = await res.json();
      setSearchResults(Array.isArray(data) ? data : []);
    } catch (err) {
      alert('Network error');
    }
  };

  const loadVideo = async (video_id) => {
    // Use the server-decrypted endpoint as the video src so the browser can
    // perform range requests and enable seeking. Browser will include cookies
    // for same-origin requests; include crossOrigin for credentialed requests.
    setVideoUrl(`/video/${video_id}`);
    setTimeout(() => videoRef.current && videoRef.current.play(), 100);
  };

  if (!isAuthenticated) {
    return <div style={{ textAlign: 'center', marginTop: 40 }}>Please sign in to view videos.</div>;
  }

  return (
    <div style={{ maxWidth: 900, margin: '24px auto', fontFamily: 'Arial, sans-serif' }}>
      <h2>Secure Video Viewer</h2>

      <form onSubmit={performSearch} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input placeholder="Date (YYYY-MM-DD)" value={query.date} onChange={e => setQuery({...query, date: e.target.value})} />
        <input placeholder="Start (HH:MM:SS)" value={query.start_time} onChange={e => setQuery({...query, start_time: e.target.value})} />
        <input placeholder="End (HH:MM:SS)" value={query.end_time} onChange={e => setQuery({...query, end_time: e.target.value})} />
        <input placeholder="Camera ID" value={query.camera_id} onChange={e => setQuery({...query, camera_id: e.target.value})} />
        <input placeholder="Plate" value={query.plate} onChange={e => setQuery({...query, plate: e.target.value})} />
        <button type="submit">Search</button>
      </form>

      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <h4>Results</h4>
          {searchResults.length === 0 && <div>No results</div>}
          <ul>
            {searchResults.map(r => (
              <li key={r.video_id} style={{ marginBottom: 8 }}>
                <strong>{r.filename}</strong> — {r.upload_date_ist} — {r.camera_id}
                <div>
                  <button onClick={() => loadVideo(r.video_id)} style={{ marginTop: 6 }}>Load</button>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ flex: 1 }}>
          <h4>Player</h4>
          {videoUrl ? (
            <video ref={videoRef} src={videoUrl} controls style={{ width: '100%' }} crossOrigin="use-credentials" />
          ) : (
            <div style={{ padding: 20, border: '1px dashed #ccc' }}>No video loaded</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Player;