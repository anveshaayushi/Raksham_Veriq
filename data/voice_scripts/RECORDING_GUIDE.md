# Voice recording guide (3 teammates)

All scripts are fictional (`scripts.csv`). `type` says whether the *script* reads like a scam or a genuine message; the audio label (real/fake) is separate.

## 1. Consent and privacy (read first)
- Record **only your own voice**, and only after you have given **written consent** (a message in the team chat is enough) for it to be used in this event's test set.
- **Never clone, imitate or record anyone else's voice**, including family, friends, celebrities or officials. An `own_voice_clone` clip means a clone of **your own** voice, made with your own consent.
- Do not say real names, real phone numbers, real UPI IDs or real account numbers. Read the script exactly as written: its identifiers are fictional.
- Keep clips on the team's shared folder only. **Delete all clips (originals and copies, including phone and chat backups) after the event.** Do not upload them to any public site.
- If anyone withdraws consent, remove their clips immediately and record the removal.

## 2. Recording genuine voice notes on a phone
1. Find a quiet room: door closed, fan/AC off, no TV. Sit still, phone about a hand-span from your mouth.
2. Use the WhatsApp voice-note button in a chat with yourself (or the phone's voice recorder), so the clip is a normal compressed voice note. Do not use studio/denoise apps.
3. Read the script at your normal pace, once, in a natural voice, in the language of the script. If you stumble, record again; keep only the clean take.
4. Each clip should last about the `seconds_target` in `scripts.csv` (5 to 25 s).
5. Export the voice note as `.opus` (WhatsApp's own format). Do not rename other formats to `.opus`.

## 3. File names
- Genuine human clips: `genuine_<name>_<scriptid>.opus` (example `genuine_asha_v014.opus`). `<name>` is your first name, lowercase.
- Open text-to-speech fakes: `fake_tts_<tool>_<scriptid>.opus`.
- Clones of your own voice: `fake_clone_<name>_<scriptid>.opus`.

## 4. Labels
Fill `audio_labels_template.csv` (columns `file,label,source,language,script_id`): label is `real` or `fake`; source is `human`, `open_tts` or `own_voice_clone`; language is `en`, `hi` or `hinglish`.
Record scripts of **both** types (scam_like and genuine) in your real voice so the detector cannot learn "scam script = fake".
