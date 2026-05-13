import { userApi } from './client'
import type { CryptoPayment } from '../types'

export const paymentsApi = {
  getCurrencies: () =>
    userApi.get<string[]>('/payments/currencies'),

  createPayment: (amount: number, currency: string) =>
    userApi.post<CryptoPayment>('/payments/create', { amount, currency }),
}