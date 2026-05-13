import { userApi } from './client'
import type { AuthTokens } from '../types'

export const authApi = {
  register: (email: string, password: string) =>
    userApi.post('/auth/register', { email, password }),

  login: (email: string, password: string) =>
    userApi.post<AuthTokens>('/auth/login', { email, password }),

  refresh: (refreshToken: string) =>
    userApi.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken }),

  verifyEmail: (token: string) =>
    userApi.get('/auth/verify', { params: { token } }),

  resendVerification: () =>
    userApi.post('/auth/resend-verification'),

  forgotPassword: (email: string) =>
    userApi.post('/auth/forgot-password', { email }),

  resetPassword: (token: string, password: string) =>
    userApi.post('/auth/reset-password', { token, new_password: password }),
}