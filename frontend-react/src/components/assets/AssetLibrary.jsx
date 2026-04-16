import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '../shared/Button';
import { useApi } from '../../hooks/useApi';

const FILE_TYPES = {
  image: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
  video: ['.mp4', '.mov', '.avi', '.webm'],
  document: ['.pdf', '.doc', '.docx', '.txt', '.md'],
  design: ['.fig', '.sketch', '.psd', '.ai']
};

const TYPE_ICONS = {
  image: '🖼️',
  video: '🎬',
  document: '📄',
  design: '🎨',
  default: '📦'
};

const STATUS_COLORS = {
  pending_review: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  approved: 'bg-green-500/20 text-green-400 border-green-500/30',
  rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
  archived: 'bg-white/10 text-white/60 border-white/20'
};

export function AssetLibrary({ businessId }) {
  const { get, post, del, patch, loading } = useApi();
  const [assets, setAssets] = useState([]);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  // Load assets from API
  const loadAssets = useCallback(async () => {
    if (!businessId) return;
    
    const response = await get(`/files/business/${businessId}`, {
      params: { 
        asset_type: filter === 'all' ? undefined : filter,
        search: search || undefined,
        limit: 100
      }
    });
    
    if (response?.assets) {
      setAssets(response.assets);
    }
  }, [businessId, filter, search, get]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const handleFileDrop = useCallback((e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    handleUpload(files);
  }, []);

  const handleUpload = async (files) => {
    if (!files.length || !businessId) return;
    
    setIsUploading(true);
    
    for (const file of files) {
      const fileId = Math.random().toString(36).substring(7);
      setUploadProgress(prev => ({ ...prev, [fileId]: 0 }));
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('business_id', businessId);
      formData.append('asset_type', getAssetType(file.name));
      formData.append('description', '');
      
      try {
        // Simulate progress
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: Math.min((prev[fileId] || 0) + 10, 90)
          }));
        }, 200);
        
        const response = await post('/files/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        clearInterval(progressInterval);
        setUploadProgress(prev => ({ ...prev, [fileId]: 100 }));
        
        if (response) {
          // Add new asset to list
          setAssets(prev => [response, ...prev]);
        }
      } catch (err) {
        console.error('Upload failed:', err);
        alert(`Failed to upload ${file.name}`);
      }
      
      // Remove from progress after delay
      setTimeout(() => {
        setUploadProgress(prev => {
          const { [fileId]: _, ...rest } = prev;
          return rest;
        });
      }, 1000);
    }
    
    setIsUploading(false);
    loadAssets(); // Refresh to get server state
  };

  const handleApprove = async (assetId) => {
    try {
      await post(`/files/${assetId}/approve`);
      setAssets(prev => prev.map(a => 
        a.id === assetId ? { ...a, status: 'approved' } : a
      ));
    } catch (err) {
      console.error('Approval failed:', err);
    }
  };

  const handleDelete = async (assetId) => {
    if (!confirm('Delete this asset?')) return;
    
    try {
      await del(`/files/${assetId}`);
      setAssets(prev => prev.filter(a => a.id !== assetId));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleUpdateTags = async (assetId, tags) => {
    try {
      await patch(`/files/${assetId}`, { tags });
      setAssets(prev => prev.map(a => 
        a.id === assetId ? { ...a, tags } : a
      ));
    } catch (err) {
      console.error('Update failed:', err);
    }
  };

  // Filter assets locally for search
  const filteredAssets = assets.filter(asset => {
    const matchesFilter = filter === 'all' || asset.type === filter;
    const matchesSearch = !search || 
      asset.filename?.toLowerCase().includes(search.toLowerCase()) ||
      asset.tags?.some(t => t.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  // Active uploads
  const activeUploads = Object.entries(uploadProgress);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Asset Library</h3>
          <p className="text-white/50 text-sm">
            {assets.length} assets • {assets.filter(a => a.status === 'approved').length} approved
          </p>
        </div>
        <Button onClick={() => document.getElementById('file-upload').click()}>
          <span>⬆️</span> Upload Asset
        </Button>
        <input
          id="file-upload"
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleUpload(Array.from(e.target.files))}
        />
      </div>

      {/* Upload Progress */}
      {activeUploads.length > 0 && (
        <div className="space-y-2 p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-white/70">Uploading...</p>
          {activeUploads.map(([id, progress]) => (
            <div key={id} className="space-y-1">
              <div className="flex justify-between text-xs text-white/50">
                <span>File {id.slice(0, 6)}</span>
                <span>{progress}%</span>
              </div>
              <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-cyan-500 transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex gap-2">
          {['all', 'image', 'video', 'document'].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === type
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              {TYPE_ICONS[type]} {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search assets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        className="p-8 border-2 border-dashed border-white/10 rounded-2xl text-center hover:border-cyan-500/30 transition-colors"
      >
        <div className="text-4xl mb-2">📁</div>
        <p className="text-white/60">Drag and drop files here</p>
        <p className="text-sm text-white/40">or click Upload Asset</p>
      </div>

      {/* Asset Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {filteredAssets.map((asset) => (
          <AssetCard 
            key={asset.id} 
            asset={asset}
            onApprove={handleApprove}
            onDelete={handleDelete}
          />
        ))}
      </div>

      {/* Empty State */}
      {filteredAssets.length === 0 && !loading && (
        <div className="text-center py-12 bg-white/5 rounded-2xl">
          <div className="text-4xl mb-2">📂</div>
          <p className="text-white/50">No assets found</p>
          <p className="text-sm text-white/30 mt-1">
            Upload files or adjust your filters
          </p>
        </div>
      )}

      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-white/50">Loading assets...</p>
        </div>
      )}
    </div>
  );
}

function getAssetType(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  for (const [type, exts] of Object.entries(FILE_TYPES)) {
    if (exts.includes(`.${ext}`)) return type;
  }
  return 'document';
}

function AssetCard({ asset, onApprove, onDelete }) {
  const [showActions, setShowActions] = useState(false);
  
  const type = getAssetType(asset.filename || '');
  const status = asset.status || 'pending_review';
  
  // Format file size
  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div 
      className="group relative bg-white/5 rounded-xl border border-white/10 overflow-hidden hover:border-cyan-500/30 transition-all"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Preview */}
      <div className="aspect-video bg-gradient-to-br from-white/10 to-white/5 flex items-center justify-center relative">
        {asset.thumbnail_url ? (
          <img 
            src={asset.thumbnail_url} 
            alt={asset.filename}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-4xl">{TYPE_ICONS[type] || TYPE_ICONS.default}</span>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <h4 className="font-medium text-white text-sm line-clamp-2" title={asset.filename}>
            {asset.filename}
          </h4>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_COLORS[status]}`}>
            {status.replace('_', ' ')}
          </span>
          <span className="text-xs text-white/40">{formatSize(asset.size)}</span>
        </div>

        <div className="flex items-center gap-2 mt-2 text-xs text-white/50">
          <span>{new Date(asset.created_at).toLocaleDateString()}</span>
        </div>

        {/* Tags */}
        {asset.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {asset.tags.slice(0, 2).map((tag, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 bg-white/5 rounded text-white/40">
                #{tag}
              </span>
            ))}
            {asset.tags.length > 2 && (
              <span className="text-xs px-1.5 py-0.5 text-white/30">
                +{asset.tags.length - 2}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Hover Actions */}
      {showActions && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center gap-2">
          <a 
            href={asset.url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
            title="View"
          >
            👁️
          </a>
          <a 
            href={asset.url}
            download
            className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
            title="Download"
          >
            ⬇️
          </a>
          {status === 'pending_review' && (
            <button 
              onClick={() => onApprove(asset.id)}
              className="p-2 bg-green-500/20 rounded-lg hover:bg-green-500/30 transition-colors"
              title="Approve"
            >
              ✅
            </button>
          )}
          <button 
            onClick={() => onDelete(asset.id)}
            className="p-2 bg-red-500/20 rounded-lg hover:bg-red-500/30 transition-colors"
            title="Delete"
          >
            🗑️
          </button>
        </div>
      )}
    </div>
  );
}
