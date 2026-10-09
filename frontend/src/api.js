/**
 * Frontend API client communicating with the FastAPI backend.
 * Provides JWT auth token injection, account management, persistent database
 * synchronization for health profiles and logged meals, and OCR/recommendations.
 */

export function getApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('nutrimenu_custom_api_url');
    if (custom) return custom.replace(/\/+$/, '');
  }
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return 'http://127.0.0.1:8000';
  }
  return 'http://127.0.0.1:8000';
}

export function setCustomApiUrl(url) {
  try {
    if (url && url.trim()) {
      localStorage.setItem('nutrimenu_custom_api_url', url.trim().replace(/\/+$/, ''));
    } else {
      localStorage.removeItem('nutrimenu_custom_api_url');
    }
  } catch {}
}

export const API_BASE_URL = getApiBaseUrl();

const AUTH_TOKEN_KEY = 'nutrimenu_auth_token';

export function getStoredToken() {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch {}
}

export function clearStoredToken() {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {}
}

/**
 * Universal wrapper for API calls with automatic Bearer token injection.
 */
async function fetchWithAuth(endpoint, options = {}) {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  const headers = { ...options.headers };

  const token = getStoredToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Only set application/json if body is not FormData
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && token) {
      clearStoredToken();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:session_expired'));
      }
    }

    return response;
  } catch (err) {
    if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
      const currentUrl = getApiBaseUrl();
      throw new Error(`Unable to connect to backend at ${currentUrl}. Please make sure the FastAPI server is running (python run_fullstack.py).`);
    }
    throw err;
  }
}


// =====================================================================
// 🔐 AUTHENTICATION & USER MANAGEMENT
// =====================================================================

export async function registerUser(email, password, profile = null) {
  const res = await fetchWithAuth('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, profile }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Registration failed.');
  }

  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function loginUser(email, password) {
  const res = await fetchWithAuth('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Invalid email or password.');
  }

  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function fetchCurrentUser() {
  const token = getStoredToken();
  if (!token) return null;

  const res = await fetchWithAuth('/api/auth/me', {
    method: 'GET',
  });

  if (!res.ok) {
    clearStoredToken();
    return null;
  }
  return await res.json();
}

export async function fetchUserProfile() {
  const res = await fetchWithAuth('/api/profile', {
    method: 'GET',
  });
  if (!res.ok) return null;
  return await res.json();
}

