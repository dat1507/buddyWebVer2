interface DynamicEventsLaunchScopeEnvironment {
  development: boolean
  eventsFlag?: string
}

function resolveDynamicEventsLaunchEnabled({
  development,
  eventsFlag,
}: DynamicEventsLaunchScopeEnvironment): boolean {
  if (eventsFlag === 'true') return true
  if (eventsFlag === 'false') return false
  return development
}

// This gate keeps the API-backed Event surfaces, including the live Landing
// carousel, out of Production until the explicit staging/launch acceptance.
const eventsLaunchFlag = import.meta.env.VITE_EVENTS_LAUNCH_ENABLED
const dynamicEventsLaunchEnabled =
  eventsLaunchFlag === 'true' || (eventsLaunchFlag !== 'false' && import.meta.env.DEV)

export { dynamicEventsLaunchEnabled, resolveDynamicEventsLaunchEnabled }
