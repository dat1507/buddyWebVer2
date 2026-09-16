# FEATURE & IMPLEMENTATION PLAN AUDIT

Ngày audit: **12/09/2026**. Project hiện tại: `C:/Users/phuoc/Downloads/buddyWebVer2`; HEAD `fced9f33413aef4dd2c794cce16701bc17fe1440`. Legacy: `C:/Users/phuoc/Downloads/VGU_Buddy_Website/VGU_Buddy_Website/main`.

**Kết luận:** Plan cũ hỗ trợ **PARTIALLY**. Plan v2.2 đã bổ sung thiết kế và task đủ để tiếp tục **Backend Foundation — BE-001**. Đây là audit/tài liệu; chưa triển khai feature, database, service hay migration.

Phạm vi đã đọc: toàn bộ implementation plan, root/package README, CONTRIBUTING, docs audit/presentation; entrypoint/router/layouts; cả ba auth pages; toàn bộ luồng Event Slider từ component → query → repository → parser/client/mock; Benefits và Landing composition; legacy Calendar HTML/JS và article/gallery International Day. Không lấy tên route, folder rỗng, lời giới thiệu tính năng hay plan tương lai làm bằng chứng đã implement.

GitHub URL đã được đối chiếu với nhận diện repo local; web tool không đọc được trang repo nên không giả định remote/deployed version trùng local. Audit này dựa trên local source. Các README/docs đang thay đổi trước audit được giữ nguyên.

## 1. User Profile / Buddy System

Status bên dưới đánh giá **mức bao phủ của plan trước khi sửa**. Cột source phân biệt code thực tế: EXISTING = luồng đầy đủ, PARTIAL = chỉ có một phần/scaffold, MISSING = không có implementation. Sau audit, task bổ sung vẫn là PLANNED, không phải tính năng đã chạy.

| Feature | Existing | Partial | Missing | Source hiện tại | Notes |
|---------|---------:|--------:|--------:|----------------|-------|
| User Dashboard |  | ✓ |  | PARTIAL | FE-021..024 có shell/quick links; source chỉ có route placeholder, thiếu dashboard dùng profile và routing readiness. |
| User Profile |  | ✓ |  | MISSING | BE-008..013 + FE-025..029 có sẵn, nhưng StudentProfile/BuddyProfile trùng dữ liệu và chưa có social-style DTO/privacy đầy đủ. |
| Profile Photo |  |  | ✓ | MISSING | Chưa có photo entity, avatar UI hay private upload; storage cũ chỉ dành cho slider. |
| Interests |  | ✓ |  | MISSING | USER_INTEREST là chuỗi category/interest; có Step 2 nhưng thiếu catalog mở rộng và API contract. |
| Languages |  | ✓ |  | MISSING | USER_LANGUAGE có proficiency; thiếu catalog/API implementation. EN/DE i18n của website không phải ngôn ngữ profile. |
| Student Type |  | ✓ |  | MISSING | student_type=exchange/local mới xuất hiện trên StudentProfile, không nhất quán hai profile và chưa ràng buộc hai nhóm. |
| Profile Onboarding |  | ✓ |  | MISSING | FE-025..027 đã chia ba bước; thiếu save/resume, ảnh, routing sau auth và điều kiện Finish. |
| Profile Completion |  |  | ✓ | MISSING | Không có rule, DTO, missing-field reasons hoặc authority phía backend. |
| Matching Eligibility |  | ✓ |  | MISSING | MATCH-007 mới là constraint service chung; chưa gắn completion/opt-in/active/reservation. |
| Vietnamese ↔ International constraint |  |  | ✓ | MISSING | Persona nói local/exchange nhưng không có hard rule bắt buộc, kể cả manual override. |
| Profile-based Matching |  | ✓ |  | MISSING | Có weights/algorithm nhưng thiếu pipeline profile → eligibility → candidates; constraints đặt cả sau thuật toán. |

Thiết kế đã bổ sung:

- Một `StudentProfile` cho mọi USER; `student_type=VIETNAMESE/INTERNATIONAL` tách hoàn toàn khỏi `role=USER/ADMIN`. Nationality không tự quyết định nhóm ghép. Không thu thập gender trong MVP.
- Profile hỗ trợ full/display name, avatar, bio, major, study year, nationality, language/proficiency, interest/hobby catalog, availability và activity preferences. Một avatar trong MVP; model cho phép mở rộng photo sau này.
- COMPLETE cần **5 nhóm**: tên, student type, avatar hợp lệ, ít nhất một interest, ít nhất một language. Phần trăm được derive; client không được tự gửi `complete=true`. Matching còn cần opt-in, account active và chưa được giữ chỗ trong một pair.
- Matching chỉ tạo tập cặp **VIETNAMESE × INTERNATIONAL**, rồi mới tính score và greedy. Publish/accept/manual override đều kiểm tra lại; không có quyền Admin nào bỏ qua hard constraint. Profile type không được đổi khi đang có pair reserved/live.
- Thay vì thêm hệ thống AI ngay, dùng score có giải thích từ catalog/profile thực: interests 40%, languages 25%, availability 15%, major 10%, activities 10%; thiếu trường optional thì chuẩn hóa lại trọng số. Đây là giá trị khởi đầu để đánh giá, không phải xác suất tương thích đã được chứng minh.
- Profile và ảnh là private; chỉ owner/coordinator có quyền tương ứng và buddy trong match hợp lệ được đọc safe card. Không public email, contact, raw preferences, lịch chi tiết hay credentials.

Bằng chứng source: [App.tsx](../apps/web/src/App.tsx), [UserLayout](../apps/web/src/components/layout/user-layout.tsx), [AdminLayout](../apps/web/src/components/layout/admin-layout.tsx), [placeholder](../apps/web/src/pages/route-placeholder.tsx), [login](../apps/web/src/pages/public/user-login-page.tsx), [register](../apps/web/src/pages/public/user-registration-page.tsx), [admin login](../apps/web/src/pages/public/admin-login-page.tsx). Các form chỉ bật thông báo backend-pending; không tạo session, account hay role redirect.

## 2. Event Management

| Feature | Existing | Partial | Missing | Source hiện tại | Notes |
|---------|---------:|--------:|--------:|----------------|-------|
| Event Entity |  | ✓ |  | MISSING | EVENT/EVT-001..003 đã có; thiếu visibility/registration URL, timezone contract, media metadata và status tách bạch. |
| Admin Event Management |  | ✓ |  | PARTIAL | EVT-006 + ADMIN-006..011 có CRUD/form, nhưng upload chưa có backend, API list/detail và dependencies chưa đầy đủ; source chỉ placeholder. |
| Upcoming Events |  | ✓ |  | PARTIAL | Có timestamp trong plan và slider frontend, nhưng fixtures không có lịch live; published-only mâu thuẫn các trạng thái registration/complete. |
| Event Recaps |  |  | ✓ | MISSING | Chưa có recap model, draft/publish API hay admin editor; legacy article là reference. |
| Event Media Upload |  | ✓ |  | MISSING | Admin Create Event có nhắc image upload; EVS-003 chỉ thiết kế bucket slider, thiếu ownership/lifecycle của Event/Recap. |
| Event Slider API Integration | ✓ |  |  | PARTIAL | FE-014, EVS-001..007, ADMIN-SLIDER-001..004, FE-014B đã cover luồng cơ bản đầy đủ; source mới có adapter/mock/query, chưa có server. |
| Event Calendar Backend |  | ✓ |  | MISSING | Có Event list API dự kiến; thiếu overlap range, timezone, pagination và public/member permissions rõ ràng. |
| Event Calendar Frontend |  |  | ✓ | MISSING | Rebuild chưa có Calendar route/UI; benefit card chỉ thông tin. Legacy là danh sách HTML tĩnh, không phải calendar tháng đã migrate. |

Chọn **Event + EventRecap riêng, quan hệ 1:0..1**: thời gian/nội dung sự kiện giữ ở Event; recap có draft/publish và nội dung sau sự kiện riêng. `EventMedia` thuộc Event, giữ bucket/key/type/size/dimensions/alt/order. Cách này đủ gọn cho 100–150 users và tránh trộn lifecycle của sự kiện với lifecycle bài recap.

`status=DRAFT/PUBLISHED/CANCELLED` do Admin quản lý; `phase=UPCOMING/ONGOING/COMPLETED` derive từ UTC start/end. Visibility `PUBLIC/MEMBERS`; registration là chính sách riêng, không chen vào status. Location dùng text, không chờ Campus module. Calendar backend tái sử dụng `GET /api/events` có overlap range; UI Calendar để Phase 12B/P1.

