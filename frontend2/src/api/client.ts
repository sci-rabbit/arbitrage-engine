import axios from 'axios'
import { useAuthStore } from '../store/auth'

export const userApi = axios.create({ baseURL: '/user-api' })
export const aggApi = axios.create({ baseURL: '/agg-api' })

function injectAuth(config: Parameters<Parameters<typeof userApi.interceptors.request.use>[0]>[0]) {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
}

userApi.interceptors.request.use(injectAuth)
aggApi.interceptors.request.use(injectAuth)

let refreshPromise: Promise<string> | null = null

async function getRefreshedToken(): Promise<string> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    const refreshToken = useAuthStore.getState().refreshToken
    if (!refreshToken) throw new Error('No refresh token')
    const { data } = await axios.post('/user-api/auth/refresh', { refresh_token: refreshToken })
    useAuthStore.getState().setTokens(data.access_token, data.refresh_token ?? refreshToken)
    return data.access_token
  })().finally(() => { refreshPromise = null })
  return refreshPromise
}

async function refreshAndRetry(error: { config?: any; response?: { status: number } }, instance: typeof userApi) {
  const original = error.config
  if (error.response?.status === 401 && !original._retry) {
    original._retry = true
    try {
      const newToken = await getRefreshedToken()
      original.headers.Authorization = `Bearer ${newToken}`
      return instance(original)
    } catch {
      useAuthStore.getState().logout()
    }
  }
  return Promise.reject(error)
}

userApi.interceptors.response.use((r) => r, (e) => refreshAndRetry(e, userApi))
aggApi.interceptors.response.use((r) => r, (e) => refreshAndRetry(e, aggApi))
