import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'

interface RoutePlaceholderProps {
  area: 'Public' | 'User' | 'Admin'
  title: string
}

function RoutePlaceholder({ area, title }: RoutePlaceholderProps) {
  // Private layouts own the main landmark; a standalone public page keeps its own.
  const Container = area === 'Public' ? 'main' : 'div'

  return (
    <Container
      className={cn(
        'flex items-center justify-center',
        area === 'Public' ? 'min-h-screen px-6 py-16' : 'py-6',
      )}
    >
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
    </Container>
  )
}

export { RoutePlaceholder }
