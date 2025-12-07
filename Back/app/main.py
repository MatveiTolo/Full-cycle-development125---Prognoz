# Back/app/main.py - МИНИМАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys
import os
import datetime as dt
import uvicorn

print("=" * 50)
print("🚀 STARTING FORECAST API SERVER")
print("=" * 50)

# Попробуем импортировать ML модуль
try:
    # Добавляем путь к ml-model
    import pathlib
    BASE_DIR = pathlib.Path(__file__).parent.parent.parent
    
    # Проверяем разные возможные имена папки
    possible_paths = ['ml-model', 'm1.model', 'ml_model']
    ml_path = None
    
    for path_name in possible_paths:
        test_path = BASE_DIR / path_name
        if os.path.exists(test_path):
            ml_path = str(test_path)
            sys.path.insert(0, ml_path)
            print(f"✅ Found ML directory: {test_path}")
            break
    
    if ml_path:
        from ml.forecast import forecast_ticker
        print("✅ ML module imported successfully!")
        ML_AVAILABLE = True
    else:
        print("⚠️ ML directory not found, running in API-only mode")
        ML_AVAILABLE = False
        
except ImportError as e:
    print(f"⚠️ ML import error: {e}")
    ML_AVAILABLE = False
    forecast_ticker = None

app = FastAPI(title="Forecast API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "Forecast API",
        "ml_available": ML_AVAILABLE,
        "endpoints": ["/", "/health", "/api/tickers", "/api/forecast"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": dt.datetime.now().isoformat()}

@app.get("/api/tickers")
def get_tickers():
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "SPY", "USDRUB=X"]
    return {"tickers": tickers}

# Модель запроса
class ForecastRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    horizon: int = Field(..., ge=3, le=30)

@app.post("/api/forecast")
async def forecast(request: ForecastRequest):
    if not ML_AVAILABLE:
        raise HTTPException(status_code=503, detail="ML module not available")
    
    try:
        # Имитация прогноза для теста
        import random
        return {
            "ticker": request.ticker,
            "horizon": request.horizon,
            "history": {
                "dates": ["2024-12-01", "2024-12-02"],
                "prices": [100.0, 101.5]
            },
            "forecast": {
                "dates": ["2024-12-03", "2024-12-04"],
                "prices": [102.0 + random.random(), 103.0 + random.random()]
            },
            "mode": "test"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(f"🌐 Server will run on: http://localhost:8000")
    print(f"📊 ML available: {ML_AVAILABLE}")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)