/**
 * One article in the feed: title link, source, publish date, score, and tags.
 *
 * When the parent passes onSaveClick (only for logged-in users), the card
 * also shows a Save button that starts saving the article as a bookmark.
 */
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActions from '@mui/material/CardActions'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Link from '@mui/material/Link'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder'

// Article URLs come from third-party APIs, so only normal web addresses
// become links. Anything else (for example "javascript:...") could run code.
const SAFE_LINK_PROTOCOLS = ['http:', 'https:']

// Returns the URL to link to, or null if the article's URL is not safe to link.
function getSafeLinkUrl(articleUrl) {
  try {
    const parsedUrl = new URL(articleUrl)
    // Link to the parsed href, so the link uses exactly the URL that was checked.
    return SAFE_LINK_PROTOCOLS.includes(parsedUrl.protocol) ? parsedUrl.href : null
  } catch {
    // new URL() throws for missing, relative, or malformed URLs.
    return null
  }
}

// Formats an ISO timestamp like "2026-10-30T14:05:00Z" as "Oct 30, 2026"
// in the reader's locale. published_at can be null, so that case is handled.
function formatPublishedDate(publishedAt) {
  if (!publishedAt) {
    return 'Date unknown'
  }
  return new Date(publishedAt).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function ArticleCard({ article, onSaveClick }) {
  const safeLinkUrl = getSafeLinkUrl(article.url)

  return (
    <Card variant="outlined">
      <CardContent>
        {safeLinkUrl ? (
          // Opens the original story in a new tab; rel stops the new tab from controlling this one
          <Link
            href={safeLinkUrl}
            target="_blank"
            rel="noopener noreferrer"
            variant="h6"
            underline="hover"
          >
            {article.title}
          </Link>
        ) : (
          // Unsafe or invalid URL: show the title as plain text, with nothing to click
          <Typography variant="h6" component="span">
            {article.title}
          </Typography>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ marginTop: 0.5 }}>
          {article.source_name} · {formatPublishedDate(article.published_at)} · score{' '}
          {article.raw_score}
        </Typography>

        {article.tags.length > 0 && (
          <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap', marginTop: 1 }}>
            {article.tags.map((tag) => (
              <Chip key={tag.id} label={tag.label} size="small" />
            ))}
          </Stack>
        )}
      </CardContent>

      {onSaveClick && (
        <CardActions sx={{ paddingTop: 0 }}>
          <Button
            size="small"
            startIcon={<BookmarkBorderIcon />}
            onClick={() => onSaveClick(article)}
            // The visible text is just "Save"; screen readers also hear which article.
            aria-label={`Save ${article.title}`}
          >
            Save
          </Button>
        </CardActions>
      )}
    </Card>
  )
}

export default ArticleCard
