import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [tickers, setTickers] = useState([])
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Загружаем тикеры при запуске
    axios.get('http://localhost:8000/api/tickers')
      .then(response => {
        setTickers(response.data.tickers)
      })
      .catch(error => {
        console.error('Error loading tickers:', error)
      })
  }, [])

  const getForecast = (ticker) => {
    setLoading(true)
    axios.post('http://localhost:8000/api/forecast', {
      ticker: ticker,
      horizon: 7
    })
    .then(response => {
      setForecast(response.data)
      setLoading(false)
    })
    .catch(error => {
      console.error('Error getting forecast:', error)
      setLoading(false)
    })
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>📈 Forecast Dashboard</h1>
      
      <div style={{ 
        backgroundColor: '#f0f8ff', 
        padding: '15px', 
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <p><strong>Backend:</strong> ✅ Running on http://localhost:8000</p>
        <p><strong>Frontend:</strong> ✅ Running on http://localhost:5173</p>
      </div>

      <h2>Available Symbols:</h2>
      <div style={{ 
        display: 'flex', 
        gap: '10px', 
        flexWrap: 'wrap',
        marginBottom: '30px'
      }}>
        {tickers.map(ticker => (
          <button
            key={ticker}
            onClick={() => getForecast(ticker)}
            style={{
              padding: '12px 24px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold',
              transition: 'background-color 0.3s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#0056b3'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#007bff'}
          >
            {ticker}
          </button>
        ))}
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <p>⏳ Loading forecast data...</p>
        </div>
      )}

      {forecast && !loading && (
        <div style={{ 
          marginTop: '30px', 
          padding: '25px', 
          border: '2px solid #007bff',
          borderRadius: '10px',
          backgroundColor: '#f8f9fa'
        }}>
          <h2 style={{ color: '#007bff', marginBottom: '20px' }}>
            Forecast for {forecast.ticker} (next {forecast.horizon} days)
          </h2>
          
          <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap' }}>
            <div>
              <h3>📊 History (Last 60 days):</h3>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {forecast.history.dates.slice(-5).map((date, index) => (
                  <li key={date} style={{ 
                    padding: '8px', 
                    borderBottom: '1px solid #eee',
                    display: 'flex',
                    justifyContent: 'space-between'
                  }}>
                    <span>{date}</span>
                    <span style={{ fontWeight: 'bold' }}>
                      ${forecast.history.prices.slice(-5)[index].toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div>
              <h3>🔮 Forecast (Next {forecast.horizon} days):</h3>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {forecast.forecast.dates.map((date, index) => (
                  <li key={date} style={{ 
                    padding: '8px', 
                    borderBottom: '1px solid #eee',
                    display: 'flex',
                    justifyContent: 'space-between',
                    backgroundColor: index === 0 ? '#e7f3ff' : 'transparent'
                  }}>
                    <span>{date}</span>
                    <span style={{ 
                      fontWeight: 'bold',
                      color: forecast.forecast.prices[index] > (forecast.history.prices.slice(-1)[0] || 0) 
                        ? '#28a745' 
                        : '#dc3545'
                    }}>
                      ${forecast.forecast.prices[index].toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          
          <div style={{ marginTop: '20px', fontSize: '14px', color: '#666' }}>
            <p>Last training date: {forecast.last_training_date}</p>
            <p>Model type: {forecast.metadata?.model_type || 'LSTM'}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App