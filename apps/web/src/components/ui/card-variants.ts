import { cva } from 'class-variance-authority'

export const cardVariants = cva('rounded-2xl border bg-card text-card-foreground shadow-sm', {
  variants: {
    variant: {
      default: 'border-border',
      interactive:
        'border-vgu-surface transition-[border-color,box-shadow,transform] duration-300 ease-out hover:border-vgu-orange hover:shadow-[0_20px_40px_rgba(255,103,13,0.16)] motion-safe:hover:-translate-y-1 motion-safe:hover:scale-[1.01] motion-reduce:transition-none',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})
