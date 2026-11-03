/**
 * App layout: the top app bar with navigation and log-in state, plus the page routes.
 *
 * Every page renders inside the same Container below the app bar,
 * so spacing and width stay consistent across the app.
 */
import { useState } from 'react'
import { NavLink, Route, Routes, useNavigate } from 'react-router'
import Alert from '@mui/material/Alert'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import DynamicFeedIcon from '@mui/icons-material/DynamicFeed'

import { useAuth } from './auth/useAuth.js'
import AboutPage from './pages/AboutPage.jsx'
import FeedPage from './pages/FeedPage.jsx'
import LogInPage from './pages/LogInPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import SignUpPage from './pages/SignUpPage.jsx'

// Pages shown as buttons in the app bar, in display order.
const navigationLinks = [
  { label: 'Feed', path: '/' },
  { label: 'About', path: '/about' },
]

// NavLink adds the "active" class to the link for the current page.
const activeLinkStyle = { '&.active': { textDecoration: 'underline', textUnderlineOffset: 6 } }

function App() {
  const { isLoggedIn, username, logOut } = useAuth()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logOutErrorMessage, setLogOutErrorMessage] = useState(null)

  async function handleLogOut() {
    setIsLoggingOut(true)
    setLogOutErrorMessage(null)
    try {
      await logOut()
      navigate('/')
    } catch {
      // logOut() keeps the session when the server can't be reached.
      setLogOutErrorMessage('Could not log out. Is the backend running? Please try again.')
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <>
      <AppBar position="sticky">
        <Toolbar>
          <DynamicFeedIcon sx={{ marginRight: 1 }} />
          <Typography
            variant="h6"
            component={NavLink}
            to="/"
            sx={{ color: 'inherit', textDecoration: 'none', flexGrow: 1 }}
          >
            DevFeed
          </Typography>

          <Box component="nav" sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {navigationLinks.map((navigationLink) => (
              <Button
                key={navigationLink.path}
                component={NavLink}
                to={navigationLink.path}
                // "end" makes "/" active only on the feed itself, not on every page.
                end
                color="inherit"
                sx={activeLinkStyle}
              >
                {navigationLink.label}
              </Button>
            ))}

            {isLoggedIn ? (
              <>
                {/* Shows who is logged in */}
                <Typography variant="body2" sx={{ marginLeft: 2 }}>
                  {username}
                </Typography>
                <Button color="inherit" onClick={handleLogOut} disabled={isLoggingOut}>
                  Log out
                </Button>
              </>
            ) : (
              <>
                <Button component={NavLink} to="/login" color="inherit" sx={activeLinkStyle}>
                  Log in
                </Button>
                <Button component={NavLink} to="/signup" color="inherit" sx={activeLinkStyle}>
                  Sign up
                </Button>
              </>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <Container component="main" maxWidth="md" sx={{ paddingY: 3 }}>
        {logOutErrorMessage && (
          <Alert severity="error" onClose={() => setLogOutErrorMessage(null)} sx={{ marginBottom: 2 }}>
            {logOutErrorMessage}
          </Alert>
        )}
        <Routes>
          <Route path="/" element={<FeedPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/login" element={<LogInPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          {/* Any other path shows the not-found page */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Container>
    </>
  )
}

export default App
