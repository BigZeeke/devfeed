/**
 * One article in the feed: title link, source, publish date, score, and tags.
 */
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Link from '@mui/material/Link'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

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

function ArticleCard({ article }) {
  return (
    <Card variant="outlined">
      <CardContent>
        {/* Opens the original story in a new tab; rel stops the new tab from controlling this one */}
        <Link
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          variant="h6"
          underline="hover"
        >
          {article.title}
        </Link>

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
    </Card>
  )
}

export default ArticleCard
