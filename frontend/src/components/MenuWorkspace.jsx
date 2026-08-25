import React, { useState, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, Sparkles, Plus, Trash2, Edit2, Loader2, RefreshCw } from 'lucide-react';
import { uploadMenuImage } from '../api';

export default function MenuWorkspace({
  dishes,
  setDishes,
  ocrLoading,
  setOcrLoading,
  ocrError,
  setOcrError,
  imagePreview,
  setImagePreview,
}) {
  const [dragActive, setDragActive] = useState(false);
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
    setImagePreview(URL.createObjectURL(file));
    setOcrError(null);
    setOcrLoading(true);

    try {
      const data = await uploadMenuImage(file);
      if (data.dishes && data.dishes.length > 0) {
        setDishes(data.dishes);
      } else {
        setOcrError('No food dishes detected. Try another photo or enter items manually.');
      }
    } catch (err) {
      setOcrError(err.message || 'Failed to extract menu text.');
    } finally {
      setOcrLoading(false);
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
    <div className="glass-panel rounded-[24px] p-6 border border-slate-800 shadow-2xl mb-8">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <span>📸 Menu Input & OCR Scanner</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Upload menu images or type dishes. Recommendations match against your account profile automatically.
          </p>
        </div>

        {/* Input Mode Selector (Apple HIG Segmented Control) */}
        <div className="inline-flex p-1 bg-slate-900/80 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] ${
              activeTab === 'upload' ? 'bg-emerald-500 text-slate-950 shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            📷 Photo Upload
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] ${
              activeTab === 'manual' ? 'bg-emerald-500 text-slate-950 shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            ✍️ Manual Text
          </button>
        </div>
      </div>

      {activeTab === 'upload' ? (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Dropzone (5 cols) */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`md:col-span-5 border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[220px] ${
              dragActive
                ? 'border-emerald-400 bg-emerald-500/10 scale-[1.01]'
                : 'border-slate-700/80 bg-slate-900/40 hover:border-emerald-500/60 hover:bg-slate-900/70'
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
                  alt="Menu thumbnail"
                  className="max-h-40 rounded-xl object-contain shadow-md border border-slate-700/60 ring-1 ring-white/10"
                />
                <span className="mt-2.5 text-[11px] text-slate-400 group-hover:text-emerald-400 font-semibold">
                  Click to choose a different menu photo
                </span>
              </div>
            ) : (
              <>
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-white mb-0.5">Drag & drop menu image</h3>
                <p className="text-[11px] text-slate-400 mb-2.5">PNG, JPG or JPEG supported</p>
                <span className="px-3 py-1 rounded-lg bg-slate-800 text-[11px] font-bold text-emerald-400 border border-slate-700">
                  Browse Photo
                </span>
              </>
            )}
          </div>

          {/* Detected Dishes Preview (7 cols) */}
          <div className="md:col-span-7 bg-slate-900/50 rounded-2xl p-4 border border-slate-800/80 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                🍽️ Detected Menu Items
                {dishes.length > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[11px] font-extrabold tabular-nums">
                    {dishes.length}
                  </span>
                )}
              </span>
              {ocrLoading && (
                <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Deep OCR Extraction...
                </span>
              )}
            </div>

            {ocrError && (
              <div className="p-2.5 mb-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {ocrError}
              </div>
            )}

            {dishes.length === 0 && !ocrLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
                <ImageIcon className="w-8 h-8 mb-1.5 opacity-30" />
                <p className="text-xs">Upload a menu image above to extract dishes automatically.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto max-h-[170px] space-y-1.5 pr-1">
                {dishes.map((dish, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between group hover:border-slate-700 transition-colors"
                  >
                    <div className="min-w-0 pr-2">
                      <div className="font-semibold text-xs text-slate-200 truncate">{dish.name}</div>
                      {dish.description && (
                        <div className="text-[11px] text-slate-400 truncate max-w-[280px]">
                          {dish.description}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {dish.price && (
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 tabular-nums">
                          {dish.price}
                        </span>
                      )}
                      <button
                        onClick={() => removeDish(idx)}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all active:scale-[0.96]"
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
        /* Manual Dishes */
        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1.5">
            Type dishes line by line (format: <code className="text-emerald-400 font-mono">Dish Name | Description | Price</code>):
          </label>
          <textarea
            value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            rows={4}
            className="w-full glass-input rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 border border-slate-700 font-mono mb-3"
          />
          <button
            onClick={handleParseManual}
            className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs shadow-md transition-all active:scale-[0.96]"
          >
            Load Manual Items
          </button>
        </div>
      )}
    </div>
  );
}
