/**
 * About page: a short description of DevFeed and where its stories come from.
 */
import Link from '@mui/material/Link'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

function AboutPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        About DevFeed
      </Typography>
      <Typography>
        DevFeed is a personalized developer news digest. It collects stories from
        Hacker News and GitHub into one feed, so you can filter by tags, follow
        keywords, save articles with notes, and vote stories up or down.
      </Typography>
      <Typography>
        Built with React, Material UI, Django REST Framework, and PostgreSQL as a
        Code Platoon project.{' '}
        <Link
          href="https://github.com/BigZeeke/devfeed"
          target="_blank"
          rel="noopener noreferrer"
        >
          View the source on GitHub
        </Link>
        .
      </Typography>
    </Stack>
  )
}

export default AboutPage
