import type { Recommendation, RecommendationList } from '@/features/matching/recommendation'

const recommendation: Recommendation = {
  profile: {
    id: '11111111-1111-4111-8111-111111111111',
    display_name: 'Linh',
    student_type: 'VIETNAMESE',
    major: 'Computer Science',
    avatar: {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      width: 800,
      height: 800,
    },
    interests: [
      {
        id: '22222222-2222-4222-8222-222222222222',
        code: 'photography',
        label: 'Photography',
        is_custom: false,
      },
      { id: null, code: null, label: 'Formula 1', is_custom: true },
    ],
    languages: [
      { code: 'en', label: 'English', proficiency: 'fluent', is_custom: false },
      { code: null, label: 'Thai', proficiency: 'beginner', is_custom: true },
    ],
    activities: [
      {
        id: '33333333-3333-4333-8333-333333333333',
        code: 'coffee-chat',
        label: 'Coffee chat',
        is_custom: false,
      },
    ],
    availability: {
      timezone: 'Asia/Ho_Chi_Minh',
      slots: [{ weekday: 1, start_minute: 540, end_minute: 660 }],
    },
  },
  score: 87,
  explanation: {
    interests: { similarity: 0.75, weight: 40, points: 30 },
    activities: { similarity: 0.8, weight: 35, points: 28 },
    availability: { similarity: 0.8, weight: 15, points: 12 },
    languages: { similarity: 1, weight: 5, points: 5 },
    major: { similarity: 1, weight: 5, points: 5 },
  },
}

const recommendationList: RecommendationList = {
  items: [recommendation],
  page: 1,
  page_size: 20,
  total: 1,
  total_pages: 1,
  reference_week_start: '2026-09-21',
}

export { recommendation, recommendationList }
