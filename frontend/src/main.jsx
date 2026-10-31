/**
 * Entry point: mounts the React app into the #root element of index.html.
 *
 * Wraps the app in the providers every page needs: the MUI theme,
 * CssBaseline (consistent default styles), and the React Router browser router.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

// Roboto font weights used by MUI's default typography.
import '@fontsource/roboto/300.css'
import '@fontsource/roboto/400.css'
import '@fontsource/roboto/500.css'
import '@fontsource/roboto/700.css'

import App from './App.jsx'
import devfeedTheme from './theme.js'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={devfeedTheme}>
      {/* Resets browser default styles and applies the theme's background and text colors */}
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
