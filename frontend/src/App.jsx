/**
 * App layout: the top app bar with navigation, plus the page routes.
 *
 * Every page renders inside the same Container below the app bar,
 * so spacing and width stay consistent across the app.
 */
import { NavLink, Route, Routes } from 'react-router'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import DynamicFeedIcon from '@mui/icons-material/DynamicFeed'

import AboutPage from './pages/AboutPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

// Pages shown as buttons in the app bar, in display order.
const navigationLinks = [
  { label: 'Feed', path: '/' },
  { label: 'About', path: '/about' },
]

function App() {
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

          <Box component="nav" sx={{ display: 'flex', gap: 1 }}>
            {navigationLinks.map((navigationLink) => (
              <Button
                key={navigationLink.path}
                component={NavLink}
                to={navigationLink.path}
                // "end" makes "/" active only on the feed itself, not on every page.
                end
                color="inherit"
                // NavLink adds the "active" class to the link for the current page.
                sx={{ '&.active': { textDecoration: 'underline', textUnderlineOffset: 6 } }}
              >
                {navigationLink.label}
              </Button>
            ))}
          </Box>
        </Toolbar>
      </AppBar>

      <Container component="main" maxWidth="md" sx={{ paddingY: 3 }}>
        <Routes>
          {/* Temporary placeholder until the feed page is added in the next commit */}
          <Route path="/" element={<Typography>The article feed comes next.</Typography>} />
          <Route path="/about" element={<AboutPage />} />
          {/* Any other path shows the not-found page */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Container>
    </>
  )
}

export default App
