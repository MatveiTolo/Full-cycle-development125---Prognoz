# ml-model/ml/forecast.py
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import StandardScaler
from typing import Dict, List
import datetime as dt
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import warnings
warnings.filterwarnings('ignore')

# Глобальный кеш для моделей (чтобы не переобучать каждый раз)
_MODEL_CACHE = {}
_SCALER_CACHE = {}

def _download_close(ticker: str, start_date: str) -> pd.Series:
    """Скачивание исторических данных"""
    try:
        d = yf.download(
            ticker,
            start=start_date,
            progress=False,
            auto_adjust=False,
            actions=False,
            threads=False,
        )
        if d.empty:
            return pd.Series(dtype=float)
        
        s = d["Close"] if "Close" in d else d.get("Adj Close", pd.Series(dtype=float))
        s = s.copy()
        s.index = pd.to_datetime(s.index)
        
        if s.index.tz is not None:
            s.index = s.index.tz_localize(None)
        
        s = s.sort_index()
        idx_b = pd.date_range(s.index.min(), s.index.max(), freq="B")
        s = s.reindex(idx_b).ffill()
        return s.dropna()
    except Exception as e:
        raise ValueError(f"Error downloading data for {ticker}: {str(e)}")

def _rsi(series: pd.Series, n: int = 14) -> pd.Series:
    """Расчет RSI индикатора"""
    delta = series.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = (-delta.clip(upper=0)).rolling(n).mean()
    rs = up / (down.replace(0, np.nan))
    return 100 - (100 / (1 + rs))

def _build_dataset(ticker: str, start_date: str) -> pd.DataFrame:
    """Построение датасета с признаками"""
    exog_map = {
        "USDRUB=X": ["EURRUB=X", "BZ=F", "GC=F"],
        "AAPL": ["SPY", "GC=F"],
        "MSFT": ["SPY", "AAPL"],
        "GOOGL": ["SPY", "AAPL"],
        "AMZN": ["SPY", "AAPL"],
        "SPY": ["^GSPC", "GC=F"],
        "^GSPC": ["SPY", "GC=F"],
        "EURUSD=X": ["GBPUSD=X", "GC=F"],
        "GBPUSD=X": ["EURUSD=X", "GC=F"],
        "GC=F": ["BZ=F", "SPY"],
        "BZ=F": ["GC=F", "SPY"],
    }
    
    exog = exog_map.get(ticker, ["SPY", "GC=F"])  # значения по умолчанию
    
    tickers = [ticker] + exog
    data = {}
    
    for t in tickers:
        s = _download_close(t, start_date)
        if not s.empty:
            data[t] = s
    
    if ticker not in data:
        raise ValueError(f"No data for ticker {ticker}")
    
    df = pd.concat(data, axis=1).dropna()
    df.columns = list(data.keys())
    
    # Целевая переменная - лог-доходность
    df["ret_target"] = np.log(df[ticker] / df[ticker].shift(1))
    
    # Лог-доходности экзогенных переменных
    for t in exog:
        if t in df.columns:
            df[f"ret_{t}"] = np.log(df[t] / df[t].shift(1))
    
    # Технические индикаторы
    ret_full = np.log(df[ticker] / df[ticker].shift(1))
    df["vol20"] = ret_full.rolling(20).std()
    df["ma5"] = df[ticker].rolling(5).mean()
    df["ma20"] = df[ticker].rolling(20).mean()
    df["ma60"] = df[ticker].rolling(60).mean()
    df["rsi14"] = _rsi(df[ticker], 14)
    roll_max60 = df[ticker].rolling(60).max()
    df["dd60"] = df[ticker] / roll_max60 - 1.0
    
    # Лаги целевой переменной
    for lag in [1, 2, 3, 5]:
        df[f"ret_target_lag{lag}"] = df["ret_target"].shift(lag)
    
    df = df.dropna()
    return df

def _make_future_bdays(last_date: pd.Timestamp, horizon: int) -> List[pd.Timestamp]:
    """Генерация будущих рабочих дней"""
    start = (last_date + pd.tseries.offsets.BDay(1)).date()
    rng = pd.bdate_range(start=start, periods=horizon)
    return list(rng)

