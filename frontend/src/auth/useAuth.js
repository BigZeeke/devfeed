/**
 * Hook for reading the session and the log-in, sign-up, and log-out actions.
 */
import { useContext } from 'react'

import { AuthContext } from './AuthContext.js'

export function useAuth() {
  const authValue = useContext(AuthContext)
  if (authValue === null) {
    throw new Error('useAuth() must be used inside <AuthProvider>.')
  }
  return authValue
}
