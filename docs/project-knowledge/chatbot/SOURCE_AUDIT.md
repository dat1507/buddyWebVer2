# Historical prompt audit — 2026-10-22

Input: owner-provided `systemPrompt.txt`, 431 lines, SHA-256
`0fe1c16900d47c2c57e50d56cdc3ee4b2bd66dc9d6b2ccd2366256162519f0a8`.
The source remains unchanged in its original external location. No original private staff-contact
list or full source is copied into Git. Line numbers below refer to that exact input.
This audit date records inspection, not verification of the historical claims.

| Classification               | Source lines                                     | Treatment                                                                                                                                                                  |
| ---------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System behavior              | 1–5                                              | Reject as agent instructions. Overbroad answer scope, assumed university context, sarcasm/teasing and mandatory Google use are replaced by compact factual behavior rules. |
| VGU knowledge                | 12–19, 74–86                                     | University/social/campus references; verify identity separately; avoid historical location assertions.                                                                     |
| Buddy Program                | 7–11, 425–431                                    | Community/contact material; website source confirms team mailto. No verified recruitment workflow in the prompt.                                                           |
| Student life                 | 189–240, 241–356, 380–400, 420–423               | Sports, food, shopping, internet, printing, laundry and local advice; retain categories, quarantine transient specifics.                                                   |
| Transportation/accommodation | 74–77, 87–128, 156–231                           | Bus/taxi/route, guest house/dorm, rents and schedules need current service confirmation.                                                                                   |
| Visa/arrival                 | 38–86                                            | Immigration, passport, customs, vaccines, registration and arrival deadlines are high-stakes and unresolved. No current procedural FAQ derived.                            |
| Contacts/services            | 20–37, 78–86, 182–189, 357–379, 401–419, 425–431 | Prefer institutional service links; individual contacts, clinic quality and hours remain unverified. Library service availability separately verified.                     |
| Time-sensitive facts         | 63–65, 117–125, 130–231, 241–419                 | All historical prices, exchange conversions, timetables, gate times, shops, room availability and phone plans excluded as current facts.                                   |

## Contradictions and duplication

- Cafeteria: lines 193–194 advertise breakfast/lunch/dinner; lines 233–234 say no dinner.
  No current meal-service evidence resolves this. `legacy-cafeteria` is conflicting, never retrieved.
- Passport: line 43 requires twelve months upon arrival; lines 53–54 say six months on entry.
  These might refer to different processes, but the source does not establish that distinction.
  Neither becomes advice. `legacy-passport` is conflicting. Verify with the appropriate Vietnamese
  authority/mission and VGU International Office before adding guidance.
- Dorm rooms: lines 168–169 give 600,000–1,200,000 VND/person/month; lines 190–191 extend the
  range to 2,400,000. Guest-house prices use night/house and month/house, not person/month.
  Different categories may explain differences; do not merge them into a single current price.
- Buddy/International Office contacts repeat at the start/end. Campus sports facilities repeat
  in Sports Complex/Living on campus; SIM/internet appears in arrival and campus support;
  gate closure repeats in sports/dorm/campus life. Consolidation does not validate the claims.
- One exchange rate is explicitly dated `02/06/2025`; other EUR equivalents do not form a
  consistent current conversion. Exact historical precision is not evidence of current accuracy.

## Incomplete references and institutional uncertainty

`Route Map Link`, `Sports Complex Schedules`, `this link`, `Dorm Registration Form: Click here`
and the motorbike QR code lack usable targets in the text. Social channel names/Instagram handles
are not complete URLs. The old `www.library.vgu.edu.vn` spelling differs from the current linked
`library.vgu.edu.vn` host. No claim that these incomplete references resolve is made. Google Maps
short links and individual restaurant/phone listings were not exhaustively checked; treat their
current existence, location and prices as unverified, not proven broken.

The old source says campus is in Binh Duong and not Ho Chi Minh City. The inspected
[official VGU page](https://vgu.edu.vn/international-office) footer now uses Ho Chi Minh City.
The [VGU conference page](https://icsud.vgu.edu.vn/about-us/) itself contains an older campus
paragraph and a newer footer with different naming. This is an administrative/geographic
verification gap; do not choose one silently or assert a campus move.

The prompt's health-insurance exemption, vaccine advice, malaria prophylaxis, customs thresholds,
visa type, police registration, clinic equivalence and free dorm care require responsible
authoritative verification. No legal/medical claims or hotline numbers are published from them.
International Office room 218, old named staff, check-in before 15:00 and gate times need renewed
confirmation. Institutional appointment and recruitment rules are not inferred from website UI.

## Official-source checks and promotion scope

| Source checked 2026-10-22                                                                                            | What was actually supported                                                                                                                                                     |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [VGU institutional introduction](https://icsud.vgu.edu.vn/about-us/)                                                 | University identity, public status, founding/cooperation only; no dynamic counters or old campus wording promoted.                                                              |
| [VGU Library](https://library.vgu.edu.vn/print-copy-scan-services/)                                                  | Printing/copying/scanning, credit through library staff and institutional library email. Page also lists prices; answers refer to the current page instead of freezing a price. |
| [Dormitory portal](https://dorm.vgu.edu.vn/)                                                                         | Official service portal exists; no housing price/application policy inferred.                                                                                                   |
| [International Office](https://vgu.edu.vn/international-office), [Sports Complex](https://vgu.edu.vn/sports-complex) | Official destinations exist, but extracted content contains template placeholders; no detailed policy/contact/hours validation.                                                 |
| [Buddy page](https://vgu.edu.vn/eu/international-office/incomings-international-students/buddy-program)              | Search index showed support/contact text; direct fetch timed out. Not promoted as a fully inspected official procedure. The Vietnamese variant returned template placeholders.  |

The fifteen code-confirmed entries cite actual files inspected on local `main` at `f88c18d`.
They explain implemented registration/verification/Matching/invitations/profile dialog/Events/chat
or route users to owner-confirmed service links. They are not independent institutional evidence.
No private records, real account operations or Production requests were used to build the corpus.
