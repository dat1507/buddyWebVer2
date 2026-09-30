import type { IncomingInvitationList, SentInvitationList } from '@/features/matching/invitation'
import { recommendationList } from '@/test/recommendations'

const sender = {
  ...recommendationList.items[0].profile,
}

const recipient = {
  ...recommendationList.items[0].profile,
  id: '77777777-7777-4777-8777-777777777777',
  display_name: 'Alex',
  avatar: {
    ...recommendationList.items[0].profile.avatar,
    id: '88888888-8888-4888-8888-888888888888',
  },
}

const incomingInvitationList: IncomingInvitationList = {
  items: [
    {
      id: '11111111-aaaa-4111-8111-111111111111',
      status: 'PENDING',
      created_at: '2026-09-30T08:00:00Z',
      expires_at: '2026-10-07T08:00:00Z',
      score: recommendationList.items[0].score,
      explanation: recommendationList.items[0].explanation,
      sender,
      message: '<script>alert(1)</script>\nWould you like to meet on campus?',
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
  total_pages: 1,
  reference_week_start: '2026-09-21',
}

const sentInvitationList: SentInvitationList = {
  items: [
    {
      id: '22222222-aaaa-4222-8222-222222222222',
      status: 'PENDING',
      created_at: '2026-09-29T08:00:00Z',
      expires_at: '2026-10-06T08:00:00Z',
      score: recommendationList.items[0].score,
      explanation: recommendationList.items[0].explanation,
      recipient,
    },
    {
      id: '33333333-aaaa-4333-8333-333333333333',
      status: 'ACCEPTED',
      created_at: '2026-09-28T08:00:00Z',
      expires_at: '2026-10-05T08:00:00Z',
      score: null,
      explanation: null,
      recipient: {
        ...recipient,
        id: '99999999-9999-4999-8999-999999999999',
        display_name: 'Sam',
        avatar: null,
      },
    },
  ],
  page: 1,
  page_size: 20,
  total: 2,
  total_pages: 1,
  reference_week_start: '2026-09-21',
}

export { incomingInvitationList, sentInvitationList }
