import { useId } from 'react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

interface NotFoundPageProps {
  embedded?: boolean
}

function NotFoundPage({ embedded = false }: NotFoundPageProps) {
  const titleId = useId()
  const Container = embedded ? 'section' : 'main'

  return (
    <Container
      aria-labelledby={titleId}
      className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center"
    >
      <Typography variant="small" className="uppercase tracking-[0.2em] text-vgu-orange">
        404
      </Typography>
      <Typography id={titleId} variant="h1">
        Page not found
      </Typography>
      <Button asChild variant="outline">
        <Link to="/">Back to home</Link>
      </Button>
    </Container>
  )
}

export { NotFoundPage }
