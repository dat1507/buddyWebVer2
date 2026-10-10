interface EventFeatureFlagEnvironment {
  adminEventsFlag?: string
  publicEventsFlag?: string
  legacyEventsFlag?: string
}

interface EventFeatureFlags {
  adminEventsEnabled: boolean
  publicEventsEnabled: boolean
}

function resolveEventFeatureFlags({
  adminEventsFlag,
  publicEventsFlag,
}: EventFeatureFlagEnvironment): EventFeatureFlags {
  return {
    adminEventsEnabled: adminEventsFlag === 'true',
    publicEventsEnabled: publicEventsFlag === 'true',
  }
}

// Event access is fail-safe: missing or invalid values stay off. The retired
// VITE_EVENTS_LAUNCH_ENABLED flag is intentionally ignored and cannot enable
// either surface.
const adminEventsEnabled = import.meta.env.VITE_ADMIN_EVENTS_ENABLED === 'true'
const publicEventsEnabled = import.meta.env.VITE_PUBLIC_EVENTS_ENABLED === 'true'

export { adminEventsEnabled, publicEventsEnabled, resolveEventFeatureFlags }
export type { EventFeatureFlagEnvironment, EventFeatureFlags }
