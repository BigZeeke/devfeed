/**
 * Sign-up page: username, optional email, and password form that calls the register endpoint.
 *
 * The register endpoint returns a token, so a successful sign-up also logs
 * the user in (see AuthProvider) and goes to the feed. Django's password
 * validators run on the server; their messages show under the password field.
 * The confirm-password check runs only in the browser, because DevFeed has no
 * password reset: a typo at sign-up would lock the user out after log-out.
 */
import { useState } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Link from '@mui/material/Link'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'

import { useAuth } from '../auth/useAuth.js'
import { describeFormError } from '../formErrors.js'

const SIGN_UP_FIELD_NAMES = ['username', 'email', 'password']

function SignUpPage() {
  const { isLoggedIn, username: loggedInUsername, signUp } = useAuth()
  const navigate = useNavigate()

  const [usernameInput, setUsernameInput] = useState('')
  const [emailInput, setEmailInput] = useState('')
  const [passwordInput, setPasswordInput] = useState('')
  const [confirmPasswordInput, setConfirmPasswordInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState({ fieldErrors: {}, generalMessage: null })

  async function handleSubmit(event) {
    // Stop the browser's own form submit (a full page reload).
    event.preventDefault()
    // Catch a mistyped password before anything is sent to the server.
    if (passwordInput !== confirmPasswordInput) {
      setFormError({
        fieldErrors: { confirmPassword: 'Passwords do not match.' },
        generalMessage: null,
      })
      return
    }
    setIsSubmitting(true)
    setFormError({ fieldErrors: {}, generalMessage: null })
    try {
      await signUp({ username: usernameInput, email: emailInput, password: passwordInput })
      // replace: Back from the feed shouldn't return to the sign-up form.
      navigate('/', { replace: true })
    } catch (error) {
      setFormError(describeFormError(error, SIGN_UP_FIELD_NAMES))
      setIsSubmitting(false)
    }
  }

  if (isLoggedIn) {
    return (
      <Alert severity="info">
        You're logged in as {loggedInUsername}. Log out first to create another account.
      </Alert>
    )
  }

  return (
    <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate sx={{ maxWidth: 400 }}>
      <Typography variant="h4" component="h1">
        Sign up
      </Typography>

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
        label="Email (optional)"
        name="email"
        type="email"
        autoComplete="email"
        value={emailInput}
        onChange={(event) => setEmailInput(event.target.value)}
        error={Boolean(formError.fieldErrors.email)}
        helperText={formError.fieldErrors.email}
      />
      <TextField
        label="Password"
        name="password"
        type="password"
        // Tells password managers to offer a new password, not a saved one.
        autoComplete="new-password"
        value={passwordInput}
        onChange={(event) => setPasswordInput(event.target.value)}
        error={Boolean(formError.fieldErrors.password)}
        helperText={formError.fieldErrors.password}
        required
      />
      <TextField
        label="Confirm password"
        name="confirmPassword"
        type="password"
        autoComplete="new-password"
        value={confirmPasswordInput}
        onChange={(event) => setConfirmPasswordInput(event.target.value)}
        error={Boolean(formError.fieldErrors.confirmPassword)}
        helperText={formError.fieldErrors.confirmPassword}
        required
      />

      <Button type="submit" variant="contained" disabled={isSubmitting} sx={{ alignSelf: 'flex-start' }}>
        {isSubmitting ? 'Creating account…' : 'Sign up'}
      </Button>

      <Typography variant="body2">
        Already have an account?{' '}
        <Link component={RouterLink} to="/login">
          Log in
        </Link>
      </Typography>
    </Stack>
  )
}

export default SignUpPage
