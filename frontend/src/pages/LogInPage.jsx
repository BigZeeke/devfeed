/**
 * Log-in page: username and password form that calls the token endpoint.
 *
 * On success the session is stored (see AuthProvider) and the user goes to
 * the feed. If the app sent the user here because a saved token was
 * rejected, location.state.sessionEnded is true and a notice explains why.
 */
import { useState } from 'react'
import { Link as RouterLink, useLocation, useNavigate } from 'react-router'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Link from '@mui/material/Link'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'

import { useAuth } from '../auth/useAuth.js'
import { describeFormError } from '../formErrors.js'

const LOG_IN_FIELD_NAMES = ['username', 'password']

function LogInPage() {
  const { isLoggedIn, username: loggedInUsername, logIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const sessionEnded = location.state?.sessionEnded === true

  const [usernameInput, setUsernameInput] = useState('')
  const [passwordInput, setPasswordInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState({ fieldErrors: {}, generalMessage: null })

  async function handleSubmit(event) {
    // Stop the browser's own form submit (a full page reload).
    event.preventDefault()
    setIsSubmitting(true)
    setFormError({ fieldErrors: {}, generalMessage: null })
    try {
      await logIn({ username: usernameInput, password: passwordInput })
      // replace: Back from the feed shouldn't return to the log-in form.
      navigate('/', { replace: true })
    } catch (error) {
      setFormError(describeFormError(error, LOG_IN_FIELD_NAMES))
      setIsSubmitting(false)
    }
  }

  if (isLoggedIn) {
    return (
      <Alert severity="info">
        You're logged in as {loggedInUsername}. Log out first to switch accounts.
      </Alert>
    )
  }

  return (
    <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate sx={{ maxWidth: 400 }}>
      <Typography variant="h4" component="h1">
        Log in
      </Typography>

      {sessionEnded && (
        <Alert severity="info">Your session has ended. Please log in again.</Alert>
      )}
      {formError.generalMessage && <Alert severity="error">{formError.generalMessage}</Alert>}

      <TextField
        label="Username"
        name="username"
        autoComplete="username"
        value={usernameInput}
        onChange={(event) => setUsernameInput(event.target.value)}
        error={Boolean(formError.fieldErrors.username)}
        helperText={formError.fieldErrors.username}
        required
        autoFocus
      />
      <TextField
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        value={passwordInput}
        onChange={(event) => setPasswordInput(event.target.value)}
        error={Boolean(formError.fieldErrors.password)}
        helperText={formError.fieldErrors.password}
        required
      />

      <Button type="submit" variant="contained" disabled={isSubmitting} sx={{ alignSelf: 'flex-start' }}>
        {isSubmitting ? 'Logging in…' : 'Log in'}
      </Button>

      <Typography variant="body2">
        No account yet?{' '}
        <Link component={RouterLink} to="/signup">
          Sign up
        </Link>
      </Typography>
    </Stack>
  )
}

export default LogInPage