Giữ `/api/event-sliders` và wire format snake_case mà frontend đã dùng. Slide liên kết Event lấy title/date/location từ Event, nên thay đổi sự kiện không cần sửa thêm bản sao dữ liệu. Poster/thứ tự/publish window vẫn thuộc promotion. Event bị ẩn/hủy không tiếp tục được quảng bá; xóa Event hợp lệ giữ slide nhưng chuyển DRAFT và bỏ CTA. Public client thấy cập nhật ở lần refetch thành công tiếp theo, mục tiêu trong 60 giây; không phải push tức thời.

Giữ Supabase Storage đã chọn. Profile và Event/Recap dùng bucket private; bucket slider public hiện có chỉ chứa poster quảng bá không nhạy cảm. Tách này cần thiết vì public bucket không bảo vệ lượt đọc theo quyền; private media có thể cấp URL hết hạn sau khi API kiểm tra quyền. [Supabase Storage](https://supabase.com/docs/guides/storage/buckets/fundamentals)

Bằng chứng source: [Event schema/parser](../apps/web/src/features/events/event-slider.ts), [API adapter](../apps/web/src/features/events/repositories/api-event-slider-repository.ts), [provider chọn mock](../apps/web/src/features/events/repositories/event-slider-repository-provider.ts), [mock posters](../apps/web/src/features/events/mocks/mock-event-slider-repository.ts), [query](../apps/web/src/features/events/queries/use-event-sliders.ts), [cache defaults](../apps/web/src/lib/query-client.ts), [carousel](../apps/web/src/components/landing/events-slider.tsx), [Benefits](../apps/web/src/components/landing/benefits-grid.tsx).

## 3. Implementation Plan Changes

**Existing tasks updated: 56.** Không đổi ID hoặc trạng thái của task completed; bổ sung đủ Goal/Dependencies/Scope/Acceptance Criteria/Out of Scope cho các task đang chờ.

`BE-004`, `EVS-003`, `AUTH-021`, `FE-022`, `FE-023`, `FE-024`, `BE-008`, `BE-009`, `BE-010`, `BE-011`, `BE-012`, `BE-013`, `FE-025`, `FE-026`, `FE-027`, `FE-028`, `FE-029`, `EVT-001`, `EVT-004`, `EVT-005`, `EVT-006`, `EVT-008`, `EVT-009`, `ADMIN-006`, `ADMIN-007`, `ADMIN-008`, `ADMIN-009`, `ADMIN-010`, `FE-030`, `FE-031`, `FE-014B`, `EVS-004`, `MATCH-001`, `MATCH-007`, `MATCH-003`, `MATCH-004`, `MATCH-005`, `MATCH-006`, `MATCH-008`, `MATCH-009`, `MATCH-010`, `FE-033`, `FE-034`, `FE-035`, `FE-037`, `ADMIN-015`, `ADMIN-016`, `ADMIN-017`, `ADMIN-018`, `ADMIN-014`, `AUTH-017`, `AUTH-016`, `EVT-003`, `EVS-002`, `FE-036`, `ADMIN-011`.

**New tasks added: 16.**

`AUTH-024`, `AUTH-025`, `BE-014`, `BE-015`, `BE-016`, `FE-038`, `FE-039`, `EVT-010`, `EVT-011`, `EVT-012`, `EVT-013`, `ADMIN-EVT-001`, `ADMIN-EVT-002`, `FE-EVENT-CALENDAR-001`, `MATCH-013`, `MATCH-014`.

**Tasks moved / reordered:**

- `EVS-003`: từ Phase 10A sang phần storage dùng chung ở Phase 8, trước profile/event upload; giữ ID và provider.
- `MATCH-005/006`: từ Matching Backend sang Phase 16/P2 research; greedy là MVP.
- `FE-023`: vẫn thuộc Dashboard Phase 6 nhưng thực thi sau profile/readiness/onboarding. `FE-024` + password-change endpoint là P1; logout vẫn P0 trong auth client/layout flow.
- `EVT-008`: giữ Phase 10, kéo sớm trong execution order vì là audit dùng chung; `MATCH-007` chạy trước `MATCH-003/004`.
- `FE-031`: tách khỏi phụ thuộc Event List để có public detail/recap destination trong MVP; `FE-014B` chờ live backend, admin flow và detail route. `FE-EVENT-CALENDAR-001` chạy sau core flow.

**Dependencies changed:** bảng mục 4 ghi chính xác từng task. Các sửa quan trọng gồm EventMedia model trước migration Event, Event migration trước slider FK, `/auth/me` sau `require_auth`, API upload trước form upload, completion trước onboarding gate, filtering trước scoring, publish/override trước own-match API, và feedback/registration UI sau API tương ứng.

Không tạo lại Profile CRUD, multi-step form, constraint service, carousel hay Event Calendar backend mới khi đã có task thích hợp. Hai endpoint logout/change-password trước đây có trong permission matrix nhưng không có task riêng nay được gán owner để Settings và admin wrong-role flow có dependency thực.

Kiến trúc/roadmap được cập nhật tại Parts 1, 4–8, 11, 15–16, 19–22, 24–25. Parts 18/18A chứa lịch sử completed được giữ nguyên nội dung. Các ước lượng cũ ~165 tasks/~327 giờ được đánh dấu historical, không dùng làm forecast mới. Shorthand RAG từng tái dùng FE-035..037 được bỏ alias; RAG/notifications/campus vẫn là hướng tương lai, cần task contracts riêng trước triển khai.

## 4. New / Updated Tasks

Mỗi dòng dưới đây có contract đầy đủ trong **Part 25 của [Implementation Plan v2.2](../implementation_plan_vgu_buddy.md#part-25--profile-matching-and-event-task-contracts-v22)**. P0=MUST HAVE, P1=SHOULD HAVE, P2=LATER. Mới/Cập nhật chỉ nói thay đổi tài liệu, không nói completion của code.

| Task | Description | Depends On | Priority | Phase |
|------|-------------|------------|----------|-------|
| `BE-004` | Cập nhật — Configure Supabase PostgreSQL connection and database access boundary | BE-003 | P0 | 2 |
| `AUTH-017` | Cập nhật — Create verified-current-user authentication dependency | AUTH-011, AUTH-009 | P0 | 5 |
| `AUTH-016` | Cập nhật — Create sanitized current-session endpoint | AUTH-017 | P0 | 5 |
| `AUTH-024` | Mới — Implement session logout endpoint | AUTH-015, AUTH-017, AUTH-011A | P0 | 5 |
| `AUTH-021` | Cập nhật — Connect session client, registration, and auth bootstrap | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 | 5 |
| `FE-022` | Cập nhật — Create User Sidebar navigation | FE-021 | P0 | 6 |
| `EVT-008` | Cập nhật — Create audit log model, migration and service | AUTH-009 | P0 | 10 |
| `EVS-003` | Cập nhật — Create shared Supabase image storage service and bucket policies | BE-004, AUTH-018, AUTH-011A | P0 | 8 |
| `BE-008` | Cập nhật — Define unified StudentProfile and ProfilePhoto models | AUTH-008 | P0 | 8 |
| `BE-009` | Cập nhật — Define Interest catalog and profile interest/language relations | BE-008 | P0 | 8 |
| `BE-010` | Cập nhật — Create profile, catalog and photo migrations | BE-008, BE-009, AUTH-009, BE-004 | P0 | 8 |
| `BE-011` | Cập nhật — Create own-profile persistence service | BE-010 | P0 | 8 |
| `BE-012` | Cập nhật — Create own-profile read/update endpoints | BE-011, AUTH-017, AUTH-011A | P0 | 8 |
| `BE-013` | Cập nhật — Create authorized admin user list and detail reads | BE-011, AUTH-018, EVT-008 | P0 | 8 |
| `BE-014` | Mới — Implement own profile photo upload and removal | BE-010, BE-012, EVS-003 | P0 | 8 |
| `BE-015` | Mới — Implement profile interest and language catalog APIs | BE-009, BE-012 | P0 | 8 |
| `BE-016` | Mới — Implement profile completion and matching eligibility read model | BE-012, BE-014, BE-015 | P0 | 8 |
| `FE-025` | Cập nhật — Create onboarding Step 1: identity and student type | FE-021, BE-012 | P0 | 9 |
| `FE-026` | Cập nhật — Create onboarding Step 2: interests and languages | FE-025, BE-015 | P0 | 9 |
| `FE-028` | Cập nhật — Create own social-style profile view | FE-025, BE-012, BE-014, BE-015 | P0 | 9 |
| `FE-039` | Mới — Create reusable profile avatar upload control | FE-025, BE-014 | P0 | 9 |
| `FE-027` | Cập nhật — Create onboarding Step 3: availability and preferences | FE-026, BE-012, BE-016, FE-039 | P0 | 9 |
| `FE-029` | Cập nhật — Create profile edit page using onboarding field components | FE-028, FE-027, BE-016 | P0 | 9 |
| `FE-038` | Mới — Integrate onboarding routing and readiness gate | AUTH-022, AUTH-023, BE-016, FE-027 | P0 | 9 |
| `FE-023` | Cập nhật — Create profile-aware User Dashboard home | FE-021, FE-022, BE-012, BE-016, FE-038 | P0 | 6 |
| `EVT-001` | Cập nhật — Define Event editorial state, time and visibility model | BE-006, AUTH-008 | P0 | 10 |
| `EVT-010` | Mới — Define EventMedia ownership model | EVT-001 | P0 | 10 |
| `EVT-003` | Cập nhật — Create Event, EventMedia and registration migrations | EVT-001, EVT-002, EVT-010, AUTH-009, BE-004 | P0 | 10 |
| `EVT-004` | Cập nhật — Create event CRUD and publication service | EVT-003 | P0 | 10 |
| `EVT-005` | Cập nhật — Create audience-safe event list, detail and calendar queries | EVT-004, AUTH-017 | P0 | 10 |
| `EVT-006` | Cập nhật — Create admin event list, detail, CRUD and status APIs | EVT-004, AUTH-018, AUTH-011A | P0 | 10 |
| `EVT-009` | Cập nhật — Integrate event audit and content freshness | EVT-006, EVT-008 | P0 | 10 |
| `EVT-011` | Mới — Implement authorized event media lifecycle API | EVT-010, EVS-003, EVT-006, EVT-009 | P0 | 10 |
| `EVT-012` | Mới — Define EventRecap model and migration | EVT-003, EVT-010 | P0 | 10 |
| `EVT-013` | Mới — Implement recap editing and publication APIs | EVT-012, EVT-011 | P0 | 10 |
| `EVS-002` | Cập nhật — Create EventSlider migration and Event linkage constraints | EVS-001, EVT-003 | P0 | 10A |
| `EVS-004` | Cập nhật — Create EventSlider CRUD and canonical linked-event projection | EVS-002, EVS-003, EVT-009 | P0 | 10A |
| `ADMIN-006` | Cập nhật — Create Admin Events list with editorial/time filters | ADMIN-004, EVT-006, EVT-009 | P0 | 11 |
| `ADMIN-007` | Cập nhật — Create Event form with managed cover upload | ADMIN-006, EVT-011 | P0 | 11 |
| `ADMIN-008` | Cập nhật — Create Edit Event form | ADMIN-007 | P0 | 11 |
| `ADMIN-009` | Cập nhật — Create event publish, unpublish and cancel controls | ADMIN-006, EVT-009 | P0 | 11 |
| `ADMIN-010` | Cập nhật — Create event deletion with dependency-aware confirmation | ADMIN-005, ADMIN-006, EVT-009 | P0 | 11 |
| `ADMIN-EVT-001` | Mới — Create recap editor and publish controls | ADMIN-008, EVT-013 | P0 | 11 |
| `FE-031` | Cập nhật — Create audience-aware Event detail and recap view | FE-006, EVT-005, EVT-013 | P0 | 12 |
| `FE-014B` | Cập nhật — Verify live Event Slider integration and linked Event freshness | FE-014, EVS-007, ADMIN-SLIDER-004, ADMIN-010, FE-031 | P0 | 12A |
| `MATCH-001` | Cập nhật — Create Match model and persistence constraints | BE-010 | P0 | 13 |
| `MATCH-007` | Cập nhật — Implement shared eligibility and candidate hard-constraint policy | MATCH-001, BE-016 | P0 | 13 |
| `MATCH-003` | Cập nhật — Create deterministic rule-based compatibility scoring | MATCH-007, BE-009 | P0 | 13 |
| `MATCH-004` | Cập nhật — Implement deterministic greedy buddy assignment | MATCH-003, MATCH-007 | P0 | 13 |
| `MATCH-008` | Cập nhật — Create admin matching run and preview persistence | MATCH-004, AUTH-018, EVT-008 | P0 | 13 |
| `MATCH-013` | Mới — Create admin matching preview and history read APIs | MATCH-008 | P0 | 13 |
| `MATCH-014` | Mới — Create guarded match publication and override APIs | MATCH-013, MATCH-007 | P0 | 13 |
| `MATCH-009` | Cập nhật — Create own-match result endpoint | MATCH-014, AUTH-017 | P0 | 13 |
| `MATCH-010` | Cập nhật — Create own-match accept/reject endpoint | MATCH-009, MATCH-007, AUTH-011A | P0 | 13 |
| `FE-033` | Cập nhật — Create matching participation/preferences form | FE-027, BE-012, BE-016 | P0 | 14 |
| `FE-034` | Cập nhật — Create match result and safe buddy card | FE-033, MATCH-009 | P0 | 14 |
| `FE-035` | Cập nhật — Create buddy match accept/reject UI | FE-034, MATCH-010 | P0 | 14 |
| `FE-037` | Cập nhật — Create My Buddy page | FE-034, FE-035 | P0 | 14 |
| `ADMIN-014` | Cập nhật — Create Admin Matching overview | ADMIN-003, MATCH-013 | P0 | 15 |
| `ADMIN-015` | Cập nhật — Create Run Matching control panel | ADMIN-014, MATCH-008 | P0 | 15 |
| `ADMIN-016` | Cập nhật — Create matching preview and publish table | ADMIN-015, MATCH-013, MATCH-014 | P0 | 15 |
| `ADMIN-017` | Cập nhật — Create constrained manual match override UI | ADMIN-016, MATCH-014 | P0 | 15 |
| `AUTH-025` | Mới — Implement authenticated password change endpoint | AUTH-024, AUTH-010 | P1 | 5 |
| `FE-024` | Cập nhật — Create User Settings page with real session actions | FE-021, AUTH-021, AUTH-025 | P1 | 6 |
| `ADMIN-011` | Cập nhật — Create admin event registration detail view | ADMIN-006, EVT-007 | P1 | 11 |
| `ADMIN-EVT-002` | Mới — Create recap gallery upload and ordering UI | ADMIN-EVT-001, EVT-011 | P1 | 11 |
| `FE-030` | Cập nhật — Create published event list for users | FE-021, EVT-005 | P1 | 12 |
| `FE-EVENT-CALENDAR-001` | Mới — Create Event Calendar UI after stable Event API | FE-030, FE-031, FE-014B | P1 | 12B |
| `FE-036` | Cập nhật — Create match feedback form | FE-034, MATCH-011 | P1 | 14 |
| `ADMIN-018` | Cập nhật — Create match history table | ADMIN-014, MATCH-013 | P1 | 15 |
| `MATCH-005` | Cập nhật — Implement Gale-Shapley comparison algorithm | MATCH-003, MATCH-007 | P2 | 16 |
| `MATCH-006` | Cập nhật — Implement Hungarian comparison algorithm | MATCH-003, MATCH-007 | P2 | 16 |

## 5. Recommended Execution Order

**Nền tảng dùng chung:** `BE-001 → BE-002..007 → Auth Backend/RBAC → AUTH-024 → AUTH-004..006/021..023 → guarded layouts`, cùng `EVT-008` (audit) và `EVS-003` (storage). Trong mỗi nhóm phải theo dependency cụ thể ở Part 24, không chạy theo thứ tự số ID một cách máy móc.

**User/Profile/Matching Track:**

```text
BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016
  → FE-025/026/039/027 → FE-038 → Dashboard / View / Edit Profile
  → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004
  → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009/010
  → FE-033/034/035/037 + ADMIN-014/015/016/017
```

**Event/Admin Track:**

```text
EVT-001/002/010 → EVT-003 → EVT-004/005/006 → EVT-009/011
  → EVT-012/013 → ADMIN-006..010 + ADMIN-EVT-001
  → EVS-001/002/004/005/006/007 → ADMIN-SLIDER-001..004
  → FE-031 → FE-014B
  → sau MVP: FE-030 → FE-EVENT-CALENDAR-001; ADMIN-EVT-002
```

Hai track có thể tiến hành độc lập sau các dependency chung. Matching backend không cần chờ Calendar, Recap hoặc AI; chỉ cần profile backend, eligibility, auth và audit. Thứ tự solo mặc định trong Part 24 vẫn hoàn thiện admin content/slider trước khi chuyển sang matching; không bắt buộc triển khai mọi P1 trước matching MVP.

## 6. MVP Boundary

**MUST HAVE:** FastAPI/database/auth/RBAC; logout; profile type/name/avatar/interests/languages; own edit và private read; onboarding với backend completion; dashboard; opt-in + opposite-group matching, greedy score, admin review/publish và user acceptance; admin Event CRUD/cover upload; basic recap draft/publish/cover; Event detail; dynamic Event Slider; ownership/CSRF/upload/audit/concurrency checks.

**SHOULD HAVE:** Calendar UI; recap gallery; percentage progress UI (readiness API vẫn bắt buộc); feedback, internal RSVP; password-change Settings; advanced filters; notifications sau khi có task backend/frontend tương ứng.

**LATER / RESEARCH:** Gale-Shapley/Hungarian comparison, embeddings/hybrid/learned weights, profile gallery UI, rich social interactions, recurrence/calendar sync, RAG/campus/gamification. Không thêm microservices/Kafka/Kubernetes/vector infrastructure riêng cho core Buddy MVP.

## 7. Architecture Check

```text
Register → Login → verified USER session → server profile readiness
  → incomplete: Onboarding → choose VIETNAMESE / INTERNATIONAL
  → complete: User Dashboard → opt-in + eligibility
  → opposite-group candidates → rule score → greedy → Admin preview/publish
  → both accept → VIETNAMESE ↔ INTERNATIONAL Buddy
```

```text
Admin Login → backend ADMIN authorization → Dashboard
  → Event / Recap / Media management → FastAPI → PostgreSQL + Supabase Storage
  → audience-safe APIs → Landing Slider / Event Detail / Recap
  → Calendar UI later consumes the same Event API
```

Ảnh: UI → backend auth/ownership/CSRF → validate/decode/re-encode → Storage → DB metadata. Giới hạn thiết kế là 5 MiB, JPEG/PNG/WebP, tối đa 4096×4096, kiểm tra signature/MIME/extension, UUID filename, loại EXIF, xử lý rollback và orphan cleanup. Draft/private media không dùng bucket public; URL ký có tuổi thọ tối đa 5 phút, không được coi là thu hồi tức thời.

FastAPI là auth authority; không mặc định JWT tự tạo có thể dùng `auth.uid()` của Supabase. Browser không nhận service key; database application schema không expose trực tiếp. Nếu expose thì kiểm tra riêng grants và RLS. [Supabase API security](https://supabase.com/docs/guides/api/securing-your-api)

Các quyết định size/fields/weights là lựa chọn thiết kế cho project. Chưa kiểm tra live database, deployment hoặc pháp lý; các con số free-tier cũ được đánh dấu cần xác minh khi deploy.

## 8. Final Verdict

**Do the existing Implementation Plan and architecture already support these requirements? — PARTIALLY.** Có nền tảng tốt về auth transport, profile form, Event CRUD và API-ready slider, nhưng chưa đủ ở eligibility, ảnh profile, hard constraint, recap, privacy và dependency.

**Is the updated Implementation Plan now ready to continue Backend implementation? — YES**, cho Backend Foundation và lộ trình core MVP đã chốt. Đây không phải xác nhận code/backend đã sẵn sàng production; các nhánh LATER vẫn cần thiết kế/task contracts khi bắt đầu.

**Task tiếp theo: `BE-001 — Initialize FastAPI project with pyproject.toml`. Dừng ở audit này; không implement BE-001 trong cùng session.**

Kiểm tra tài liệu: đủ 19 dòng feature matrix; mỗi task mới/cập nhật có đủ 7 trường; task registry không trùng ID; dependency graph không có vòng hoặc tham chiếu task không tồn tại trong các bước pending; Part 24 chứa mỗi pending task một lần theo dependency; toàn bộ nội dung lịch sử Parts 18/18A giữ nguyên; code/config/package trong apps giữ nguyên hash. Không chạy lại test/build ứng dụng vì chỉ sửa tài liệu; kết quả 80 tests trong docs cũ là lịch sử, không được báo là đã chạy lại trong audit này.