def _prepare_features(df: pd.DataFrame, ticker: str):
    """Подготовка признаков для модели"""
    base_exog = [c for c in df.columns if c.startswith("ret_") and c != "ret_target"]
    feature_cols = base_exog + [
        "vol20",
        "ma5",
        "ma20",
        "ma60",
        "rsi14",
        "dd60",
        "ret_target_lag1",
        "ret_target_lag2",
        "ret_target_lag3",
        "ret_target_lag5",
    ]
    
    X_raw = df[feature_cols].values
    y_raw = df["ret_target"].values.reshape(-1, 1)
    
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_scaled = scaler_X.fit_transform(X_raw)
    y_scaled = scaler_y.fit_transform(y_raw)
    
    return X_scaled, y_scaled, scaler_X, scaler_y, feature_cols

def _create_sequences(X_scaled, y_scaled, window=30):
    """Создание последовательностей для LSTM"""
    X_seq, y_seq = [], []
    for i in range(window, len(X_scaled)):
        X_seq.append(X_scaled[i - window : i, :])
        y_seq.append(y_scaled[i, 0])
    
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq).reshape(-1, 1)
    
    return X_seq, y_seq

def _build_lstm_model(input_shape):
    """Создание LSTM модели"""
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.LSTM(64, return_sequences=False),
        layers.Dense(32, activation="relu"),
        layers.Dense(1, activation="linear"),
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=5e-4),
        loss="mse",
        metrics=["mae"]
    )
    
    return model

