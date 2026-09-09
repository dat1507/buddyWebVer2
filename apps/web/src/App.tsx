import { ArrowRight } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

function App() {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,rgba(255,103,13,0.22),transparent_38%)] px-6 py-20 selection:bg-vgu-orange selection:text-vgu-black lg:px-8">
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="space-y-8" aria-labelledby="page-title">
          <Typography variant="small" className="uppercase tracking-[0.2em] text-vgu-orange">
            VGU Buddy Program
          </Typography>
          <div className="space-y-5">
            <Typography id="page-title" variant="h1">
              Connect with <span className="text-vgu-orange">VGU Buddy</span>
            </Typography>
            <Typography variant="lead" className="max-w-2xl">
              Join the Vietnamese-German University community. Build connections, share experiences,
              and thrive together.
            </Typography>
          </div>
          <div className="flex flex-col gap-4 sm:flex-row">
            <Button asChild size="lg">
              <a href="https://www.facebook.com/VGUBuddyProgram" target="_blank" rel="noreferrer">
                Join the community
                <ArrowRight aria-hidden="true" />
              </a>
            </Button>
            <Button asChild variant="outline" size="lg">
              <a href="#welcome">Learn more</a>
            </Button>
          </div>
        </section>

        <Card id="welcome" variant="interactive">
          <CardHeader>
            <div className="mb-3 flex size-14 items-center justify-center rounded-xl bg-vgu-orange text-2xl text-vgu-black">
              <span aria-hidden="true">🤝</span>
            </div>
            <CardTitle>Welcome to VGU Buddy</CardTitle>
            <CardDescription>
              Your gateway to university life with friends who care.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Typography variant="p" className="text-vgu-muted">
              Meet your buddy, explore campus, join events, and find reliable answers in one place.
            </Typography>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

export default App