export async function updateUserProfile(profileData) {
  const res = await fetchWithAuth('/api/profile', {
    method: 'PUT',
    body: JSON.stringify(profileData),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to update profile in database.');
  }
  return await res.json();
}

export async function saveUserApiKey(apiKey) {
  const res = await fetchWithAuth('/api/profile/apikey', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to update API key.');
  }
  return await res.json();
}

export async function changeUserPassword(oldPassword, newPassword) {
  const res = await fetchWithAuth('/api/auth/password', {
    method: 'PUT',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to change password.');
  }
  return data;
}

export async function deleteUserAccount(password) {
  const res = await fetchWithAuth('/api/auth/account', {
    method: 'DELETE',
    body: JSON.stringify({ password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to delete account.');
  }
  clearStoredToken();
  return data;
}

export async function requestForgotPassword(email) {
  const res = await fetchWithAuth('/api/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to request password reset code.');
  }
  return data;
}

export async function submitPasswordReset(email, otpCode, newPassword) {
  const res = await fetchWithAuth('/api/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ email, otp_code: otpCode, new_password: newPassword }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to reset password.');
  }
  return data;
}

export async function verifyMfaLogin(tempToken, code) {
  const res = await fetchWithAuth('/api/auth/mfa/verify', {
    method: 'POST',
    body: JSON.stringify({ temp_token: tempToken, code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Invalid 2FA verification code.');
  }
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function setupMfa() {
  const res = await fetchWithAuth('/api/auth/mfa/setup', {
    method: 'POST',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to setup 2FA.');
  }
  return data;
}

export async function enableMfa(code) {
  const res = await fetchWithAuth('/api/auth/mfa/enable', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to enable 2FA.');
  }
  return data;
}

export async function disableMfa(password) {
  const res = await fetchWithAuth('/api/auth/mfa/disable', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to disable 2FA.');
  }
  return data;
}


// =====================================================================
// 🍱 LOGGED MEALS & CALENDAR DATABASE SYNCHRONIZATION
// =====================================================================

export async function fetchUserMeals(date = null) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  const res = await fetchWithAuth(`/api/meals${query}`, {
    method: 'GET',
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function saveMealToDb(mealData) {
  const res = await fetchWithAuth('/api/meals', {
    method: 'POST',
    body: JSON.stringify(mealData),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to save meal to database.');
  }
  return await res.json();
}

export async function deleteMealFromDb(mealId) {
  const res = await fetchWithAuth(`/api/meals/${encodeURIComponent(mealId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to delete meal from database.');
  }
  return await res.json();
}


// =====================================================================
// 🥗 OCR & RECOMMENDATION PIPELINE
// =====================================================================

export async function uploadMenuImage(imageFile, apiKey = null) {
  const formData = new FormData();
  formData.append('file', imageFile);
  if (apiKey) {
    formData.append('api_key', apiKey);
  }

  const response = await fetchWithAuth('/api/ocr/extract', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `OCR extraction failed with status ${response.status}`);
  }

  return await response.json();
}

export async function generateHealthMatrix(profilePayload) {
  const response = await fetchWithAuth('/api/matrix/generate', {
    method: 'POST',
    body: JSON.stringify(profilePayload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Matrix synthesis failed with status ${response.status}`);
  }

  return await response.json();
}

export async function evaluateRecommendations(payload) {
  try {
    const res = await fetchWithAuth('/api/recommend/evaluate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Server returned status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error('API call error:', err);
    return null;
  }
}

export async function evaluatePlate(payload) {
  try {
    const res = await fetchWithAuth('/api/plate/evaluate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Plate evaluation failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error('Plate evaluation error:', err);
    return null;
  }
}

export async function completePlate(payload) {
  try {
    const res = await fetchWithAuth('/api/plate/complete', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Plate completion failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error('Plate completion error:', err);
    return null;
  }
}

// =====================================================================
// 📋 SAVED MENUS & SCAN HISTORY
// =====================================================================

export async function fetchSavedMenus() {
  try {
    const res = await fetchWithAuth('/api/menus');
    if (!res.ok) {
      if (res.status === 401) return [];
      throw new Error(`Failed fetching saved menus: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn('Could not fetch saved menus:', err);
    return [];
  }
}

export async function saveMenuToDb(menuData) {
  const res = await fetchWithAuth('/api/menus', {
    method: 'POST',
    body: JSON.stringify(menuData),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Failed saving menu.');
  }
  return await res.json();
}

export async function deleteSavedMenu(menuId) {
  const res = await fetchWithAuth(`/api/menus/${menuId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Failed deleting menu.');
  }
  return await res.json();
}

// =====================================================================
// ⚡ ASYNC JOBS & REAL-TIME PROGRESS
// =====================================================================

export async function startMenuScanJob(imageFile, profile = null, apiKey = null) {
  const formData = new FormData();
  formData.append('file', imageFile);
  if (apiKey) {
    formData.append('api_key', apiKey);
  }
  if (profile) {
    formData.append('profile', JSON.stringify(profile));
  }

  const response = await fetchWithAuth('/api/jobs/menu-scan', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to start scan job with status ${response.status}`);
  }

  return await response.json();
}

export async function fetchJobStatus(jobId) {
  const response = await fetchWithAuth(`/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job status: ${response.status}`);
  }
  return await response.json();
}

export async function pollMenuScanJob(jobId, onProgress) {
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const job = await fetchJobStatus(jobId);
        if (onProgress && typeof onProgress === 'function') {
          onProgress(job);
        }

        if (job.status === 'completed') {
          clearInterval(interval);
          resolve(job.result);
        } else if (job.status === 'failed') {
          clearInterval(interval);
          reject(new Error(job.error || 'Job processing failed.'));
        }
      } catch (err) {
        clearInterval(interval);
        reject(err);
      }
    }, 600);
  });
}


