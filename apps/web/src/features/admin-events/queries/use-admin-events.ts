import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  adminEventsClient,
  type AdminEventListRequest,
  type EventCoverUploadInput,
  type EventDraftPayload,
  type EventStatusUpdateInput,
} from '@/features/admin-events/admin-events'

type AdminEventQueryRequest = Omit<AdminEventListRequest, 'signal'>

const adminEventKeys = {
  root: ['private', 'admin-events'] as const,
  list: (request: AdminEventQueryRequest) => ['private', 'admin-events', 'list', request] as const,
  detail: (eventId: string) => ['private', 'admin-events', 'detail', eventId] as const,
  cover: (eventId: string, mediaId: string) =>
    ['private', 'admin-events', 'cover', eventId, mediaId] as const,
}

function useAdminEvents(request: AdminEventQueryRequest) {
  return useQuery({
    queryKey: adminEventKeys.list(request),
    queryFn: ({ signal }) => adminEventsClient.readEvents({ ...request, signal }),
    meta: { private: true },
  })
}

function useAdminEventDetail(eventId: string | null) {
  return useQuery({
    queryKey: adminEventKeys.detail(eventId ?? 'none'),
    queryFn: ({ signal }) => adminEventsClient.readEvent(eventId!, signal),
    enabled: eventId !== null,
    meta: { private: true },
  })
}

function useAdminEventCover(eventId: string | null, mediaId: string | null) {
  return useQuery({
    queryKey: adminEventKeys.cover(eventId ?? 'none', mediaId ?? 'none'),
    queryFn: ({ signal }) => adminEventsClient.readCoverUrl(eventId!, mediaId!, signal),
    enabled: eventId !== null && mediaId !== null,
    meta: { private: true },
  })
}

async function invalidateEventQueries(client: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    client.invalidateQueries({ queryKey: adminEventKeys.root }),
    client.invalidateQueries({ queryKey: ['events'] }),
    client.invalidateQueries({ queryKey: ['event-sliders'] }),
  ])
}

function useCreateAdminEvent() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: EventDraftPayload) => adminEventsClient.createDraft(payload),
    onSuccess: async (event) => {
      client.setQueryData(adminEventKeys.detail(event.id), event)
      await invalidateEventQueries(client)
    },
  })
}

function useUpdateAdminEvent() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      eventId,
      payload,
    }: {
      eventId: string
      payload: EventDraftPayload & { version: number }
    }) => adminEventsClient.updateEvent(eventId, payload),
    onSuccess: async (event) => {
      client.setQueryData(adminEventKeys.detail(event.id), event)
      await invalidateEventQueries(client)
    },
  })
}

function useUploadAdminEventCover() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: EventCoverUploadInput) => adminEventsClient.uploadCover(input),
    onSuccess: async (result) => {
      client.setQueryData(adminEventKeys.detail(result.event.id), result.event)
      await invalidateEventQueries(client)
    },
  })
}

function useSetAdminEventStatus() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: EventStatusUpdateInput) => adminEventsClient.setStatus(input),
    onSuccess: async (event) => {
      client.setQueryData(adminEventKeys.detail(event.id), event)
      await invalidateEventQueries(client)
    },
  })
}

export {
  adminEventKeys,
  useAdminEventCover,
  useAdminEventDetail,
  useAdminEvents,
  useCreateAdminEvent,
  useSetAdminEventStatus,
  useUpdateAdminEvent,
  useUploadAdminEventCover,
}
