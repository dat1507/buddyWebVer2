import { cva } from 'class-variance-authority'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-[color,background-color,border-color,box-shadow,transform] duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 motion-reduce:transition-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-br from-vgu-orange to-vgu-orange-dark text-vgu-black shadow-[0_4px_15px_rgba(255,103,13,0.3)] hover:shadow-[0_8px_25px_rgba(255,103,13,0.4)] motion-safe:hover:-translate-y-0.5 active:translate-y-0',
        destructive: 'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90',
        outline:
          'border-2 border-vgu-orange bg-transparent text-vgu-orange hover:bg-vgu-orange hover:text-vgu-black motion-safe:hover:-translate-y-0.5 active:translate-y-0',
        secondary:
          'border border-border bg-secondary text-secondary-foreground shadow-sm hover:border-vgu-orange/70 hover:bg-secondary/80',
        ghost: 'text-foreground hover:bg-accent/15 hover:text-vgu-orange',
        link: 'h-auto rounded-none p-0 text-vgu-orange underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-5 py-2',
        sm: 'h-9 rounded-lg px-3 text-sm',
        lg: 'h-12 px-8 text-base',
        icon: 'size-10 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)
