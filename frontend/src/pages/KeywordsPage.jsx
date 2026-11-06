/**
 * Keywords page: the keywords the logged-in user follows, from /api/keywords/.
 *
 * A form at the top follows a new keyword with a weight (create), and the
 * list below shows followed keywords alphabetically with their weights
 * (read). Each row has Edit (update, in a dialog) and Stop following
 * (delete, after a confirm step). The page number lives in the URL
 * (?page=2), like the feed.
 */
import { Fragment, useEffect, useState } from 'react'
import { Link as RouterLink, useSearchParams } from 'react-router'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import Link from '@mui/material/Link'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import Pagination from '@mui/material/Pagination'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'

import {
  ApiError,
  createKeyword,
  deleteKeyword,
  fetchKeywordsPage,
  KEYWORD_MAX_LENGTH,
  KEYWORDS_PAGE_SIZE,
  updateKeyword,
} from '../api.js'
import { useAuth } from '../auth/useAuth.js'
import { describeFormError } from '../formErrors.js'

const KEYWORD_FIELD_NAMES = ['keyword', 'weight']

// Shown instead of DRF's "The fields user, keyword must make a unique set."
const ALREADY_FOLLOWING_MESSAGE = "You're already following that keyword."

// Reads ?page= from the URL; anything missing or invalid means page 1.
function parsePageNumber(pageParameter) {
  const pageNumber = Number.parseInt(pageParameter, 10)
  return Number.isInteger(pageNumber) && pageNumber > 0 ? pageNumber : 1
}

// Turns a failed list request into a message a reader can act on.
function describeRequestError(error) {
  if (error instanceof ApiError) {
    // DRF answers 404 when the page number is past the last page.
    if (error.status === 404) {
      return 'That page of your keywords does not exist.'
    }
    return `Could not load your keywords. ${error.message}`
  }
  // fetch() itself failed: server down, wrong address, or CORS refused.
  return 'Could not reach the DevFeed API. Is the backend running?'
}

// Turns a failed create or update into form messages. The only non-field
// error the keyword API returns is the duplicate check, so it gets a clearer message.
function describeKeywordFormError(error) {
  if (error instanceof ApiError && error.status === 400 && error.responseBody?.non_field_errors) {
    return { fieldErrors: {}, generalMessage: ALREADY_FOLLOWING_MESSAGE }
  }
  return describeFormError(error, KEYWORD_FIELD_NAMES)
}

// The weight box holds text; an empty box lets the API use its default (1).
// Anything else is sent as a number, and the API rejects non-integers.
function readWeightInput(weightInput) {
  return weightInput.trim() === '' ? undefined : Number(weightInput)
}

