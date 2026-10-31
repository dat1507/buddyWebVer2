import { createContext } from 'react'

// Default keeps standalone carousel consumers and their existing timing unchanged.
const LandingMotionContext = createContext({ paused: false, toggle: () => {} })

export { LandingMotionContext }
