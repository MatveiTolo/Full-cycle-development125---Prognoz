from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import List
import os

from ml.forecast import forecast_ticker


class ForecastRequest(BaseModel):
	ticker: str
	horizon: int

	@field_validator("ticker")
	@classmethod
	def _validate_ticker(cls, v: str):
		v = (v or "").strip()
		if not v:
			raise ValueError("ticker must not be empty")
		return v

	@field_validator("horizon")
	@classmethod
	def _validate_horizon(cls, v: int):
		if not (3 <= v <= 30):
			raise ValueError("horizon must be between 3 and 30")
		return v


app = FastAPI(title="Forecast Service ML", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.isdir(static_dir):
	app.mount("/static", StaticFiles(directory=static_dir), name="static")

print("=" * 50)
print(f"Current file: {__file__}")
print(f"Directory of main.py: {os.path.dirname(__file__)}")
print(f"Static directory path: {static_dir}")
print(f"Static directory exists: {os.path.isdir(static_dir)}")

if os.path.isdir(static_dir):
    print("Files in static directory:")
    for file in os.listdir(static_dir):
        print(f"  - {file}")
    
    index_path = os.path.join(static_dir, "index.html")
    print(f"Index.html path: {index_path}")
    print(f"Index.html exists: {os.path.exists(index_path)}")
print("=" * 50)


@app.get("/")
def root():
	index_path = os.path.join(static_dir, "index.html")
	if os.path.exists(index_path):
		return FileResponse(index_path)
	return JSONResponse({"status": "ok", "message": "Forecast Service ML"})


@app.get("/api/symbols")
def get_symbols():
	symbols = [
		{"value": "AAPL", "label": "Apple Inc. (AAPL)"},
		{"value": "MSFT", "label": "Microsoft (MSFT)"},
		{"value": "GOOGL", "label": "Alphabet Class A (GOOGL)"},
		{"value": "AMZN", "label": "Amazon (AMZN)"},
		{"value": "SPY", "label": "SPDR S&P 500 ETF (SPY)"},
		{"value": "^GSPC", "label": "S&P 500 Index (^GSPC)"},
		{"value": "USDRUB=X", "label": "USD/RUB (Доллар/Рубль)"},
		{"value": "EURUSD=X", "label": "EUR/USD (Евро/Доллар)"},
		{"value": "GBPUSD=X", "label": "GBP/USD (Фунт/Доллар)"},
		{"value": "GC=F", "label": "Gold Futures (GC=F)"},
		{"value": "BZ=F", "label": "Brent Crude Oil (BZ=F)"},
	]
	return {"symbols": symbols}


@app.post("/api/forecast")
def post_forecast(req: ForecastRequest):
	try:
		out = forecast_ticker(ticker=req.ticker, horizon_days=req.horizon)
		return out
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
