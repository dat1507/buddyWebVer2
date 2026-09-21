import type { OwnProfile } from '@/features/profile/profile'

const completeOwnProfile = Object.freeze<OwnProfile>({
  id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE',
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'I enjoy helping new students settle in.',
  home_university: null,
  arrival_date: null,
  departure_date: null,
  availability: {
    timezone: 'Asia/Ho_Chi_Minh',
    slots: [{ weekday: 1, start_minute: 540, end_minute: 600 }],
  },
  preferences: { preferred_activity_ids: ['cccccccc-cccc-4ccc-8ccc-cccccccccccc'] },
  matching_opt_in: true,
  avatar: {
    id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    mime_type: 'image/webp',
    byte_size: 24_680,
    width: 800,
    height: 800,
    processing_status: 'READY',
    created_at: '2026-09-20T08:00:00Z',
  },
  interest_ids: ['cccccccc-cccc-4ccc-8ccc-cccccccccccc'],
  languages: [{ language_code: 'en', proficiency: 'fluent' }],
  version: 4,
})

export { completeOwnProfile }
