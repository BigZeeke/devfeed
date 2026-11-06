/**
 * Saved page: the logged-in user's bookmarks from /api/bookmarks/.
 *
 * Read, update and delete for bookmarks: each saved article shows its note
 * and saved date, a "Read" checkbox that saves right away, an Edit button
 * for the note, and a Remove button with a confirm step. The page number
 * lives in the URL (?page=2), like the feed.
 */
import { useEffect, useState } from 'react'
import { Link as RouterLink, useSearchParams } from 'react-router'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActions from '@mui/material/CardActions'
import CardContent from '@mui/material/CardContent'
import Checkbox from '@mui/material/Checkbox'
import CircularProgress from '@mui/material/CircularProgress'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import FormControlLabel from '@mui/material/FormControlLabel'
import Link from '@mui/material/Link'
import Pagination from '@mui/material/Pagination'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import {
  ApiError,
  BOOKMARKS_PAGE_SIZE,
  deleteBookmark,
  fetchBookmarksPage,
  updateBookmark,
} from '../api.js'
import { useAuth } from '../auth/useAuth.js'
import BookmarkNoteDialog from '../components/BookmarkNoteDialog.jsx'

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
      return 'That page of your saved articles does not exist.'
    }
    return `Could not load your saved articles. ${error.message}`
  }
  // fetch() itself failed: server down, wrong address, or CORS refused.
  return 'Could not reach the DevFeed API. Is the backend running?'
}

// Formats an ISO timestamp as "Nov 5, 2026" in the reader's locale.
function formatSavedDate(createdAt) {
  return new Date(createdAt).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// Logged-out visitors get a pointer to the log-in page instead of a request
// that would only return 401.
function SavedPage() {
  const { isLoggedIn } = useAuth()

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        Saved articles
      </Typography>
      {isLoggedIn ? (
        <SavedBookmarksList />
      ) : (
        <Alert severity="info">
          <Link component={RouterLink} to="/login">
            Log in
          </Link>{' '}
          to see your saved articles.
        </Alert>
      )}
    </Stack>
  )
}

