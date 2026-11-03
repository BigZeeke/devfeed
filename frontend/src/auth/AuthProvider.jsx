/**
 * Holds the logged-in session and shares it through AuthContext.
 *
 * Starts from the session saved in localStorage, so a page reload keeps the
 * user logged in. Also registers the app-wide 401 rule with api.js: a
 * rejected token clears the session and sends the user to the log-in page.
 * Must sit inside <BrowserRouter>, because it uses useNavigate().
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'

import { ApiError, logInUser, logOutUser, registerUser, setUnauthorizedHandler } from '../api.js'
import { AuthContext } from './AuthContext.js'
import { clearStoredSession, readStoredSession, saveStoredSession } from './authStorage.js'

function AuthProvider({ children }) {
  // { token, username } when logged in, null when logged out.
  const [session, setSession] = useState(() => readStoredSession())
  const navigate = useNavigate()

  useEffect(() => {
    // Runs only when api.js reports a 401 for a request that sent a token.
    setUnauthorizedHandler(() => {
      clearStoredSession()
      setSession(null)
      // The log-in page reads sessionEnded from location.state to explain why.
      navigate('/login', { replace: true, state: { sessionEnded: true } })
    })
    return () => setUnauthorizedHandler(null)
  }, [navigate])

  // Saves a new session in storage and in state.
  function startSession(newSession) {
    saveStoredSession(newSession)
    setSession(newSession)
  }

  async function logIn({ username, password }) {
    // The token endpoint returns only the token, so keep the typed username.
    const { token } = await logInUser({ username, password })
    startSession({ token, username })
  }

  async function signUp({ username, email, password }) {
    const registration = await registerUser({ username, email, password })
    startSession({ token: registration.token, username: registration.username })
  }

  async function logOut() {
    try {
      await logOutUser()
    } catch (error) {
      // 401: the token was already invalid, so the user is logged out anyway.
      // Anything else (server down): keep the session, since the token still
      // works on the server, and let the caller show an error.
      if (!(error instanceof ApiError && error.status === 401)) {
        throw error
      }
    }
    clearStoredSession()
    setSession(null)
  }

  const authValue = {
    isLoggedIn: session !== null,
    username: session?.username ?? null,
    logIn,
    signUp,
    logOut,
  }

  return <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>
}

export default AuthProvider
