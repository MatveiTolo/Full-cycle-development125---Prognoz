const API_URL = "http://localhost:8000";

export const getTickers = async () => {
  const response = await fetch(`${API_URL}/api/tickers`);
  return response.json();
};

export const getForecast = async (ticker, horizon) => {
  const response = await fetch(`${API_URL}/api/forecast`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ticker, horizon }),
  });
  return response.json();
};