// Edit dialog for one keyword. The parent mounts it only while it is open,
// so each opening starts from the keyword's current values. Only fields that
// changed are sent; renaming to a keyword already followed shows the same
// "already following" message as the Follow form.
function KeywordEditDialog({ keywordItem, onCancel, onSaved }) {
  const [keywordInput, setKeywordInput] = useState(keywordItem.keyword)
  const [weightInput, setWeightInput] = useState(String(keywordItem.weight))
  const [isSaving, setIsSaving] = useState(false)
  const [formError, setFormError] = useState({ fieldErrors: {}, generalMessage: null })

  async function handleSubmit(event) {
    // Stop the browser's own form submit (a full page reload).
    event.preventDefault()

    // An empty weight box keeps the current weight, since nothing is sent for it.
    const changedFields = {}
    if (keywordInput !== keywordItem.keyword) {
      changedFields.keyword = keywordInput
    }
    const newWeight = readWeightInput(weightInput)
    if (newWeight !== undefined && newWeight !== keywordItem.weight) {
      changedFields.weight = newWeight
    }
    // Nothing changed: close without a request.
    if (Object.keys(changedFields).length === 0) {
      onCancel()
      return
    }

    setIsSaving(true)
    setFormError({ fieldErrors: {}, generalMessage: null })
    try {
      await updateKeyword(keywordItem.id, changedFields)
      onSaved()
    } catch (error) {
      setFormError(describeKeywordFormError(error))
      setIsSaving(false)
    }
  }

  return (
    <Dialog
      open
      // Closing by Escape or a click outside is blocked while a save is in flight.
      onClose={isSaving ? undefined : onCancel}
      fullWidth
      maxWidth="xs"
      slotProps={{ paper: { component: 'form', onSubmit: handleSubmit, noValidate: true } }}
    >
      <DialogTitle>Edit keyword</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ paddingTop: 1 }}>
          {formError.generalMessage && <Alert severity="error">{formError.generalMessage}</Alert>}
          <TextField
            label="Keyword"
            name="keyword"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            error={Boolean(formError.fieldErrors.keyword)}
            helperText={formError.fieldErrors.keyword ?? 'Saved in lowercase'}
            slotProps={{ htmlInput: { maxLength: KEYWORD_MAX_LENGTH } }}
            required
            autoFocus
          />
          <TextField
            label="Weight"
            name="weight"
            type="number"
            value={weightInput}
            onChange={(event) => setWeightInput(event.target.value)}
            error={Boolean(formError.fieldErrors.weight)}
            helperText={formError.fieldErrors.weight ?? 'Whole number'}
            slotProps={{ htmlInput: { step: 1 } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" variant="contained" disabled={isSaving || keywordInput.trim() === ''}>
          {isSaving ? 'Saving…' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// Logged-out visitors get a pointer to the log-in page instead of a request
// that would only return 401.
function KeywordsPage() {
  const { isLoggedIn } = useAuth()

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        Keywords
      </Typography>
      {isLoggedIn ? (
        <KeywordsManager />
      ) : (
        <Alert severity="info">
          <Link component={RouterLink} to="/login">
            Log in
          </Link>{' '}
          to follow keywords.
        </Alert>
      )}
    </Stack>
  )
}

function KeywordsManager() {
  const [searchParams, setSearchParams] = useSearchParams()
  const currentPage = parsePageNumber(searchParams.get('page'))

  // Bumped after a change so the current page is fetched again in the
  // server's alphabetical order.
  const [reloadCount, setReloadCount] = useState(0)
  const requestKey = `${currentPage}-${reloadCount}`

  // The result of the most recent finished request, tagged with the request
  // it was for, so loading can be derived instead of stored.
  const [requestResult, setRequestResult] = useState({
    requestKey: null,
    keywordsPage: null,
    errorMessage: null,
  })

  // The Follow form.
  const [keywordInput, setKeywordInput] = useState('')
  const [weightInput, setWeightInput] = useState('1')
  const [isFollowing, setIsFollowing] = useState(false)
  const [followFormError, setFollowFormError] = useState({ fieldErrors: {}, generalMessage: null })

  // Which dialog is open, if any: the keyword being edited or being removed.
  // The remove dialog has its own open flag, so the keyword's name stays
  // visible while the dialog fades out after it closes.
  const [keywordBeingEdited, setKeywordBeingEdited] = useState(null)
  const [keywordBeingRemoved, setKeywordBeingRemoved] = useState(null)
  const [isRemoveDialogOpen, setIsRemoveDialogOpen] = useState(false)
  const [isRemoving, setIsRemoving] = useState(false)
  const [removeErrorMessage, setRemoveErrorMessage] = useState(null)

  useEffect(() => {
    // Cancels the request if the page changes or the component unmounts,
    // so a slow old response can't overwrite a newer one.
    const abortController = new AbortController()
    const thisRequestKey = `${currentPage}-${reloadCount}`

    fetchKeywordsPage(currentPage, { signal: abortController.signal })
      .then((keywordsPage) => {
        setRequestResult({ requestKey: thisRequestKey, keywordsPage, errorMessage: null })
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          return
        }
        setRequestResult({
          requestKey: thisRequestKey,
          keywordsPage: null,
          errorMessage: describeRequestError(error),
        })
      })

    return () => abortController.abort()
  }, [currentPage, reloadCount])

  // Still loading until a result for the current request has arrived.
  const isLoading = requestResult.requestKey !== requestKey

  function handlePageChange(event, newPageNumber) {
    // Page 1 is the plain /keywords URL; other pages add ?page=N.
    setSearchParams(newPageNumber === 1 ? {} : { page: String(newPageNumber) })
  }

  async function handleFollowSubmit(event) {
    // Stop the browser's own form submit (a full page reload).
    event.preventDefault()
    setIsFollowing(true)
    setFollowFormError({ fieldErrors: {}, generalMessage: null })
    try {
      await createKeyword({ keyword: keywordInput, weight: readWeightInput(weightInput) })
      // Ready for the next keyword; the list reloads to show the new one in order.
      setKeywordInput('')
      setWeightInput('1')
      setReloadCount((previousCount) => previousCount + 1)
    } catch (error) {
      setFollowFormError(describeKeywordFormError(error))
    } finally {
      setIsFollowing(false)
    }
  }

  // A renamed keyword can move to another place in the alphabetical list,
  // so the page is fetched again instead of patching one row.
  function handleEditSaved() {
    setKeywordBeingEdited(null)
    setReloadCount((previousCount) => previousCount + 1)
  }

  async function handleRemoveConfirm() {
    setIsRemoving(true)
    setRemoveErrorMessage(null)
    const wasLastOnPage = requestResult.keywordsPage.results.length === 1
    try {
      await deleteKeyword(keywordBeingRemoved.id)
      if (wasLastOnPage && currentPage > 1) {
        // This page is now empty, so step back one page instead of showing a 404.
        handlePageChange(null, currentPage - 1)
      } else {
        setReloadCount((previousCount) => previousCount + 1)
      }
    } catch {
      setRemoveErrorMessage(`Could not stop following "${keywordBeingRemoved.keyword}". Please try again.`)
    } finally {
      setIsRemoveDialogOpen(false)
      setIsRemoving(false)
    }
  }

  let listContent
  if (isLoading) {
    listContent = (
      <Box sx={{ display: 'flex', justifyContent: 'center', paddingY: 6 }}>
        <CircularProgress aria-label="Loading keywords" />
      </Box>
    )
  } else if (requestResult.errorMessage) {
    listContent = <Alert severity="error">{requestResult.errorMessage}</Alert>
  } else if (requestResult.keywordsPage.results.length === 0) {
    listContent = <Alert severity="info">You're not following any keywords yet.</Alert>
  } else {
    const { count, results } = requestResult.keywordsPage
    const totalPages = Math.ceil(count / KEYWORDS_PAGE_SIZE)
    listContent = (
      <Stack spacing={2}>
        <Typography variant="body2" color="text.secondary">
          Following {count} {count === 1 ? 'keyword' : 'keywords'}
        </Typography>
        <Paper variant="outlined">
          <List disablePadding>
            {results.map((keywordItem, itemIndex) => (
              // Fragment, not a Box, so the list holds only <li> elements.
              <Fragment key={keywordItem.id}>
                {itemIndex > 0 && <Divider component="li" />}
                <ListItem>
                  <ListItemText primary={keywordItem.keyword} />
                  <Chip label={`weight ${keywordItem.weight}`} size="small" sx={{ marginRight: 1 }} />
                  {/* Icon-only buttons, so each label names the keyword for screen readers */}
                  <IconButton
                    aria-label={`Edit ${keywordItem.keyword}`}
                    onClick={() => setKeywordBeingEdited(keywordItem)}
                  >
                    <EditOutlinedIcon />
                  </IconButton>
                  <IconButton
                    aria-label={`Stop following ${keywordItem.keyword}`}
                    color="error"
                    onClick={() => {
                      setKeywordBeingRemoved(keywordItem)
                      setIsRemoveDialogOpen(true)
                    }}
                  >
                    <DeleteOutlinedIcon />
                  </IconButton>
                </ListItem>
              </Fragment>
            ))}
          </List>
        </Paper>
        {totalPages > 1 && (
          <Pagination
            count={totalPages}
            page={currentPage}
            onChange={handlePageChange}
            color="primary"
            sx={{ alignSelf: 'center' }}
          />
        )}
      </Stack>
    )
  }

  return (
    <Stack spacing={3}>
      {/* Follow form (create) */}
      <Stack component="form" spacing={2} onSubmit={handleFollowSubmit} noValidate>
        {followFormError.generalMessage && (
          <Alert severity="error">{followFormError.generalMessage}</Alert>
        )}
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: 'flex-start' }}>
          <TextField
            label="Keyword"
            name="keyword"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            error={Boolean(followFormError.fieldErrors.keyword)}
            helperText={followFormError.fieldErrors.keyword ?? 'Saved in lowercase'}
            slotProps={{ htmlInput: { maxLength: KEYWORD_MAX_LENGTH } }}
            required
            sx={{ flexGrow: 1 }}
          />
          <TextField
            label="Weight"
            name="weight"
            type="number"
            value={weightInput}
            onChange={(event) => setWeightInput(event.target.value)}
            error={Boolean(followFormError.fieldErrors.weight)}
            helperText={followFormError.fieldErrors.weight ?? 'Whole number'}
            slotProps={{ htmlInput: { step: 1 } }}
            sx={{ width: { sm: 140 } }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={isFollowing || keywordInput.trim() === ''}
            // Lines the button up with the text boxes, above their helper text.
            sx={{ height: 56 }}
          >
            {isFollowing ? 'Following…' : 'Follow'}
          </Button>
        </Stack>
      </Stack>

      {removeErrorMessage && (
        <Alert severity="error" onClose={() => setRemoveErrorMessage(null)}>
          {removeErrorMessage}
        </Alert>
      )}

      {listContent}

      {keywordBeingEdited && (
        <KeywordEditDialog
          keywordItem={keywordBeingEdited}
          onCancel={() => setKeywordBeingEdited(null)}
          onSaved={handleEditSaved}
        />
      )}

      {/* Confirm step before a delete, since it can't be undone from the UI */}
      <Dialog
        open={isRemoveDialogOpen}
        onClose={isRemoving ? undefined : () => setIsRemoveDialogOpen(false)}
      >
        <DialogTitle>Stop following this keyword?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            "{keywordBeingRemoved?.keyword}" will be removed from your keywords.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsRemoveDialogOpen(false)} disabled={isRemoving}>
            Cancel
          </Button>
          <Button color="error" variant="contained" onClick={handleRemoveConfirm} disabled={isRemoving}>
            {isRemoving ? 'Removing…' : 'Stop following'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

export default KeywordsPage
