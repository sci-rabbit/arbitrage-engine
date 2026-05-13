import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { getHasAccess, isTokenExpired } from '../utils/jwt'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  hasAccess: boolean
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  logout: () => void
  checkExpiry: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      hasAccess: false,
      isAuthenticated: false,

      setTokens: (access, refresh) => {
        set({
          accessToken: access,
          refreshToken: refresh,
          hasAccess: getHasAccess(access),
          isAuthenticated: true,
        })
      },

      logout: () => {
        set({
          accessToken: null,
          refreshToken: null,
          hasAccess: false,
          isAuthenticated: false,
        })
      },

      checkExpiry: () => {
        const token = get().accessToken
        if (!token || isTokenExpired(token)) {
          return false
        }
        return true
      },
    }),
    {
      name: 'auth',
      partialize: (s) => ({ accessToken: s.accessToken, refreshToken: s.refreshToken }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) {
          state.hasAccess = getHasAccess(state.accessToken)
          const accessValid = !isTokenExpired(state.accessToken)
          const refreshValid = Boolean(state.refreshToken && !isTokenExpired(state.refreshToken))
          state.isAuthenticated = accessValid || refreshValid
        }
      },
    },
  ),
)