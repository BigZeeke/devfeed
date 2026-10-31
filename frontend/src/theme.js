/**
 * DevFeed's single Material UI theme.
 *
 * Every component reads its colors, fonts, and corner rounding from here,
 * so the look of the app changes in one place instead of scattered CSS files.
 */
import { createTheme } from '@mui/material/styles'

const devfeedTheme = createTheme({
  // CSS variables let the browser switch between the light and dark
  // palettes below on its own, following the operating system setting.
  cssVariables: true,

  // One palette per color scheme; MUI fills in the remaining shades.
  colorSchemes: {
    light: {
      palette: {
        primary: { main: '#1565c0' },
        secondary: { main: '#ef6c00' },
      },
    },
    dark: {
      palette: {
        primary: { main: '#90caf9' },
        secondary: { main: '#ffb74d' },
      },
    },
  },

  // Roboto is bundled through @fontsource/roboto (imported in main.jsx).
  typography: {
    fontFamily: 'Roboto, "Helvetica Neue", Arial, sans-serif',
  },

  shape: {
    borderRadius: 8,
  },
})

export default devfeedTheme
