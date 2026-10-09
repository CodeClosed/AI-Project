import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  Image as ImageIcon,
  Trash2,
  Loader2,
  X,
  Plus,
  Sparkles,
  Bookmark,
  Calendar,
  CheckCircle2,
  FileText,
  RotateCcw,
} from 'lucide-react';
import { uploadMenuImage, startMenuScanJob, pollMenuScanJob, API_BASE_URL } from '../api';
import { useNutrition } from '../context/NutritionContext';

export const DEMO_MENUS = {
  bistro: {
    name: 'Mediterranean Healthy Bistro',
    items: [
      { name: 'Steamed Edamame with Sea Salt', description: 'Fresh steamed young soybeans with light sea salt', price: '$6.50', tags: ['vegan', 'low-sodium'], calories: 190, protein: 17, carbs: 14, fat: 8, sodium: 180, section: 'Starters' },
      { name: 'Grilled Lemon Herb Salmon', description: 'Atlantic salmon fillet with roasted asparagus and wild rice', price: '$21.90', tags: ['omega-3', 'heart-healthy'], calories: 520, protein: 46, carbs: 32, fat: 22, sodium: 480, section: 'Mains' },
      { name: 'Quinoa Mediterranean Power Bowl', description: 'Tri-color quinoa, cherry tomatoes, cucumbers, olives, and lemon tahini', price: '$14.50', tags: ['vegetarian', 'high-fiber'], calories: 430, protein: 14, carbs: 58, fat: 16, sodium: 390, section: 'Bowls' },
      { name: 'Crispy Fried Mozzarella Sticks', description: 'Deep-fried breaded whole-milk mozzarella with seasoned marinara', price: '$8.90', tags: ['dairy', 'deep-fried'], calories: 680, protein: 24, carbs: 48, fat: 42, sodium: 1250, section: 'Appetizers' },
      { name: 'Creamy Fettuccine Alfredo with Bacon', description: 'Fettuccine pasta in heavy cream butter sauce with smoked bacon and parmesan', price: '$18.50', tags: ['dairy', 'high-saturated-fat'], calories: 980, protein: 32, carbs: 86, fat: 58, sodium: 1680, section: 'Pastas' },
      { name: 'House Garden Green Salad', description: 'Mixed crisp greens, shaved carrots, radish, and extra virgin olive oil vinaigrette', price: '$7.50', tags: ['low-carb', 'heart-healthy'], calories: 160, protein: 3, carbs: 12, fat: 12, sodium: 140, section: 'Salads' },
      { name: 'Thai Peanut Chicken Satay', description: 'Skewered marinated chicken breast with thick spicy peanut sauce', price: '$12.00', tags: ['peanuts'], calories: 480, protein: 38, carbs: 18, fat: 28, sodium: 820, section: 'Starters' },
      { name: 'Unsweetened Iced Green Tea', description: 'Brewed organic Japanese sencha green tea with fresh mint leaf', price: '$3.50', tags: ['zero-calorie', 'antioxidant'], calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 10, section: 'Beverages' },
    ],
  },
  trattoria: {
    name: 'Classic Italian Trattoria',
    items: [
      { name: 'Minestrone Verdure Soup', description: 'Slow-simmered vegetable broth with cannellini beans, zucchini, and tomatoes', price: '$7.50', tags: ['vegan', 'high-fiber'], calories: 180, protein: 8, carbs: 32, fat: 3, sodium: 440, section: 'Zuppe' },
      { name: 'Grilled Chicken Paillard', description: 'Thinly pounded chicken breast with wild baby arugula, cherry tomatoes, and shaved parmesan', price: '$19.00', tags: ['high-protein', 'low-carb'], calories: 410, protein: 52, carbs: 6, fat: 20, sodium: 520, section: 'Secondi' },
      { name: 'Spaghetti Carbonara', description: 'Spaghetti with cured pork guanciale, pecorino romano, egg yolks, and black pepper', price: '$17.50', tags: ['high-fat', 'dairy'], calories: 840, protein: 34, carbs: 78, fat: 44, sodium: 1420, section: 'Primi' },
      { name: 'Caprese Salad with Basil Pesto', description: 'Buffalo mozzarella, heirloom tomatoes, fresh basil, and pine nut pesto', price: '$11.50', tags: ['dairy', 'tree-nuts'], calories: 380, protein: 18, carbs: 10, fat: 30, sodium: 490, section: 'Antipasti' },
      { name: 'Deep-Fried Calamari Fritti', description: 'Tender calamari tossed in spiced semolina, deep fried with garlic aioli', price: '$13.00', tags: ['shellfish', 'deep-fried'], calories: 620, protein: 28, carbs: 45, fat: 36, sodium: 1100, section: 'Antipasti' },
      { name: 'Sparkling Mineral Water', description: 'San Pellegrino sparkling water with fresh organic lemon slice', price: '$3.00', tags: ['zero-calorie'], calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 5, section: 'Bevande' },
    ],
  },
};

