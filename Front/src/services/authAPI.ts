import axios from 'axios';
import { AuthResponse, LoginData, RegisterData } from '../types/auth';

const API_URL = 'http://localhost:8000/api';

export const authApi = {
  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await axios.post(`${API_URL}/auth/login`, data);
    return response.data;
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await axios.post(`${API_URL}/auth/register`, data);
    return response.data;
  }
};