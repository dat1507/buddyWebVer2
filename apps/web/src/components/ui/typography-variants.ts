import { cva } from 'class-variance-authority'

export const typographyVariants = cva('', {
  variants: {
    variant: {
      h1: 'scroll-m-20 text-5xl font-black leading-[1.08] tracking-tight text-foreground lg:text-7xl',
      h2: 'scroll-m-20 text-4xl font-black leading-tight tracking-tight text-foreground lg:text-6xl',
      h3: 'scroll-m-20 text-2xl font-bold leading-tight tracking-tight text-foreground',
      h4: 'scroll-m-20 text-xl font-semibold leading-snug text-foreground',
      p: 'text-base leading-7 text-foreground',
      lead: 'text-xl leading-8 text-muted-foreground lg:text-2xl',
      muted: 'text-sm leading-6 text-muted-foreground',
      small: 'text-sm font-medium leading-none text-foreground',
    },
  },
  defaultVariants: {
    variant: 'p',
  },
})
