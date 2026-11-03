/**
 * The React Context that shares the logged-in session with every page.
 *
 * Kept in its own file (not in AuthProvider.jsx) so the react-refresh lint
 * rule stays clean: component files should export only components.
 */
import { createContext } from 'react'

// null outside an AuthProvider; useAuth() turns that into a clear error.
export const AuthContext = createContext(null)
