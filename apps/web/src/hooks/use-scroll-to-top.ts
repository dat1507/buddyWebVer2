import { useEffect } from 'react'
import { useLocation } from 'react-router'

/**
 * Scrolls to the top of the page on every route change.
 *
 * Place this hook once inside the router tree (e.g. in a layout component)
 * so every descendant route benefits automatically.
 */
function useScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
}

export { useScrollToTop }
