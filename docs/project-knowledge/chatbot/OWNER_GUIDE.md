# Updating the chatbot guide

Edit **`apps/api/app/services/chatbot/sources/systemPrompt.txt`**. This is the canonical owner-maintained
source for guide/domain information. Do not edit JSON corpus files to change the same guide facts.
The 17 verified application/official FAQs remain supplementary; their code/official provenance is separate.

## Local workflow

1. Start the local API with `CHATBOT_API_ENABLED=true`, `CHATBOT_AI_ENABLED=false`; start the frontend
   with `VITE_CHATBOT_ENABLED=true` and the existing local API proxy. See [local commands](SINGLE_SOURCE_2026-10-24.md#validation).
2. Open the canonical file in your editor. Add a section, edit the original statement, or delete
   outdated information. Save as UTF-8. The imported file's CRLF bytes are deliberately preserved in Git;
   either normal UTF-8 line-ending style works when you edit it.
3. Ask a new question. The backend checks a bounded content hash on each guide lookup, rebuilds only
   changed content, and publishes a complete new index. No manual generation command or restart is needed.
4. Expand the answer's source details: check its line range and source-version prefix. A new response
   uses the new version. Earlier chat bubbles are a historical display of earlier requests; clear or
   reload the chat to remove them. They are not automatically rewritten or used as model memory.

For a safe, public example of formatting (replace with real supported information):

```text
## Service name
Describe the service and its location in complete sentences.
Contact: use a public institutional contact, if appropriate.
State dates, limits and what is unknown explicitly.
```

Use descriptive headings, short complete paragraphs and clear lists. Keep a business name with its
address and price in the same row/paragraph. Distinguish different services, cities, units and dates.
Do not add a second conflicting copy when correcting a fact: edit or remove the obsolete statement.
Avoid giant unpunctuated paragraphs; oversized matches return a cited reference and a request for a
more specific question, never a silently cut sentence. Plain Markdown `##` headings support new topics
without adding a new JSON FAQ. Known EN/DE synonyms help search; new names/subjects are also indexed
lexically. Unknown paraphrases can still require clarification; this is not an LLM.

Do not place credentials, private URLs, personal test-account data or agent instructions in this public
source. Public institutional/business contacts already supplied in the guide remain source material.
Source instructions are never executed. Invalid UTF-8, control codes, oversized input and common
credential-like patterns make guide retrieval unavailable rather than serving old source answers.
Verified supplementary FAQs remain available. Correct/save the file and ask again to recover.

## Check an update

From `apps/api` (PowerShell):

```powershell
.venv/Scripts/python.exe -m app.services.chatbot --knowledge-status
'eat' | .venv/Scripts/python.exe -m app.services.chatbot
.venv/Scripts/python.exe -m pytest tests/test_chatbot_source.py tests/test_chatbot_api.py -q
```

The first command shows `ready`, the full SHA-256, source lines and passage/policy counts; otherwise
it gives a sanitized diagnostic code such as `invalid_utf8`, `invalid_text` or `unreadable`. It never
prints the guide or local path. The second returns a source-grounded JSON answer and provenance.
Check a clear EN question, a DE question, a short keyword and an unsupported question after edits.
For German, the guide is quoted without translation and explicitly labeled as such; the surrounding
answer/qualification is German. This avoids fabricated or stale translated facts after source edits.

## Conflicts, verification and release

Owner approval authorizes use; it does not independently verify current accuracy. Source answers are
labeled owner-provided, with no verification date. Existing verified FAQ answers take precedence.
High-stakes/current-fee questions do not turn old guide claims into current advice. Explicit historical
reference questions can receive qualified source quotations. Normal unsupported questions abstain.

Known passport-validity, cafeteria-dinner and differing dorm-room-range contradictions are detected
from the actual text; both versions remain cited. Repeated single-valued `Fact:`, `Status:`,
`Current fee:`, `Passport validity:`, `Dinner service:` or `Opening hours:` fields with different
values under the same section are also treated conservatively as conflicts. Use plain paragraphs for
separate independent facts. `[CONFLICTED]` explicitly marks an unresolved passage. Detection is
bounded and deterministic, not a guarantee of finding every contradiction in arbitrary prose.
Clarify the source itself; the chatbot does not guess which version is correct.

Local edits do **not** change Render/Vercel Production. The file is packaged with the API; it reaches
Production only through a separately authorized commit/push/release and new deployment. New statuses
and provenance require the matching frontend/API release. Feature flags stay OFF by default and AI
inference remains disabled. This task does not authorize release operations or a remotely editable CMS.

To undo an incorrect update, use your editor/Git history to restore the earlier file, save, and retest.
Keep any unsaved work before restoring a file. New source lookups revert automatically to the restored
hash/content; Production rollback remains a separate controlled release operation.
