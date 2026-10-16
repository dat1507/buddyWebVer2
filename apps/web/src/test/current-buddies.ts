import type { CurrentBuddyList } from '@/features/matching/current-buddy'
import { recommendationList } from '@/test/recommendations'

const currentBuddyList: CurrentBuddyList = {
  items: [
    {
      match_id: 'aaaaaaaa-1111-4111-8111-111111111111',
      conversation_id: 'bbbbbbbb-1111-4111-8111-111111111111',
      buddy: {
        id: recommendationList.items[0].profile.id,
        display_name: recommendationList.items[0].profile.display_name,
        student_type: recommendationList.items[0].profile.student_type,
        major: recommendationList.items[0].profile.major,
        avatar: recommendationList.items[0].profile.avatar,
        interests: recommendationList.items[0].profile.interests,
        languages: recommendationList.items[0].profile.languages,
        activities: recommendationList.items[0].profile.activities,
        availability: recommendationList.items[0].profile.availability,
      },
      score: recommendationList.items[0].score,
      explanation: recommendationList.items[0].explanation,
      reference_week_start: '2026-09-21',
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
  total_pages: 1,
}

export { currentBuddyList }
