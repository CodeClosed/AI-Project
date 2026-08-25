import React, { useState, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, Sparkles, Plus, Trash2, Edit2, ArrowRight, Loader2 } from 'lucide-react';
import { uploadMenuImage } from '../api';

export default function Step1MenuUpload({ dishes, setDishes, onNext }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'manual'
  const [manualInput, setManualInput] = useState(
    'Steamed Edamame | Fresh steamed soybeans with sea salt | $5.99\nGrilled Lemon Chicken | Herb grilled chicken breast with roasted broccoli | $14.50\nPalak Paneer with Whole Wheat Roti | Fresh spinach puree with cottage cheese | $13.50\nCrispy Deep Fried Mozzarella Sticks | Breaded cheese sticks fried with marinara | $7.99'
  );
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file) => {
    setSelectedFile(file);
    setImagePreview(URL.createObjectURL(file));
    setError(null);
    setLoading(true);

    try {
      const data = await uploadMenuImage(file);
      if (data.dishes && data.dishes.length > 0) {
        setDishes(data.dishes);
      } else {
        setError('No food dishes could be detected. Try a higher contrast photo or use manual dish input.');
      }
    } catch (err) {
      setError(err.message || 'Failed to extract text from menu image.');
    } finally {
      setLoading(false);
    }
  };

  const handleParseManual = () => {
    const lines = manualInput.split('\n');
    const parsed = [];
    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      const parts = trimmed.split('|').map((p) => p.trim());
      if (parts[0]) {
        parsed.push({
          name: parts[0],
          description: parts[1] || '',
          price: parts[2] || '',
          tags: [],
          section: 'Manual Input',
        });
      }
    });
    setDishes(parsed);
  };

  const removeDish = (index) => {
    setDishes(dishes.filter((_, i) => i !== index));
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" /> Model 1: Visual Menu Intelligence
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-blue-400">
          Upload & Scan Restaurant Menu
        </h1>
        <p className="text-slate-400 text-sm sm:text-base mt-2 max-w-xl mx-auto">
          Drop any menu photo or scan. Deep learning OCR automatically extracts dish names, prices, categories, and strips ambient noise.
        </p>
      </div>

      {/* Mode Switcher */}
      <div className="flex justify-center mb-6">
        <div className="glass-panel p-1 rounded-xl flex gap-1 border border-slate-800">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'upload' ? 'bg-emerald-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'
            }`}
          >
            📷 Upload Menu Image
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'manual' ? 'bg-emerald-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'
            }`}
          >
            ✍️ Manual Dish Input
          </button>
        </div>
      </div>

      {activeTab === 'upload' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Upload Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`glass-panel border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[320px] ${
              dragActive
                ? 'border-emerald-400 bg-emerald-500/10 scale-[1.01]'
                : 'border-slate-700 hover:border-emerald-500/60 hover:bg-slate-800/40'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg"
              onChange={handleFileChange}
              className="hidden"
            />
            {imagePreview ? (
              <div className="relative group w-full flex flex-col items-center">
                <img
                  src={imagePreview}
                  alt="Menu preview"
                  className="max-h-56 rounded-2xl object-contain shadow-2xl border border-slate-700/60"
                />
                <span className="mt-3 text-xs text-slate-400 group-hover:text-emerald-400">
                  Click or drop another image to replace
                </span>
              </div>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <h3 className="text-base font-bold text-white mb-1">
                  Drag & drop menu image here
                </h3>
                <p className="text-xs text-slate-400 max-w-xs mb-3">
                  Supports high-res PNG, JPG, or JPEG photos and scans
                </p>
                <span className="px-4 py-1.5 rounded-full bg-slate-800 text-xs font-semibold text-emerald-400 border border-slate-700">
                  Browse Files
                </span>
              </>
            )}
          </div>

          {/* Extracted Dishes List Preview */}
          <div className="glass-panel rounded-3xl p-6 flex flex-col border border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                🍽️ Detected Menu Dishes
                {dishes.length > 0 && (
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                    {dishes.length}
                  </span>
                )}
              </h3>
              {loading && (
                <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                  <Loader2 className="w-4 h-4 animate-spin" /> OCR Processing...
                </span>
              )}
            </div>

            {error && (
              <div className="p-3 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {error}
              </div>
            )}

            {dishes.length === 0 && !loading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
                <ImageIcon className="w-10 h-10 mb-2 opacity-40" />
                <p className="text-xs">No dishes extracted yet. Upload a menu to see items here.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto max-h-[260px] space-y-2 pr-1">
                {dishes.map((dish, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between group hover:border-slate-700"
                  >
                    <div>
                      <div className="font-semibold text-sm text-slate-200">{dish.name}</div>
                      {dish.description && (
                        <div className="text-xs text-slate-400 truncate max-w-[220px]">
                          {dish.description}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {dish.price && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {dish.price}
                        </span>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeDish(idx);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Manual Input Mode */
        <div className="glass-panel rounded-3xl p-6 border border-slate-800">
          <label className="block text-sm font-bold text-white mb-2">
            Enter dishes (format: <code className="text-emerald-400 font-mono">Dish Name | Description | Price</code>):
          </label>
          <textarea
            value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            rows={6}
            className="w-full rounded-2xl glass-input p-4 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 border border-slate-700 font-mono mb-4"
          />
          <button
            onClick={handleParseManual}
            className="px-5 py-2.5 rounded-xl bg-emerald-500 text-white text-sm font-bold shadow-lg hover:bg-emerald-600 transition-all"
          >
            Load Manual Dishes ({manualInput.split('\n').filter((l) => l.trim()).length})
          </button>
        </div>
      )}

      {/* Action Footer */}
      <div className="mt-8 flex justify-end">
        <button
          onClick={onNext}
          disabled={dishes.length === 0}
          className={`flex items-center gap-2 px-8 py-3.5 rounded-2xl font-bold text-sm shadow-xl transition-all ${
            dishes.length > 0
              ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:scale-[1.02] shadow-glow-green cursor-pointer'
              : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
          }`}
        >
          Next: Health Profile & Matrix Studio <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
