import React, { useState, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, Sparkles, Trash2, Loader2, FileText, CheckCircle2 } from 'lucide-react';
import { uploadMenuImage } from '../api';

export default function MenuUploadSection({
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
  const [manualText, setManualText] = useState(
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
    const lines = manualText.split('\n');
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
    <section className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl backdrop-blur-xl">
      {/* Section Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            2. Restaurant Menu Image Upload & Extracted Items Table
            {dishes.length > 0 && (
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-black tabular-nums">
                {dishes.length} items detected
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-400">
            Upload your menu image on the left. The OCR engine will process it and populate the extracted items table on the right.
          </p>
        </div>

        {/* Input Switcher */}
        <div className="inline-flex p-1 bg-slate-950/80 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] ${
              activeTab === 'upload' ? 'bg-emerald-500 text-slate-950 shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            📷 Image OCR
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
        /* Side-by-Side 50/50 Grid */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Image Upload & Preview (5 cols) */}
          <div className="lg:col-span-5 flex flex-col space-y-3">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[300px] relative overflow-hidden ${
                dragActive
                  ? 'border-emerald-400 bg-emerald-500/10 scale-[1.01]'
                  : 'border-slate-700/80 bg-slate-950/60 hover:border-emerald-500/60 hover:bg-slate-950/80'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg"
                onChange={handleFileChange}
                className="hidden"
              />

              {ocrLoading && (
                <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center p-4">
                  <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mb-3" />
                  <span className="text-sm font-bold text-white">Running Deep OCR Pipeline...</span>
                  <span className="text-xs text-slate-400 mt-1">Enhancing, deskewing & stripping noise</span>
                </div>
              )}

              {imagePreview ? (
                <div className="w-full flex flex-col items-center">
                  <img
                    src={imagePreview}
                    alt="Uploaded Menu"
                    className="max-h-56 rounded-xl object-contain shadow-lg border border-slate-700/60 ring-1 ring-white/10"
                  />
                  <span className="mt-3 text-xs text-slate-400 font-semibold hover:text-emerald-400">
                    Click to replace with another image
                  </span>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <h3 className="text-sm font-bold text-white mb-1">Click or drag & drop menu photo</h3>
                  <p className="text-xs text-slate-400 mb-3">PNG, JPG, or JPEG image files</p>
                  <span className="px-4 py-1.5 rounded-xl bg-slate-800 text-xs font-bold text-emerald-400 border border-slate-700">
                    Browse File
                  </span>
                </div>
              )}
            </div>

            {ocrError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {ocrError}
              </div>
            )}
          </div>

          {/* Right Column: Extracted Items Table (7 cols) */}
          <div className="lg:col-span-7 bg-slate-950/80 rounded-2xl border border-slate-800 overflow-hidden flex flex-col min-h-[300px]">
            {/* Table Header */}
            <div className="px-4 py-3 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Extracted Menu Items Table
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {dishes.length} {dishes.length === 1 ? 'item' : 'items'}
              </span>
            </div>

            {/* Table Contents */}
            {dishes.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
                <ImageIcon className="w-10 h-10 mb-2 opacity-30" />
                <p className="text-xs font-medium">No menu dishes extracted yet.</p>
                <p className="text-[11px] text-slate-600 mt-0.5">Upload a menu image on the left to populate this table.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto max-h-[320px]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-900/60 text-slate-400 text-[11px] font-bold uppercase tracking-wider sticky top-0">
                    <tr>
                      <th className="py-2.5 px-3 w-10">#</th>
                      <th className="py-2.5 px-3">Dish Name</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3 text-right">Price</th>
                      <th className="py-2.5 px-3 w-10 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {dishes.map((dish, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40 transition-colors group">
                        <td className="py-2.5 px-3 text-slate-500 tabular-nums font-mono">{idx + 1}</td>
                        <td className="py-2.5 px-3">
                          <div className="font-bold text-white">{dish.name}</div>
                          {dish.description && (
                            <div className="text-[11px] text-slate-400 truncate max-w-[220px]">{dish.description}</div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 text-[11px]">{dish.section || 'Main'}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-emerald-400 tabular-nums">
                          {dish.price || '-'}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            onClick={() => removeDish(idx)}
                            className="p-1 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all active:scale-[0.96]"
                            title="Remove dish"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Manual Input Mode */
        <div className="space-y-3">
          <label className="block text-xs font-semibold text-slate-400">
            Paste dishes line by line (format: <code className="text-emerald-400 font-mono">Dish Name | Description | Price</code>):
          </label>
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            rows={5}
            className="w-full bg-slate-950/80 border border-slate-700/80 rounded-2xl p-3.5 text-xs text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40 font-mono"
          />
          <button
            onClick={handleParseManual}
            className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs shadow-md transition-all active:scale-[0.96]"
          >
            Load Manual Dishes into Table
          </button>
        </div>
      )}
    </section>
  );
}
