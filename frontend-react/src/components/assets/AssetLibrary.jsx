import React, { useState, useCallback } from 'react';
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
  pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  approved: 'bg-green-500/20 text-green-400 border-green-500/30',
  rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
  draft: 'bg-white/10 text-white/60 border-white/20'
};

export function AssetLibrary({ businessId }) {
  const { get, post, loading } = useApi();
  const [assets, setAssets] = useState([]);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  // Mock data for demo - replace with API call
  const mockAssets = [
    {
      id: '1',
      name: 'TikTok Thumbnail - Productivity Tips',
      type: 'image',
      format: 'png',
      size: '2.4 MB',
      status: 'approved',
      agent: 'Pixel',
      createdAt: '2025-04-15',
      tags: ['thumbnail', 'tiktok', 'productivity'],
      previewUrl: null
    },
    {
      id: '2',
      name: 'YouTube Script - Week 1',
      type: 'document',
      format: 'md',
      size: '12 KB',
      status: 'pending',
      agent: 'Forge',
      createdAt: '2025-04-16',
      tags: ['script', 'youtube', 'draft'],
      previewUrl: null
    },
    {
      id: '3',
      name: 'Etsy Listing Mockup',
      type: 'image',
      format: 'jpg',
      size: '1.8 MB',
      status: 'draft',
      agent: 'Pixel',
      createdAt: '2025-04-14',
      tags: ['etsy', 'mockup', 'listing'],
      previewUrl: null
    },
    {
      id: '4',
      name: 'Product Video - 30sec',
      type: 'video',
      format: 'mp4',
      size: '45 MB',
      status: 'approved',
      agent: 'Merchant',
      createdAt: '2025-04-13',
      tags: ['video', 'product', 'short'],
      previewUrl: null
    }
  ];

  React.useEffect(() => {
    // TODO: Load from API
    setAssets(mockAssets);
  }, [businessId]);

  const handleFileDrop = useCallback((e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    handleUpload(files);
  }, []);

  const handleUpload = async (files) => {
    setIsUploading(true);
    // TODO: Implement actual upload
    await new Promise(r => setTimeout(r, 1000));
    setIsUploading(false);
    alert(`Upload ${files.length} files - implement S3/Cloudinary integration`);
  };

  const filteredAssets = assets.filter(asset => {
    const matchesFilter = filter === 'all' || asset.type === filter;
    const matchesSearch = asset.name.toLowerCase().includes(search.toLowerCase()) ||
                         asset.tags.some(t => t.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Asset Library</h3>
          <p className="text-white/50 text-sm">Manage designs, content, and media files</p>
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
          <AssetCard key={asset.id} asset={asset} />
        ))}
      </div>

      {/* Empty State */}
      {filteredAssets.length === 0 && (
        <div className="text-center py-12 bg-white/5 rounded-2xl">
          <div className="text-4xl mb-2">📂</div>
          <p className="text-white/50">No assets found</p>
          <p className="text-sm text-white/30 mt-1">
            Upload files or adjust your filters
          </p>
        </div>
      )}
    </div>
  );
}

function AssetCard({ asset }) {
  const [showActions, setShowActions] = useState(false);

  return (
    <div 
      className="group relative bg-white/5 rounded-xl border border-white/10 overflow-hidden hover:border-cyan-500/30 transition-all"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Preview */}
      <div className="aspect-video bg-gradient-to-br from-white/10 to-white/5 flex items-center justify-center">
        <span className="text-4xl">{TYPE_ICONS[asset.type] || TYPE_ICONS.default}</span>
      </div>

      {/* Info */}
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <h4 className="font-medium text-white text-sm line-clamp-2" title={asset.name}>
            {asset.name}
          </h4>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_COLORS[asset.status]}`}>
            {asset.status}
          </span>
          <span className="text-xs text-white/40">{asset.size}</span>
        </div>

        <div className="flex items-center gap-2 mt-2 text-xs text-white/50">
          <span>🤖 {asset.agent}</span>
          <span>•</span>
          <span>{asset.createdAt}</span>
        </div>

        {/* Tags */}
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
      </div>

      {/* Hover Actions */}
      {showActions && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center gap-2">
          <button 
            className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
            title="Preview"
          >
            👁️
          </button>
          <button 
            className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
            title="Download"
          >
            ⬇️
          </button>
          {asset.status === 'pending' && (
            <button 
              className="p-2 bg-green-500/20 rounded-lg hover:bg-green-500/30 transition-colors"
              title="Approve"
            >
              ✅
            </button>
          )}
        </div>
      )}
    </div>
  );
}
