# Product screenshots

Captured on **2026-09-11** from the running local Vite development application at source baseline **`fced9f3`**, in English, using the connected browser's default desktop viewport. These are real viewport captures, not generated mockups or full-page exports.

| File               | Route         | Context                                                                                           |
| ------------------ | ------------- | ------------------------------------------------------------------------------------------------- |
| `landing-page.png` | `/`           | Public landing hero and navigation; development mode uses event fixtures below the fold           |
| `login.png`        | `/login`      | Student login UI, empty fields, no session or credentials                                         |
| `admin-login.png`  | `/adminLogin` | Administrator entry UI, empty fields; authentication and account provisioning are not implemented |

## Refreshing previews

1. Run `npm ci` and `npm run dev` from `apps/web` with a working Node/npm installation.
2. Switch the interface to English and open each route directly.
3. Capture the real rendered page after fonts and assets have loaded. Keep fields empty and avoid personal account data.
4. Replace the corresponding PNG, inspect it visually, and confirm its relative link from the root README.
5. Update this date and source baseline.

Use development mode for sample event posters. Production preview always calls the event API. The existing logo is linked directly from `apps/web/src/assets/vgu-buddy-logo.png` and is not duplicated in this directory.