def forecast_ticker(
    ticker: str,
    horizon_days: int,
    start_date: str = "2015-01-01",
    use_cache: bool = True
) -> Dict:
    """
    Основная функция прогнозирования
    
    Args:
        ticker: Тикер актива (AAPL, USDRUB=X, etc.)
        horizon_days: Горизонт прогноза (3-30 дней)
        start_date: Дата начала исторических данных
        use_cache: Использовать кешированные модели
    
    Returns:
        Dict с историей и прогнозом
    """
    # Валидация параметров
    horizon_days = int(horizon_days)
    if not (3 <= horizon_days <= 30):
        horizon_days = max(3, min(30, horizon_days))
    
    # Кеширование
    cache_key = f"{ticker}_{start_date}"
    
    if use_cache and cache_key in _MODEL_CACHE:
        model, scaler_X, scaler_y, feature_cols = _MODEL_CACHE[cache_key]
        df = _build_dataset(ticker, start_date)
    else:
        # Построение датасета
        df = _build_dataset(ticker, start_date)
        
        # Фильтрация по текущей дате
        today = pd.Timestamp(dt.date.today())
        df = df.loc[df.index <= today]
        
        if df.empty or df.shape[0] < 120:
            raise ValueError("Not enough historical data (minimum 120 days required)")
        
        # Подготовка признаков
        X_scaled, y_scaled, scaler_X, scaler_y, feature_cols = _prepare_features(df, ticker)
        
        # Создание последовательностей
        window = 30
        X_seq, y_seq = _create_sequences(X_scaled, y_scaled, window)
        
        if X_seq.shape[0] < 10:
            raise ValueError("Not enough sequence samples to train")
        
        # Обучение модели
        tf.random.set_seed(123)
        model = _build_lstm_model((X_seq.shape[1], X_seq.shape[2]))
        
        # Ускоренное обучение для API
        model.fit(
            X_seq, y_seq,
            epochs=15,
            batch_size=64,
            validation_split=0.1,
            verbose=0
        )
        
        # Кеширование
        if use_cache:
            _MODEL_CACHE[cache_key] = (model, scaler_X, scaler_y, feature_cols)
            _SCALER_CACHE[cache_key] = (scaler_X, scaler_y, feature_cols)
    
    # Подготовка истории
    hist_prices = df[ticker].copy()
    last_date = hist_prices.index[-1]
    history_window_days = min(60, len(hist_prices))
    history_dates = [pd.Timestamp(d).date().isoformat() 
                    for d in hist_prices.index[-history_window_days:]]
    history_vals = [float(v) for v in hist_prices.values[-history_window_days:]]
    
    # Прогнозирование
    X_scaled, y_scaled, scaler_X, scaler_y, feature_cols = _prepare_features(df, ticker)
    last_window_scaled = X_scaled[-30:, :]
    price_list = list(hist_prices.values)
    ret_list = list(df["ret_target"].values)
    forecast_prices = []
    
    for _ in range(horizon_days):
        # Предсказание
        pred_scaled = model.predict(last_window_scaled[np.newaxis, ...], verbose=0)[0, 0]
        ret_pred = float(scaler_y.inverse_transform(np.array([[pred_scaled]]))[0, 0])
        
        # Расчет следующей цены
        next_price = price_list[-1] * float(np.exp(ret_pred))
        price_list.append(next_price)
        ret_list.append(ret_pred)
        forecast_prices.append(next_price)
        
        # Обновление признаков для следующего шага
        p_series = pd.Series(price_list)
        r_series = pd.Series(ret_list)
        
        # Пересчет технических индикаторов
        vol20 = float(r_series[-20:].std()) if len(r_series) >= 20 else 0.0
        ma5 = float(p_series[-5:].mean()) if len(p_series) >= 5 else 0.0
        ma20 = float(p_series[-20:].mean()) if len(p_series) >= 20 else 0.0
        ma60 = float(p_series[-60:].mean()) if len(p_series) >= 60 else 0.0
        
        rsi14_series = _rsi(p_series, 14)
        rsi14 = float(rsi14_series.iloc[-1]) if not rsi14_series.empty else 0.0
        
        roll_max60 = float(p_series[-60:].max()) if len(p_series) >= 60 else 0.0
        dd60 = (next_price / roll_max60 - 1.0) if roll_max60 not in (0.0, np.nan) else 0.0
        
        # Подготовка нового вектора признаков
        new_features = []
        for col in feature_cols:
            if col == "vol20":
                new_features.append(vol20)
            elif col == "ma5":
                new_features.append(ma5)
            elif col == "ma20":
                new_features.append(ma20)
            elif col == "ma60":
                new_features.append(ma60)
            elif col == "rsi14":
                new_features.append(rsi14)
            elif col == "dd60":
                new_features.append(dd60)
            elif col == "ret_target_lag1":
                new_features.append(ret_list[-1])
            elif col == "ret_target_lag2":
                new_features.append(ret_list[-2] if len(ret_list) >= 2 else 0.0)
            elif col == "ret_target_lag3":
                new_features.append(ret_list[-3] if len(ret_list) >= 3 else 0.0)
            elif col == "ret_target_lag5":
                new_features.append(ret_list[-5] if len(ret_list) >= 5 else 0.0)
            elif col.startswith("ret_"):
                # Для экзогенных переменных используем последние доступные значения
                new_features.append(0.0)  # Заглушка
        
        new_features_scaled = scaler_X.transform([new_features])
        last_window_scaled = np.vstack([last_window_scaled[1:], new_features_scaled])
    
    # Формирование дат прогноза
    future_dates = _make_future_bdays(last_date, horizon_days)
    forecast_dates_iso = [d.date().isoformat() for d in future_dates]
    
    return {
        "ticker": ticker,
        "horizon": horizon_days,
        "last_training_date": last_date.date().isoformat(),
        "history": {
            "dates": history_dates,
            "prices": history_vals
        },
        "forecast": {
            "dates": forecast_dates_iso,
            "prices": [float(x) for x in forecast_prices]
        },
        "metadata": {
            "history_points": len(history_vals),
            "forecast_points": len(forecast_prices),
            "model_type": "LSTM"
        }
    }

# Вспомогательные функции для API
def get_available_tickers() -> List[str]:
    """Список поддерживаемых тикеров"""
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", 
        "SPY", "^GSPC", 
        "USDRUB=X", "EURUSD=X", "GBPUSD=X",
        "GC=F", "BZ=F"
    ]

def clear_cache():
    """Очистка кеша моделей"""
    global _MODEL_CACHE, _SCALER_CACHE
    _MODEL_CACHE.clear()
    _SCALER_CACHE.clear()
    return {"status": "cache cleared", "cleared_models": len(_MODEL_CACHE)}