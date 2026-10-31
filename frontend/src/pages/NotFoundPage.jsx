/**
 * Not-found page: shown for any URL that doesn't match a route in App.jsx.
 */
import { Link as RouterLink } from 'react-router'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

function NotFoundPage() {
  return (
    <Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
      <Typography variant="h4" component="h1">
        Page not found
      </Typography>
      <Typography>There's no page at this address.</Typography>
      <Button variant="contained" component={RouterLink} to="/">
        Back to the feed
      </Button>
    </Stack>
  )
}

export default NotFoundPage
