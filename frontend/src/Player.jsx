// In Player.jsx - ADD useEffect to load all videos on mount

import React, { useRef, useState, useContext, useEffect } from "react";

function Player() {
  const videoRef = useRef(null);
  const { user, isAuthenticated } = useContext(AuthContext);

  const [videoUrl, setVideoUrl] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchStats, setSearchStats] = useState({ total: 0, filtered: 0 });
  const [query, setQuery] = useState({ date: '', start_time: '', end_time: '', camera_id: '', plate: '' });
  const [loading, setLoading] = useState(false);

  // Load all videos on mount
  useEffect(() => {
    if (isAuthenticated) {
      performSearch();
    }
  }, [isAuthenticated]);

  const performSearch = async (e) => {
    e && e.preventDefault();
    setLoading(true);
    
    const params = new URLSearchParams();
    Object.entries(query).forEach(([k, v]) => { if (v) params.append(k, v); });

    try {
      const res = await apiFetch('/search?' + params.toString());
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.message || err.error || 'Search failed');
        setSearchResults([]);
        return;
      }

      const data = await res.json();
      setSearchResults(data.results || []);
      setSearchStats({ total: data.total || 0, filtered: data.filtered || 0 });
    } catch (err) {
      alert('Network error');
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setQuery({ date: '', start_time: '', end_time: '', camera_id: '', plate: '' });
    setTimeout(() => performSearch(), 100);
  };

  // ... rest of the component remains same, just update the UI to show stats

  return (
    <div style={{ maxWidth: 1200, margin: '24px auto', fontFamily: 'system-ui, sans-serif' }}>
      <h2>Secure Video Viewer</h2>
      
      <div style={{ marginBottom: 16, color: '#666' }}>
        Showing {searchStats.filtered} of {searchStats.total} videos
      </div>

      <form onSubmit={performSearch} style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input 
          placeholder="Date (YYYY-MM-DD)" 
          value={query.date} 
          onChange={e => setQuery({...query, date: e.target.value})} 
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd' }}
        />
        <input 
          placeholder="Start (HH:MM:SS)" 
          value={query.start_time} 
          onChange={e => setQuery({...query, start_time: e.target.value})} 
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd' }}
        />
        <input 
          placeholder="End (HH:MM:SS)" 
          value={query.end_time} 
          onChange={e => setQuery({...query, end_time: e.target.value})} 
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd' }}
        />
        <input 
          placeholder="Camera ID" 
          value={query.camera_id} 
          onChange={e => setQuery({...query, camera_id: e.target.value})} 
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd' }}
        />
        <input 
          placeholder="Plate" 
          value={query.plate} 
          onChange={e => setQuery({...query, plate: e.target.value})} 
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd' }}
        />
        <button type="submit" disabled={loading} style={{ padding: '8px 16px', borderRadius: 6, border: 'none', background: '#2563eb', color: '#fff', cursor: 'pointer' }}>
          {loading ? 'Searching...' : 'Search'}
        </button>
        <button type="button" onClick={clearFilters} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #ddd', background: '#fff', cursor: 'pointer' }}>
          Clear
        </button>
      </form>

      {/* Rest remains the same */}
    </div>
  );
}