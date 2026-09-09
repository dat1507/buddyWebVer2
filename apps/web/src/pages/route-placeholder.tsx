import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

interface RoutePlaceholderProps {
  area: 'Public' | 'User' | 'Admin'
  title: string
}

function RoutePlaceholder({ area, title }: RoutePlaceholderProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <Typography variant="small" className="uppercase tracking-[0.2em] text-vgu-orange">
            {area}
          </Typography>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <Typography variant="muted">This area is not available yet.</Typography>
          <Button asChild variant="outline">
            <Link to="/">Back to home</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}

export { RoutePlaceholder }