export default function MenuUploadSection({
  profile,
  dishes,
  setDishes,
  ocrLoading,
  setOcrLoading,
  ocrError,
  setOcrError,
  imagePreview,
  setImagePreview,
}) {
  const {
    savedMenus,
    setSavedMenus,
    handleLoadSavedMenu,
    handleDeleteSavedMenu,
    handleSaveCurrentMenu,
    setEvalResult,
  } = useNutrition();

  const [dragActive, setDragActive] = useState(false);
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'manual' | 'history'
  const [customDishName, setCustomDishName] = useState('');
  const [activeJob, setActiveJob] = useState(null);
  const [menuSaveSuccess, setMenuSaveSuccess] = useState(false);
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
    // Immediate local blob preview while OCR executes
    setImagePreview(URL.createObjectURL(file));
    setOcrError(null);
    setOcrLoading(true);
    setActiveJob({
      progress: 15,
      stage: 'Uploading & validating menu image...',
      stages: [
        { id: 'init', label: 'Validating & storing menu image', status: 'active' },
        { id: 'ocr', label: 'Vision OCR & dish extraction', status: 'pending' },
        { id: 'matrix', label: 'Clinical health matrix synthesis', status: 'pending' },
        { id: 'recommend', label: '3-tier safety scoring & plate optimization', status: 'pending' },
      ],
    });

    try {
      // 1. Try non-blocking background job first
      let data = null;
      try {
        const jobInit = await startMenuScanJob(file, profile, profile?.api_key);
        data = await pollMenuScanJob(jobInit.job_id, (jobUpdate) => {
          setActiveJob(jobUpdate);
        });
      } catch (jobErr) {
        console.warn('Background job fallback to direct upload:', jobErr);
        data = await uploadMenuImage(file, profile?.api_key);
      }

      if (data && data.dishes && data.dishes.length > 0) {
        setDishes(data.dishes);

        if (data.recommendations) {
          setEvalResult(data.recommendations);
        }

        // Update preview to the persistent local URL served by FastAPI
        if (data.image_url) {
          const persistentUrl = data.image_url.startsWith('http')
            ? data.image_url
            : `${API_BASE_URL}${data.image_url}`;
          setImagePreview(persistentUrl);
        }

        // Register to saved menu scan history
        const cleanTitle = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        const newSaved = {
          id: data.saved_menu_id || `menu_${Date.now()}`,
          title: `Menu - ${cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1)}`,
          dishes: data.dishes,
          image_url: data.image_url,
          filename: file.name,
          created_at: new Date().toISOString(),
        };
        setSavedMenus((prev) => [newSaved, ...prev.filter((m) => m.id !== newSaved.id)]);
      } else {
        setOcrError('No food dishes detected. Try another photo or enter items manually.');
      }
    } catch (err) {
      setOcrError(err.message || 'Failed to extract menu text.');
    } finally {
      setOcrLoading(false);
      setTimeout(() => setActiveJob(null), 1200);
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

  const onSaveCurrentMenu = async () => {
    await handleSaveCurrentMenu();
    setMenuSaveSuccess(true);
    setTimeout(() => setMenuSaveSuccess(false), 2500);
  };

  const onLoadMenu = (menu) => {
    handleLoadSavedMenu(menu);
    setActiveTab('upload');
  };

  const handleLoadDemoMenu = (key) => {
    const demo = DEMO_MENUS[key];
    if (!demo) return;
    setDishes(demo.items);
    setImagePreview(null);
    setOcrError(null);
    setEvalResult(null);
  };

  return (
    <section className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm transition-colors">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            Restaurant Menu Scanner & Scan History
            {dishes.length > 0 && (
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-black tabular-nums">
                {dishes.length} items active
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mt-0.5">
            <span>Upload a photo, paste text, or load past scanned menus from your local storage.</span>
          </p>
        </div>

        {/* Input Switcher (Segmented Control) */}
        <div className="inline-flex p-1 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-2xs">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] cursor-pointer ${
              activeTab === 'upload'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            📷 Image OCR
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] cursor-pointer ${
              activeTab === 'manual'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            ✍️ Manual Text
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'history'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Bookmark className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>Past Scans</span>
            {savedMenus.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-[10px] font-black">
                {savedMenus.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {activeTab === 'upload' && (
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
                  ? 'border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/30 scale-[1.01]'
                  : 'border-slate-300 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/40 hover:border-emerald-500/60 hover:bg-slate-50 dark:hover:bg-slate-800/70'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />

              {ocrLoading && (
                <div className="absolute inset-0 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md z-20 flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-200">
                  <div className="relative mb-2">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shadow-xs">
                      <Sparkles className="w-6 h-6 animate-pulse" />
                    </div>
                  </div>

                  <span className="text-sm font-bold text-slate-900 dark:text-white mt-1">
                    {activeJob?.stage || 'Analyzing Menu Photo...'}
                  </span>

                  {/* Progress percentage bar */}
                  <div className="w-full max-w-xs mt-3 mb-1">
                    <div className="flex justify-between items-center text-[11px] font-bold text-slate-500 dark:text-slate-400 mb-1">
                      <span>Progress</span>
                      <span className="text-emerald-700 dark:text-emerald-400 font-mono">{activeJob?.progress || 25}%</span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-200 dark:border-slate-700">
                      <div
                        className="bg-gradient-to-r from-emerald-600 to-teal-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${activeJob?.progress || 25}%` }}
                      />
                    </div>
                  </div>

                  {/* Observable Stage Checklist */}
                  <div className="space-y-1.5 w-full max-w-xs text-left text-[11px] pt-3 border-t border-slate-100 dark:border-slate-800 mt-2">
                    {(activeJob?.stages || [
                      { id: 'init', label: 'Validating & storing menu image', status: 'completed' },
                      { id: 'ocr', label: 'Vision OCR & dish extraction', status: 'active' },
                      { id: 'matrix', label: 'Clinical health matrix synthesis', status: 'pending' },
                      { id: 'recommend', label: '3-tier safety scoring & plate optimization', status: 'pending' },
                    ]).map((s) => (
                      <div key={s.id} className="flex items-center gap-2">
                        {s.status === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />}
                        {s.status === 'active' && <Loader2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 animate-spin shrink-0" />}
                        {s.status === 'pending' && <div className="w-3.5 h-3.5 rounded-full border border-slate-300 dark:border-slate-700 shrink-0" />}
                        <span
                          className={`truncate ${
                            s.status === 'active'
                              ? 'font-bold text-slate-900 dark:text-white'
                              : s.status === 'completed'
                              ? 'text-slate-600 dark:text-slate-300 font-medium'
                              : 'text-slate-400 dark:text-slate-600'
                          }`}
                        >
                          {s.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {imagePreview ? (
                <div className="relative w-full flex flex-col items-center">
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
                    className="max-h-56 rounded-xl object-contain shadow-sm border border-slate-200 dark:border-slate-700 ring-1 ring-slate-900/5"
                  />
                  <div className="mt-3 flex items-center gap-3">
                    <span className="text-xs text-slate-600 dark:text-slate-400 font-semibold group-hover:text-emerald-600">
                      Click to replace photo
                    </span>
                    <button
                      type="button"
                      onClick={handleClearImage}
                      className="text-xs text-rose-600 dark:text-rose-400 hover:text-rose-700 font-bold underline cursor-pointer"
                    >
                      Clear File
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3 shadow-xs">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Click or drag & drop menu photo</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">PNG, JPG, or JPEG image files</p>
                  <span className="px-4 py-1.5 rounded-xl bg-white dark:bg-slate-800 text-xs font-bold text-emerald-700 dark:text-emerald-300 border border-slate-300 dark:border-slate-700 shadow-xs mb-2">
                    Browse File
                  </span>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-emerald-500" /> Stored locally in /uploads/
                  </span>
                </div>
              )}
            </div>

            {/* Quick Demo Menus for Instant Viva / Testing */}
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-700/80 space-y-2">
              <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                <span>Instant Demo Presets (1-Click Test):</span>
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleLoadDemoMenu('bistro')}
                  className="py-1.5 px-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 text-slate-700 dark:text-slate-200 hover:text-emerald-700 dark:hover:text-emerald-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center justify-between transition cursor-pointer shadow-2xs"
                >
                  <span>🥗 Healthy Bistro</span>
                  <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">8 items →</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleLoadDemoMenu('trattoria')}
                  className="py-1.5 px-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 text-slate-700 dark:text-slate-200 hover:text-emerald-700 dark:hover:text-emerald-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center justify-between transition cursor-pointer shadow-2xs"
                >
                  <span>🍝 Italian Trattoria</span>
                  <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">6 items →</span>
                </button>
              </div>
            </div>

            {ocrError && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs font-medium">
                {ocrError}
              </div>
            )}
          </div>

          {/* Right Column: Extracted Items Table (7 cols) */}
          <div className="lg:col-span-7 bg-slate-50/70 dark:bg-slate-800/40 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col min-h-[300px]">
            {/* Table Header */}
            <div className="px-4 py-3 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                Extracted Menu Items Table
              </span>
              <div className="flex items-center gap-2">
                {dishes.length > 0 && (
                  <button
                    onClick={onSaveCurrentMenu}
                    className="px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-bold transition flex items-center gap-1 cursor-pointer"
                  >
                    {menuSaveSuccess ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span>Saved!</span>
                      </>
                    ) : (
                      <>
                        <Bookmark className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span>Save to Past Scans</span>
                      </>
                    )}
                  </button>
                )}
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  {dishes.length} {dishes.length === 1 ? 'item' : 'items'}
                </span>
              </div>
            </div>

            {/* Quick Add Custom Item Bar */}
            <form onSubmit={handleAddCustomDish} className="p-2.5 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
              <input
                type="text"
                placeholder="Type item name to add (e.g. Garlic Naan)..."
                value={customDishName}
                onChange={(e) => setCustomDishName(e.target.value)}
                className="flex-1 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
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
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400 dark:text-slate-500">
                <ImageIcon className="w-10 h-10 mb-2 opacity-30" />
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400">No menu dishes extracted yet.</p>
                <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">Upload a menu image on the left or load a past scan.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto max-h-[320px] bg-white dark:bg-slate-900">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[11px] font-bold uppercase tracking-wider sticky top-0 border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="py-3 px-4 w-12 text-center">#</th>
                      <th className="py-3 px-4">Food Item</th>
                      <th className="py-3 px-4 w-16 text-center">Delete</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                    {dishes.map((dish, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700/60 transition-colors group">
                        <td className="py-3 px-4 text-slate-400 dark:text-slate-500 tabular-nums font-mono text-center font-bold">
                          {idx + 1}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-bold text-slate-900 dark:text-white text-sm">{dish.name}</span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => removeDish(idx)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/60 transition-all active:scale-[0.96] cursor-pointer inline-flex items-center justify-center"
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
      )}

      {activeTab === 'manual' && (
        /* Manual Input Mode */
        <div className="space-y-3">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            Paste dishes line by line (format: <code className="text-emerald-700 dark:text-emerald-400 font-mono">Dish Name | Description | Price</code>):
          </label>
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            rows={5}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-2xl p-3.5 text-xs text-slate-900 dark:text-white focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 font-mono"
          />
          <button
            onClick={() => {
              handleParseManual();
              setActiveTab('upload');
            }}
            className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition-all active:scale-[0.96] cursor-pointer"
          >
            Load Manual Dishes into Table
          </button>
        </div>
      )}

      {activeTab === 'history' && (
        /* Past Scanned Menus History Tab */
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Locally Stored Menus & Past Scans</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Click "Load Menu" to instantly evaluate any past menu without re-uploading the image.
              </p>
            </div>
          </div>

          {savedMenus.length === 0 ? (
            <div className="text-center py-12 text-slate-400 dark:text-slate-500 space-y-2">
              <Bookmark className="w-10 h-10 mx-auto opacity-30" />
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">No saved menu scans yet.</p>
              <p className="text-[11px] text-slate-400 dark:text-slate-500">
                Upload a menu photo in the "Image OCR" tab and it will automatically be archived here.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {savedMenus.map((menu) => {
                const imgUrl = menu.image_url
                  ? menu.image_url.startsWith('http')
                    ? menu.image_url
                    : `${API_BASE_URL}${menu.image_url}`
                  : null;

                const dishCount = (menu.dishes || []).length;
                const formattedDate = menu.created_at
                  ? new Date(menu.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })
                  : 'Recent Scan';

                return (
                  <div
                    key={menu.id}
                    className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 p-4 hover:border-emerald-300 dark:hover:border-emerald-700 hover:bg-white dark:hover:bg-slate-800 transition-all shadow-2xs flex flex-col justify-between space-y-3 group"
                  >
                    <div className="flex items-start gap-3">
                      {imgUrl ? (
                        <img
                          src={imgUrl}
                          alt={menu.title}
                          className="w-14 h-14 rounded-xl object-cover border border-slate-200 dark:border-slate-700 shrink-0 shadow-2xs"
                        />
                      ) : (
                        <div className="w-14 h-14 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                          <FileText className="w-6 h-6" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-white truncate">{menu.title || 'Untitled Menu'}</h4>
                        <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          <span className="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-bold text-[10px]">
                            {dishCount} dishes
                          </span>
                          <span>• {formattedDate}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-slate-200/80 dark:border-slate-800">
                      <button
                        onClick={() => onLoadMenu(menu)}
                        className="flex-1 py-1.5 px-3 rounded-xl bg-slate-900 dark:bg-slate-800 hover:bg-emerald-600 dark:hover:bg-emerald-600 text-white font-bold text-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Load Menu</span>
                      </button>
                      <button
                        onClick={() => handleDeleteSavedMenu(menu.id)}
                        className="p-1.5 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/60 border border-slate-200 dark:border-slate-700 transition cursor-pointer"
                        title="Delete saved menu"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
