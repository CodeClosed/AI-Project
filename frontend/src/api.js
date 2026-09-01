/**
 * Frontend API client communicating with the FastAPI backend.
 */

const API_BASE_URL = 'http://127.0.0.1:8000';

export async function uploadMenuImage(imageFile, apiKey = null) {
  const formData = new FormData();
  formData.append('file', imageFile);
  if (apiKey) {
    formData.append('api_key', apiKey);
  }

  const response = await fetch(`${API_BASE_URL}/api/ocr/extract`, {
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
  const response = await fetch(`${API_BASE_URL}/api/matrix/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
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
    const res = await fetch(`${API_BASE_URL}/api/recommend/evaluate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Server returned status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error("API call error:", err);
    return null;
  }
}

export async function evaluatePlate(payload) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/plate/evaluate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Plate evaluation failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error("Plate evaluation error:", err);
    return null;
  }
}

export async function completePlate(payload) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/plate/complete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Plate completion failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error("Plate completion error:", err);
    return null;
  }
}


