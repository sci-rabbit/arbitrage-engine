import type { TokenPayload } from '../types'

export function decodeJwt(token: string): TokenPayload {
  const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
  const json = atob(base64)
  return JSON.parse(json) as TokenPayload
}

export function isTokenExpired(token: string): boolean {
  try {
    const { exp } = decodeJwt(token)
    return Date.now() / 1000 >= exp - 30
  } catch {
    return true
  }
}

export function getHasAccess(token: string): boolean {
  try {
    return Boolean(decodeJwt(token).has_access)
  } catch {
    return false
  }
}