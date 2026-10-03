function UnreadBadge({ count, label }: { count: number; label: string }) {
  if (count <= 0) return null
  return (
    <span
      aria-label={label}
      title={label}
      className="inline-flex min-w-5 shrink-0 items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-[0.65rem] font-bold leading-none text-white shadow-sm"
    >
      {count > 99 ? '99+' : count}
    </span>
  )
}

export { UnreadBadge }
