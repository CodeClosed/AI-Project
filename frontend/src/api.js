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

export async function evaluateRecommendations(userMatrix, dishes, goodThreshold = 75, badThreshold = 45, apiKey = null) {
  // Extract clean string names if dishes are objects
  const itemsList = (dishes || []).map((dish) =>
    typeof dish === 'string' ? dish : dish.name || dish.label || String(dish)
  );

  const response = await fetch(`${API_BASE_URL}/api/recommend/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_matrix: userMatrix,
      dishes: dishes,
      items: itemsList, // Sends the required clean list to backend
      good_threshold: goodThreshold,
      bad_threshold: badThreshold,
      api_key: apiKey,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Recommendation evaluation failed with status ${response.status}`);
  }

  return await response.json();
}
