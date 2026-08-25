import React, { useState, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, Trash2, Loader2, X, Plus } from 'lucide-react';
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
  const [customDishName, setCustomDishName] = useState('');
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

  const handleClearImage = (e) => {
    e.stopPropagation();
    setImagePreview(null);
    setDishes([]);
    setOcrError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAddCustomDish = (e) => {
    if (e) e.preventDefault();
    const trimmed = customDishName.trim();
    if (!trimmed) return;
    setDishes([...dishes, { name: trimmed, description: '', price: '', tags: [], section: 'Custom' }]);
    setCustomDishName('');
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
    <section className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-sm">
      {/* Section Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            Restaurant Menu Image Upload & Extracted Items Table
            {dishes.length > 0 && (
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-black tabular-nums">
                {dishes.length} items detected
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-500">
            Upload your menu image on the left. The OCR engine will process it and populate the extracted items table on the right.
          </p>
        </div>

        {/* Input Switcher (Segmented Control) */}
        <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] cursor-pointer ${
              activeTab === 'upload' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            📷 Image OCR
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] cursor-pointer ${
              activeTab === 'manual' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
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
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[300px] relative overflow-hidden group ${
                dragActive
                  ? 'border-emerald-500 bg-emerald-50/60 scale-[1.01]'
                  : 'border-slate-300 bg-slate-50/70 hover:border-emerald-500/60 hover:bg-slate-50'
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
                <div className="absolute inset-0 bg-white/90 backdrop-blur-xs z-20 flex flex-col items-center justify-center p-4">
                  <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mb-3" />
                  <span className="text-sm font-bold text-slate-900">Running Deep OCR Pipeline...</span>
                  <span className="text-xs text-slate-500 mt-1">Enhancing, deskewing & stripping noise</span>
                </div>
              )}

              {imagePreview ? (
                <div className="relative w-full flex flex-col items-center">
                  {/* Dedicated Close / Remove File Button */}
                  <button
                    type="button"
                    onClick={handleClearImage}
                    title="Remove menu image"
                    className="absolute -top-2 -right-2 z-30 p-1.5 rounded-full bg-slate-900/80 hover:bg-rose-600 text-white shadow-md transition-all active:scale-[0.96] cursor-pointer"
                  >
                    <X className="w-4 h-4 stroke-[2.5]" />
                  </button>

                  <img
                    src={imagePreview}
                    alt="Uploaded Menu"
                    className="max-h-56 rounded-xl object-contain shadow-sm border border-slate-200 ring-1 ring-slate-900/5"
                  />
                  <div className="mt-3 flex items-center gap-3">
                    <span className="text-xs text-slate-600 font-semibold group-hover:text-emerald-600">
                      Click to replace image
                    </span>
                    <button
                      type="button"
                      onClick={handleClearImage}
                      className="text-xs text-rose-600 hover:text-rose-700 font-bold underline cursor-pointer"
                    >
                      Clear File
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mb-3 shadow-xs">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 mb-1">Click or drag & drop menu photo</h3>
                  <p className="text-xs text-slate-500 mb-3">PNG, JPG, or JPEG image files</p>
                  <span className="px-4 py-1.5 rounded-xl bg-white text-xs font-bold text-emerald-700 border border-slate-300 shadow-xs">
                    Browse File
                  </span>
                </div>
              )}
            </div>

            {ocrError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                {ocrError}
              </div>
            )}
          </div>

          {/* Right Column: Extracted Items Table (7 cols) */}
          <div className="lg:col-span-7 bg-slate-50/70 rounded-2xl border border-slate-200 overflow-hidden flex flex-col min-h-[300px]">
            {/* Table Header */}
            <div className="px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Extracted Menu Items Table
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {dishes.length} {dishes.length === 1 ? 'item' : 'items'}
              </span>
            </div>

            {/* Quick Add Custom Item Bar */}
            <form onSubmit={handleAddCustomDish} className="p-2.5 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
              <input
                type="text"
                placeholder="Type item name to add (e.g. Garlic Naan)..."
                value={customDishName}
                onChange={(e) => setCustomDishName(e.target.value)}
                className="flex-1 bg-white border border-slate-300 rounded-xl px-3 py-1.5 text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              />
              <button
                type="submit"
                disabled={!customDishName.trim()}
                className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold text-xs shadow-xs transition-all active:scale-[0.96] flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" /> Add
              </button>
            </form>

            {/* Table Contents */}
            {dishes.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
                <ImageIcon className="w-10 h-10 mb-2 opacity-30" />
                <p className="text-xs font-medium text-slate-500">No menu dishes extracted yet.</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Upload a menu image on the left or add an item above.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto max-h-[320px] bg-white">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 text-slate-600 text-[11px] font-bold uppercase tracking-wider sticky top-0 border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4 w-12 text-center">#</th>
                      <th className="py-3 px-4">Food Item</th>
                      <th className="py-3 px-4 w-16 text-center">Delete</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {dishes.map((dish, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 transition-colors group">
                        <td className="py-3 px-4 text-slate-400 tabular-nums font-mono text-center font-bold">
                          {idx + 1}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-bold text-slate-900 text-sm">{dish.name}</span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => removeDish(idx)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-all active:scale-[0.96] cursor-pointer inline-flex items-center justify-center"
                            title="Delete item"
                          >
                            <Trash2 className="w-4 h-4" />
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
          <label className="block text-xs font-semibold text-slate-700">
            Paste dishes line by line (format: <code className="text-emerald-700 font-mono">Dish Name | Description | Price</code>):
          </label>
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            rows={5}
            className="w-full bg-slate-50 border border-slate-300 rounded-2xl p-3.5 text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30 font-mono"
          />
          <button
            onClick={handleParseManual}
            className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition-all active:scale-[0.96] cursor-pointer"
          >
            Load Manual Dishes into Table
          </button>
        </div>
      )}
    </section>
  );
}
