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

// This gate controls only future API-backed User/Admin Event surfaces. The
// current-launch static Landing carousel is intentionally independent of it.
const dynamicEventsLaunchEnabled = resolveDynamicEventsLaunchEnabled({
  development: import.meta.env.DEV,
  eventsFlag: import.meta.env.VITE_EVENTS_LAUNCH_ENABLED,
})

export { dynamicEventsLaunchEnabled, resolveDynamicEventsLaunchEnabled }