function SavedBookmarksList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const currentPage = parsePageNumber(searchParams.get('page'))

  // Bumped after a delete so the current page is fetched again, which pulls
  // the next bookmark up from the following page.
  const [reloadCount, setReloadCount] = useState(0)
  const requestKey = `${currentPage}-${reloadCount}`

  // The result of the most recent finished request, tagged with the request
  // it was for, so loading can be derived instead of stored.
  const [requestResult, setRequestResult] = useState({
    requestKey: null,
    bookmarksPage: null,
    errorMessage: null,
  })

  // Which dialog is open, if any: the bookmark being edited or being removed.
  const [bookmarkBeingEdited, setBookmarkBeingEdited] = useState(null)
  const [bookmarkBeingRemoved, setBookmarkBeingRemoved] = useState(null)
  const [isRemoving, setIsRemoving] = useState(false)

  // Ids of bookmarks whose "Read" checkbox is saving, so it can't be clicked twice.
  const [readSavingBookmarkIds, setReadSavingBookmarkIds] = useState([])

  // Errors from the read toggle and remove, shown above the list.
  const [actionErrorMessage, setActionErrorMessage] = useState(null)

  useEffect(() => {
    // Cancels the request if the page changes or the component unmounts,
    // so a slow old response can't overwrite a newer one.
    const abortController = new AbortController()
    const thisRequestKey = `${currentPage}-${reloadCount}`

    fetchBookmarksPage(currentPage, { signal: abortController.signal })
      .then((bookmarksPage) => {
        setRequestResult({ requestKey: thisRequestKey, bookmarksPage, errorMessage: null })
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          return
        }
        setRequestResult({
          requestKey: thisRequestKey,
          bookmarksPage: null,
          errorMessage: describeRequestError(error),
        })
      })

    return () => abortController.abort()
  }, [currentPage, reloadCount])

  // Still loading until a result for the current request has arrived.
  const isLoading = requestResult.requestKey !== requestKey

  // Swaps one updated bookmark into the loaded page without refetching.
  function replaceBookmarkInPage(updatedBookmark) {
    setRequestResult((previousResult) => ({
      ...previousResult,
      bookmarksPage: {
        ...previousResult.bookmarksPage,
        results: previousResult.bookmarksPage.results.map((bookmark) =>
          bookmark.id === updatedBookmark.id ? updatedBookmark : bookmark,
        ),
      },
    }))
  }

  function handlePageChange(event, newPageNumber) {
    // Page 1 is the plain /saved URL; other pages add ?page=N.
    setSearchParams(newPageNumber === 1 ? {} : { page: String(newPageNumber) })
    window.scrollTo({ top: 0 })
  }

  async function handleReadToggle(bookmark, isReadChecked) {
    setActionErrorMessage(null)
    setReadSavingBookmarkIds((previousIds) => [...previousIds, bookmark.id])
    try {
      const updatedBookmark = await updateBookmark(bookmark.id, { is_read: isReadChecked })
      replaceBookmarkInPage(updatedBookmark)
    } catch {
      setActionErrorMessage(`Could not update "${bookmark.article_title}". Please try again.`)
    } finally {
      setReadSavingBookmarkIds((previousIds) =>
        previousIds.filter((savingId) => savingId !== bookmark.id),
      )
    }
  }

  // Called by the note dialog; errors are thrown back so the dialog shows them.
  async function handleNoteSave(note) {
    const updatedBookmark = await updateBookmark(bookmarkBeingEdited.id, { note })
    replaceBookmarkInPage(updatedBookmark)
    setBookmarkBeingEdited(null)
  }

  async function handleRemoveConfirm() {
    setIsRemoving(true)
    setActionErrorMessage(null)
    const wasLastOnPage = requestResult.bookmarksPage.results.length === 1
    try {
      await deleteBookmark(bookmarkBeingRemoved.id)
      if (wasLastOnPage && currentPage > 1) {
        // This page is now empty, so step back one page instead of showing a 404.
        handlePageChange(null, currentPage - 1)
      } else {
        setReloadCount((previousCount) => previousCount + 1)
      }
    } catch {
      setActionErrorMessage(
        `Could not remove "${bookmarkBeingRemoved.article_title}". Please try again.`,
      )
    } finally {
      setBookmarkBeingRemoved(null)
      setIsRemoving(false)
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', paddingY: 6 }}>
        <CircularProgress aria-label="Loading saved articles" />
      </Box>
    )
  }
  if (requestResult.errorMessage) {
    return <Alert severity="error">{requestResult.errorMessage}</Alert>
  }
  if (requestResult.bookmarksPage.results.length === 0) {
    return (
      <Alert severity="info">
        Nothing saved yet. Use Save on an article in the{' '}
        <Link component={RouterLink} to="/">
          feed
        </Link>
        .
      </Alert>
    )
  }

  const totalPages = Math.ceil(requestResult.bookmarksPage.count / BOOKMARKS_PAGE_SIZE)

  return (
    <Stack spacing={2}>
      {actionErrorMessage && (
        <Alert severity="error" onClose={() => setActionErrorMessage(null)}>
          {actionErrorMessage}
        </Alert>
      )}

      {requestResult.bookmarksPage.results.map((bookmark) => (
        <Card key={bookmark.id} variant="outlined">
          <CardContent>
            <Typography variant="h6" component="h2">
              {bookmark.article_title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ marginTop: 0.5 }}>
              Saved {formatSavedDate(bookmark.created_at)}
            </Typography>
            {/* pre-wrap keeps the line breaks typed into the note */}
            <Typography
              variant="body1"
              color={bookmark.note ? 'text.primary' : 'text.secondary'}
              sx={{ marginTop: 1, whiteSpace: 'pre-wrap' }}
            >
              {bookmark.note || 'No note'}
            </Typography>
          </CardContent>
          <CardActions>
            <FormControlLabel
              label="Read"
              control={
                <Checkbox
                  checked={bookmark.is_read}
                  disabled={readSavingBookmarkIds.includes(bookmark.id)}
                  onChange={(event) => handleReadToggle(bookmark, event.target.checked)}
                />
              }
              sx={{ marginLeft: 0, marginRight: 'auto' }}
            />
            <Button onClick={() => setBookmarkBeingEdited(bookmark)}>Edit note</Button>
            <Button color="error" onClick={() => setBookmarkBeingRemoved(bookmark)}>
              Remove
            </Button>
          </CardActions>
        </Card>
      ))}

      {totalPages > 1 && (
        <Pagination
          count={totalPages}
          page={currentPage}
          onChange={handlePageChange}
          color="primary"
          sx={{ alignSelf: 'center', paddingTop: 1 }}
        />
      )}

      {bookmarkBeingEdited && (
        <BookmarkNoteDialog
          dialogTitle="Edit note"
          articleTitle={bookmarkBeingEdited.article_title}
          initialNote={bookmarkBeingEdited.note}
          saveButtonLabel="Save note"
          onCancel={() => setBookmarkBeingEdited(null)}
          onSave={handleNoteSave}
        />
      )}

      {/* Confirm step before a delete, since it can't be undone from the UI */}
      <Dialog
        open={bookmarkBeingRemoved !== null}
        onClose={isRemoving ? undefined : () => setBookmarkBeingRemoved(null)}
      >
        <DialogTitle>Remove saved article?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {bookmarkBeingRemoved?.article_title} and its note will be removed from your saved
            articles.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBookmarkBeingRemoved(null)} disabled={isRemoving}>
            Cancel
          </Button>
          <Button color="error" variant="contained" onClick={handleRemoveConfirm} disabled={isRemoving}>
            {isRemoving ? 'Removing…' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

export default SavedPage
