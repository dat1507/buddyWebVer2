import { useEffect, type RefObject } from 'react'

interface IsolatedElementState {
  element: HTMLElement
  inert: string | null
  ariaHidden: string | null
}

/**
 * Removes content outside an active modal from keyboard and accessibility-tree
 * navigation, then restores every affected element to its previous state.
 */
function useModalIsolation(containerRef: RefObject<HTMLElement | null>, active = true) {
  useEffect(() => {
    const container = containerRef.current
    if (!active || !container) return

    const isolatedElements: IsolatedElementState[] = []
    let currentElement: HTMLElement = container

    while (currentElement.parentElement) {
      const parentElement = currentElement.parentElement

      for (const sibling of parentElement.children) {
        if (sibling === currentElement || !(sibling instanceof HTMLElement)) continue

        isolatedElements.push({
          element: sibling,
          inert: sibling.getAttribute('inert'),
          ariaHidden: sibling.getAttribute('aria-hidden'),
        })
        sibling.setAttribute('inert', '')
        sibling.setAttribute('aria-hidden', 'true')
      }

      if (parentElement === document.body) break
      currentElement = parentElement
    }

    return () => {
      for (const { element, inert, ariaHidden } of isolatedElements) {
        if (inert === null) {
          element.removeAttribute('inert')
        } else {
          element.setAttribute('inert', inert)
        }

        if (ariaHidden === null) {
          element.removeAttribute('aria-hidden')
        } else {
          element.setAttribute('aria-hidden', ariaHidden)
        }
      }
    }
  }, [active, containerRef])
}

export { useModalIsolation }
