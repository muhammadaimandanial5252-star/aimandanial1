---
name: nexabot-generate
description: Generate images, videos (incl. Seedance 2.5), music and text-to-speech through the NexaBot API (nexabot.id) from the workspace shell. Use when the user asks to generate/buat gambar, video, lagu, muzik, suara or TTS.
---

# NexaBot generate

Generates images, video (incl. Seedance 2.5), music and TTS through the NexaBot API (https://nexabot.id), using the user's own API key and credit. Run calls from the workspace shell with `scripts/nexabot.py` in this skill folder (the browser can't: the API sends no CORS headers).

Reply in the user's language (Bahasa Melayu santai if they write in Malay), short and practical.

## Settings (the user fills these in)

API_KEY: PASTE_KEY_KAU_KAT_SINI
TELEGRAM_ID: PASTE_TELEGRAM_ID_KAT_SINI

- TELEGRAM_ID is optional. It is the user's NexaBot account ID, needed only for GPT Image.

## Step 0 — Get the key (every session)

1. Read API_KEY above. If it still says `PASTE_...` or is empty, look for a key the user gave earlier in this chat (starts with `nxb_`). If there is none, ask once in one short message: "Bagi API key NexaBot kau (bermula nxb_). Ambil kat nexabot.id → bahagian API." Then wait.
2. Same for TELEGRAM_ID, but **don't ask for it**. If it's empty, just use the Google image model (see below).
3. Never print the key back in replies, never write it into delivered files, never put it in URLs or anything sent anywhere except nexabot.id.
4. First time in a session, check the balance: `NEXABOT_KEY=<key> python3 <skill>/scripts/nexabot.py credit`.
   - 401 → the key is wrong or revoked; ask for the right key.
   - NETWORK error → tell the user in one line that Claude can't reach nexabot.id from here, and that they need to allow network access to `nexabot.id` in their Claude settings (code execution / network access), then try again.
   - 402 / balance too low → tell them to top up credit at nexabot.id. Mention that the web "Unlimited" plan does NOT cover the API; only API credit or the separate "API Unlimited" plan does.

`<skill>` = the folder that holds this SKILL.md.

## Costs (always report model + cost + remaining balance after generating)

| what | cost (credit) | on API Unlimited plan |
|---|---|---|
| Omni modes (img, t2v, sfv, i2v, r2v, extend, music, tts) | 0.15 / request, refunded on failure | free |
| Seedance 2.5 (15 s or 30 s) | 0.2 / video, refunded on failure | free |
| GPT Image | 0.1 / image | always charged |

Before a job with several outputs, check the balance and tell the user up front if it won't cover every request.

## Which image model

- **GPT Image (`--gpt`)** when TELEGRAM_ID is filled in: 0.1 credit, sharp, larger PNG, supports reference images (product, face). Small NexaBot watermark bottom-right.
- **Google image (`img` mode, no `--gpt`)**: 0.15 credit, 768×1376-class JPG, ~20 s. Use it when TELEGRAM_ID is empty, when the user asks for it, or when GPT Image fails (say so in one line). The script falls back to it automatically if `--gpt` is passed without TELEGRAM_ID.

## Which video model

- **Seedance 2.5** (`seedance`): one clip of 15 s or 30 s, 0.2 credit. Best for a full ad/story in one go. Text-to-video, or image-to-video with one start-frame image (max 15 MB). Ratio 1 = 16:9, 2 = 9:16, or "1:1".
  - Jobs run in a batch every 60 s, so the status starts `queued`. Max 20 waiting jobs per account.
  - Result files are deleted 30 min after finishing; the script downloads right away.
  - Prompt max 10,000 chars. No brand names or copyrighted characters in prompts. For a 30 s video write one full 30 s prompt.
- **Omni modes** (~10 s clips, 0.15 credit): `t2v` text to video, `sfv` start frame, `i2v` 1–3 ingredient images, `r2v` reference video, `extend` continue an mp4.
  - Longer talking videos: `extend` the previous clip, or make one character image first and generate each angle with `i2v` using that image. Submit independent clips in parallel.
  - Ask for one silent second after the last spoken word so the line isn't cut off.

## How to run

Pick aspect/ratio: 9:16 for reels/stories, 1:1 default for images, 16:9 for landscape. Several outputs → one job each, run in parallel. English prompts usually work best; keep the user's wording if they gave an exact prompt.

```bash
K="NEXABOT_KEY=<key> NEXABOT_TELEGRAM_ID=<telegram id or empty>"
env $K python3 <skill>/scripts/nexabot.py img "<prompt>" --aspect 5 --gpt --out out1.png      # GPT Image (aspect 1=1:1, 2=16:9, 5=9:16)
env $K python3 <skill>/scripts/nexabot.py img "<prompt>" --aspect 1 --out out1.jpg            # Google image
env $K python3 <skill>/scripts/nexabot.py img "<prompt>" --gpt --media ref.jpg --out p.png    # with reference image
env $K python3 <skill>/scripts/nexabot.py t2v "<prompt>" --ratio 2 --resolution 1080 --out v.mp4
env $K python3 <skill>/scripts/nexabot.py i2v "<prompt>" --ratio 2 --resolution 1080 --media char.jpg --out shot1.mp4
env $K python3 <skill>/scripts/nexabot.py seedance "<prompt>" --duration 15 --ratio 2 --out seed1.mp4   # add --media start.jpg for a start frame
env $K python3 <skill>/scripts/nexabot.py music "<description or lyrics>" --out m.wav
env $K python3 <skill>/scripts/nexabot.py tts "<text>" --voice Kore --out vo.wav
```

Seedance can take several minutes: run it with a long timeout (or in the background) and keep the user posted.

After it finishes:
1. Look at the result before sending (for a large PNG make a JPG preview first; for video, check a few frames).
2. Send the original file to the user.
3. One line: model, cost, remaining balance (from the script output).

## API reference (for anything the script doesn't cover)

- Base `https://nexabot.id`, header `x-api-key: <key>`. No rate limit on the API.
- Submit `POST /api/v1/api` `{mode, prompt, aspect|ratio, resolution, voice, media[]}` → 202 `{ok, job_id, status, credit_cost, credit_balance}`.
- Status `GET /api/v1/jobs/<id>` → `{job:{status: queued|processing|done|failed}}` (poll every 3 s). Download `GET /api/v1/jobs/<id>/download`.
- Balance `GET /api/v1/api/credit`. Modes and voices `GET /api/v1/modes`.
- Seedance: `POST /api/v1/seedance` `{prompt, duration: 15|30, ratio, media?}`; status `GET /api/v1/seedance/<id>` (poll every 10 s); download `GET /api/v1/seedance/<id>/download`.
- GPT Image: `POST /api/v1/gpt-image` `{prompt, aspect, references[], telegram_id}`; status `GET /api/v1/gpt-image/<id>` → `images[0].url`.
- media items are base64 data URIs.
- Errors: 400 bad body, 401 bad key, 402 not enough credit, 403 not your job, 404 not found, 409 still processing.

TTS voices: Achernar, Achird, Algenib, Algieba, Alnilam, Aoede, Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux, Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi, Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr, Zubenelgenubi.
