interface LaunchScopeEnvironment {
  development: boolean
  eventsFlag?: string
}

function resolveEventsLaunchEnabled({ development, eventsFlag }: LaunchScopeEnvironment): boolean {
  if (eventsFlag === 'true') return true
  if (eventsFlag === 'false') return false
  return development
}

const eventsLaunchEnabled = resolveEventsLaunchEnabled({
  development: import.meta.env.DEV,
  eventsFlag: import.meta.env.VITE_EVENTS_LAUNCH_ENABLED,
})

export { eventsLaunchEnabled, resolveEventsLaunchEnabled }
