import { createContext, useContext } from 'react'

import type { ChatUnreadSummary } from '@/features/chat/chat'

interface BuddyUnreadContextValue {
  summary: ChatUnreadSummary
  isFetching: boolean
}

const EMPTY_UNREAD_SUMMARY: ChatUnreadSummary = {
  total_unread_messages: 0,
  conversations: [],
}

const BuddyUnreadContext = createContext<BuddyUnreadContextValue>({
  summary: EMPTY_UNREAD_SUMMARY,
  isFetching: false,
})

const buddyUnreadQueryKeys = {
  summary: (userId: string) => ['private', userId, 'chat', 'unread-summary'] as const,
}

function useBuddyUnread(): BuddyUnreadContextValue {
  return useContext(BuddyUnreadContext)
}

function unreadCountForConversation(summary: ChatUnreadSummary, conversationId: string): number {
  return (
    summary.conversations.find(({ conversation_id: id }) => id === conversationId)?.unread_count ??
    0
  )
}

export {
  BuddyUnreadContext,
  EMPTY_UNREAD_SUMMARY,
  buddyUnreadQueryKeys,
  unreadCountForConversation,
  useBuddyUnread,
}
