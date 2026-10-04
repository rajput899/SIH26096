# Heritage extension verification

Current state: implementation and local checks in progress; runtime acceptance is pending. Phases 0–2 remain owner-verified. No live archival records, originals or publication states were changed by this work. Do not publish “Dr Babasaheb Ambedkar’s letters” until public-display rights are independently confirmed.

## Owner-run checks (normal Windows PowerShell)

Docker Desktop must be running with Linux containers. Use the existing project `.env` and volumes. The frontend's existing npm dependencies and Chrome are prerequisites for the browser runner; it defaults to `C:/Program Files/Google/Chrome/Application/chrome.exe`.

```powershell
Set-Location 'C:\Users\Hackathon\Documents\Codex\2026-09-24\we-are-starting-sih26096-completely-from'
.\scripts\check_phase3.ps1
```

The existing runner now also includes `tests/heritage.spec.ts`. It builds backend/frontend/worker, applies additive migration 004, runs real PostgreSQL tests in disposable schemas/storage, backend lint, frontend lint/typecheck/build, then runs archive/OCR/kiosk/heritage browser tests against the isolated API on 8011 and frontend on 3001. Cleanup stops those fixture processes and removes their temporary schema, files and credentials. It does not reset production volumes or publish the owner's photograph. Do not use `docker compose down -v`.

New browser checks cover a self-created PNG becoming visible only after publication, thumbnail withdrawal and original integrity; a synthetic plaintext source through extraction/review/publication into a quiz, server result, certificate download and invalidation after source withdrawal; and a self-created silent WAV through reviewed cues and browser playback. These are explicitly test fixtures, never historical holdings. Automated fixture servers force Ollama generation and disable Gemini and SMTP. Provider and email tests use mocks.

The successful baseline ends with `PASS: Kiosk and heritage baseline runtime suite...`; this does not certify live Gemini, real SMTP delivery, physical touchscreen accessibility or historical source accuracy. `-RunAI` additionally requests the existing real local Ollama/Qdrant acceptance, requiring installed/configured models.

## Gemini (optional, explicit cloud provider)

Edit `.env` locally; never paste keys into chat or commit the file:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=<your privately supplied key>
GEMINI_MODEL=<a model available to your account that you intend to test>
```

No Gemini model is hardcoded or assumed tested. Recreate the backend after configuration changes:

```powershell
docker compose up -d --build backend
```

The AI page indicates cloud processing. Questions and retrieved public verified excerpts go to Google; no automatic fallback occurs. Ollama embeddings remain separately configured. To run ONE deliberate live acceptance question against approved source material:

```powershell
docker compose exec backend python -m app.check_gemini --live --question 'Your question about an actual published verified source'
```

This may incur provider usage. It succeeds only with a validated answer and citations. Review the quoted source and factual support manually. No such live call has been made by the agent. Restore `AI_PROVIDER=ollama` and recreate backend to use local generation.

## Optional email

Backend-only settings: SMTP_HOST, SMTP_PORT (587 default), SMTP_USER, SMTP_PASSWORD, SMTP_FROM, CERTIFICATE_PUBLIC_URL. Use a STARTTLS SMTP service; set the public URL to the deployment's visitor-accessible origin. Blank host/from disables delivery and leaves certificate download available. No SMTP credentials were set and no email was sent. UI requires an explicit request and consent; success means the mail server accepted the message, not proof of delivery. Test with your own address after configuration.

## Manual acceptance still required

- Check `/` home links, `/archive` real permitted holdings, image detail and `/speeches` playback after the rebuild.
- Confirm the named unapproved-rights photograph remains unpublished.
- Check keyboard focus, screen reader announcements, native audio/video controls, high contrast, enlarged text, portrait/landscape and fullscreen on the actual convertible device.
- Confirm supported MP3 and H.264/AAC MP4 on the target browser; only self-created WAV is covered by the new automated browser fixture.
- Complete a real curator-reviewed activity and inspect downloaded HTML/Print-to-PDF and verification ID. Certificates are not signed credentials and imply no accreditation.
- Verify live Gemini only after a permitted, published, curator-verified source and private configuration are available.
