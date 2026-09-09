import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <Typography variant="small" className="uppercase tracking-[0.2em] text-vgu-orange">
        404
      </Typography>
      <Typography variant="h1">Page not found</Typography>
      <Button asChild variant="outline">
        <Link to="/">Back to home</Link>
      </Button>
    </main>
  )
}

export { NotFoundPage }
