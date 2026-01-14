import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Definição do contexto de autenticação
const AuthContext = createContext(undefined);

// URL base da API FastAPI
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://deadlytruth-backend-production.up.railway.app';
const ALLOW_MOCK_AUTH = import.meta.env.VITE_ALLOW_MOCK_AUTH === 'true';

// Provedor de autenticação
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Carrega o token do localStorage e valida a sessão
  useEffect(() => {
    const storedToken = localStorage.getItem('jwt_token');
    if (!storedToken) {
      setLoading(false);
      return;
    }

    setToken(storedToken);
    setIsAuthenticated(true);

    const validateSession = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        });

        if (!response.ok) {
          throw new Error('Sessão expirada ou inválida.');
        }

        const data = await response.json();
        setUser({ email: data.email });
      } catch (e) {
        console.warn('Falha ao validar sessão:', e.message);
        logout();
      } finally {
        setLoading(false);
      }
    };

    if (ALLOW_MOCK_AUTH && storedToken.startsWith('mock.')) {
      try {
        const payload = JSON.parse(atob(storedToken.split('.')[1]));
        setUser({ email: payload.sub || payload.email || 'Usuário' });
      } catch (e) {
        console.error("Failed to decode token:", e);
        logout();
      } finally {
        setLoading(false);
      }
    } else {
      validateSession();
    }
  }, []);

  // Função de Login
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ username: email, password: password }).toString(),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Falha no login' }));
        throw new Error(errorData.detail || 'Falha no login');
      }

      const data = await response.json();
      localStorage.setItem('jwt_token', data.access_token);
      setToken(data.access_token);
      setIsAuthenticated(true);
      setUser({ email: email });
      navigate('/lobby');
    } catch (err) {
      if (ALLOW_MOCK_AUTH) {
        // Modo desenvolvimento: permite login sem backend
        console.warn('Auth endpoint não disponível, usando modo desenvolvimento:', err.message);
        const mockToken = btoa(JSON.stringify({ sub: email, exp: Date.now() + 86400000 }));
        localStorage.setItem('jwt_token', `mock.${mockToken}.token`);
        setToken(`mock.${mockToken}.token`);
        setIsAuthenticated(true);
        setUser({ email: email });
        navigate('/lobby');
      } else {
        setError(err.message || 'Erro desconhecido ao fazer login.');
        setIsAuthenticated(false);
        setToken(null);
        setUser(null);
        localStorage.removeItem('jwt_token');
      }
    } finally {
      setLoading(false);
    }
  };

  // Função de Registro
  const register = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Falha no registro' }));
        throw new Error(errorData.detail || 'Falha no registro');
      }

      // Se o registro for bem-sucedido, loga automaticamente
      await login(email, password);
      navigate('/lobby');
    } catch (err) {
      if (ALLOW_MOCK_AUTH) {
        console.warn('Auth endpoint não disponível, usando modo desenvolvimento:', err.message);
        await login(email, password);
      } else {
        setError(err.message || 'Erro desconhecido ao registrar.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Função de Logout
  const logout = () => {
    localStorage.removeItem('jwt_token');
    setToken(null);
    setIsAuthenticated(false);
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, user, loading, login, register, logout, error }}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook personalizado para usar o contexto de autenticação
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
