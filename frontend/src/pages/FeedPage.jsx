/**
 * Feed page: one page of articles from /api/articles/.
 *
 * The page number lives in the URL (?page=2), so Back/Forward and shared
 * links work. Shows a spinner while loading and an alert if the request fails.
 * Logged-in users can save an article as a bookmark, with an optional note.
 */
import { useEffect, useState } from 'react'
import { Link as RouterLink, useSearchParams } from 'react-router'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Pagination from '@mui/material/Pagination'
import Snackbar from '@mui/material/Snackbar'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import { ApiError, ARTICLES_PAGE_SIZE, createBookmark, fetchArticlesPage } from '../api.js'
import { useAuth } from '../auth/useAuth.js'
import ArticleCard from '../components/ArticleCard.jsx'
import BookmarkNoteDialog from '../components/BookmarkNoteDialog.jsx'

// Shown instead of DRF's "The fields user, article must make a unique set."
const ALREADY_SAVED_MESSAGE =
  'You already saved this article. You can edit its note on your Saved page.'

// Reads ?page= from the URL; anything missing or invalid means page 1.
function parsePageNumber(pageParameter) {
  const pageNumber = Number.parseInt(pageParameter, 10)
  return Number.isInteger(pageNumber) && pageNumber > 0 ? pageNumber : 1
}

// Turns a failed request into a message a reader can act on.
function describeRequestError(error) {
  if (error instanceof ApiError) {
    // DRF answers 404 when the page number is past the last page.
    if (error.status === 404) {
      return 'That page of the feed does not exist.'
    }
    return `Could not load articles. ${error.message}`
  }
  // fetch() itself failed: server down, wrong address, or CORS refused.
  return 'Could not reach the DevFeed API. Is the backend running?'
}

function FeedPage() {
  const { isLoggedIn } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const currentPage = parsePageNumber(searchParams.get('page'))

  // The result of the most recent finished request, tagged with the page it
  // was for. Loading is derived below instead of stored, so the effect only
  // sets state after the request finishes.
  const [requestResult, setRequestResult] = useState({
    pageNumber: null,
    articlesPage: null,
    errorMessage: null,
  })

  // The article whose Save dialog is open, and the title of the last article
  // saved (shown in a short confirmation message), or null.
  const [articleBeingSaved, setArticleBeingSaved] = useState(null)
  const [lastSavedTitle, setLastSavedTitle] = useState(null)

  useEffect(() => {
    // Cancels the request if the page changes or the component unmounts,
    // so a slow old response can't overwrite a newer one.
    const abortController = new AbortController()

    fetchArticlesPage(currentPage, { signal: abortController.signal })
      .then((articlesPage) => {
        setRequestResult({ pageNumber: currentPage, articlesPage, errorMessage: null })
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          return
        }
        setRequestResult({
          pageNumber: currentPage,
          articlesPage: null,
          errorMessage: describeRequestError(error),
        })
      })

    return () => abortController.abort()
  }, [currentPage])

  // Still loading until a result for the current page has arrived.
  const isLoading = requestResult.pageNumber !== currentPage

  // Called by the note dialog; errors are thrown back so the dialog shows them.
  async function handleBookmarkSave(note) {
    try {
      await createBookmark({ articleId: articleBeingSaved.id, note })
    } catch (error) {
      // The only non-field error the bookmark API returns is the duplicate
      // check (same user and article), so swap in a clearer message.
      if (error instanceof ApiError && error.status === 400 && error.responseBody?.non_field_errors) {
        throw new ApiError(error.status, error.message, { non_field_errors: [ALREADY_SAVED_MESSAGE] })
      }
      throw error
    }
    setLastSavedTitle(articleBeingSaved.title)
    setArticleBeingSaved(null)
  }

  function handlePageChange(event, newPageNumber) {
    // Page 1 is the plain feed URL; other pages add ?page=N.
    setSearchParams(newPageNumber === 1 ? {} : { page: String(newPageNumber) })
    window.scrollTo({ top: 0 })
  }

  let pageContent
  if (isLoading) {
    pageContent = (
      <Box sx={{ display: 'flex', justifyContent: 'center', paddingY: 6 }}>
        <CircularProgress aria-label="Loading articles" />
      </Box>
    )
  } else if (requestResult.errorMessage) {
    pageContent = <Alert severity="error">{requestResult.errorMessage}</Alert>
  } else if (requestResult.articlesPage.results.length === 0) {
    pageContent = (
      <Alert severity="info">No articles yet. Run the ingestion commands to load stories.</Alert>
    )
  } else {
    const totalPages = Math.ceil(requestResult.articlesPage.count / ARTICLES_PAGE_SIZE)
    pageContent = (
      <Stack spacing={2}>
        {requestResult.articlesPage.results.map((article) => (
          <ArticleCard
            key={article.id}
            article={article}
            // Only logged-in users get a Save button; the API needs a token.
            onSaveClick={isLoggedIn ? setArticleBeingSaved : undefined}
          />
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
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        Latest stories
      </Typography>
      {pageContent}

      {articleBeingSaved && (
        <BookmarkNoteDialog
          dialogTitle="Save article"
          articleTitle={articleBeingSaved.title}
          saveButtonLabel="Save"
          onCancel={() => setArticleBeingSaved(null)}
          onSave={handleBookmarkSave}
        />
      )}

      {/* Short confirmation after a save, with a shortcut to the Saved page */}
      <Snackbar
        open={lastSavedTitle !== null}
        autoHideDuration={5000}
        onClose={(event, closeReason) => {
          // A click elsewhere on the page shouldn't hide it early.
          if (closeReason !== 'clickaway') {
            setLastSavedTitle(null)
          }
        }}
      >
        <Alert
          severity="success"
          variant="filled"
          onClose={() => setLastSavedTitle(null)}
          action={
            <Button component={RouterLink} to="/saved" color="inherit" size="small">
              View saved
            </Button>
          }
        >
          Saved "{lastSavedTitle}".
        </Alert>
      </Snackbar>
    </Stack>
  )
}

export default FeedPage
