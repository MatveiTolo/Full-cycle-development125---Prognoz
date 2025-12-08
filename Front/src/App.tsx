import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

// Простой Dashboard вместо ForecastDashboard
const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  
  return (
    <div style={{ padding: '20px' }}>
      <h1>📈 Forecast Dashboard</h1>
      <p>Welcome, <strong>{user?.username}</strong>!</p>
      <p>Email: {user?.email}</p>
      <button onClick={logout}>Logout</button>
      
      <div style={{ marginTop: '30px' }}>
        <h2>Your forecast data will appear here...</h2>
        <p>Connect to backend to see real data.</p>
      </div>
    </div>
  );
};

// Защищённый маршрут
const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" />;
};

// Основной компонент
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route 
            path="/" 
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            } 
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;