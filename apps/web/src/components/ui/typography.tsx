import * as React from 'react'
import { type VariantProps } from 'class-variance-authority'

import { typographyVariants } from '@/components/ui/typography-variants'
import { cn } from '@/lib/utils'

type TypographyVariant = NonNullable<VariantProps<typeof typographyVariants>['variant']>

const defaultElements: Record<TypographyVariant, React.ElementType> = {
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
  h4: 'h4',
  p: 'p',
  lead: 'p',
  muted: 'p',
  small: 'span',
}

export interface TypographyProps
  extends React.HTMLAttributes<HTMLElement>, VariantProps<typeof typographyVariants> {
  as?: React.ElementType
}

function Typography({ as, className, variant = 'p', ...props }: TypographyProps) {
  const Component = as ?? defaultElements[variant ?? 'p']

  return <Component className={cn(typographyVariants({ variant, className }))} {...props} />
}

export { Typography }
