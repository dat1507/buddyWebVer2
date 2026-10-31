import type { LucideIcon } from 'lucide-react'

interface ProfileSectionHeadingProps {
  id: string
  title: string
  description: string
  eyebrow: string
  Icon: LucideIcon
  editing: boolean
}

function ProfileSectionHeading({
  id,
  title,
  description,
  eyebrow,
  Icon,
  editing,
}: ProfileSectionHeadingProps) {
  const Heading = editing ? 'h2' : 'h1'

  return (
    <header className="flex items-start gap-4">
      <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <div className="min-w-0 space-y-2">
        <p className="text-sm font-medium text-muted-foreground">{eyebrow}</p>
        <Heading
          id={id}
          tabIndex={-1}
          className="max-w-2xl text-balance text-2xl font-bold leading-tight tracking-tight sm:text-3xl"
        >
          {title}
        </Heading>
        <p className="max-w-2xl text-base leading-7 text-muted-foreground">{description}</p>
      </div>
    </header>
  )
}

export { ProfileSectionHeading }
