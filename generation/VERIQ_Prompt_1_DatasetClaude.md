# PROMPT 1: the dataset-generating Claude (brand-new chat)

**Rules for this chat:** open a brand-new chat. Attach NOTHING (no repo, no brief, no rubric, no VERIQ file). If you can, use a different AI from the one that wrote the engine.
**How to run:** paste the prompt below. It starts with D1 batch 1. Then send these messages one at a time, in this order: `Next batch` (x3), `D2`, `D3`, `D4`, `Finish`. Budget 60 to 90 minutes. If time is short, stop D1 after batch 3 and still do D2, D3, D4.
**Afterwards:** save every raw output unedited with this prompt; put the files at the repo paths named below; commit BEFORE anyone runs the engine on them. Then use `VERIQ_Prompt_2_MainClaude.md`, Message 2.

---

```
I am building TEST DATA to evaluate a tool that helps people in India spot financial-fraud conversations before they pay. You do not have access to the tool or its rules and must not ask about them; do not guess what it does.
Everything must be FICTIONAL: invented people, firms, phone numbers, UPI IDs and bank accounts. No real brands, people or numbers. Use firm names that do not exist; invent numbers that cannot belong to a real person (for example 5 digits + "000" + 2 digits;
account numbers beginning 0000). Do not write anything more persuasive than real scams; this is for detection testing only. Do not use these names: Meera, Rahul, Navyug, Sunita, Ramesh.
Work in batches. After each batch write nothing but the files (no commentary). If you can create files, deliver them and a zip named veriq_datasets_<part>.zip. If you cannot, print every file as
"=== FILE: <path> ===" followed by the exact file content, so I can split it by script.

D1 BLIND CHATS (4 batches of 20: c001-c020, c021-c040, c041-c060, c061-c080; each batch 10 scam + 10 genuine, shuffled).
 Files: data/blind_ai/chats/c001.txt ... (one chat per file) in WhatsApp "Export chat, without media" style. Use the Android form "20/10/2026, 8:59 pm - Name: message" for about 70% of chats and the iPhone form "[20/10/26, 8:59:12 PM] Name: message" for the rest.
 Multi-line messages sometimes; 6 to 50 messages over 1 to 14 days; English, Hinglish (Roman script), some Devanagari Hindi; natural typos, emojis, abbreviations. About 10% of chats include a voice note shown as "<Media omitted>" or "<attached: PTT-20261005-WA0003.opus>".
 SCAM variety (do not repeat a script): fake investment club or research firm with a claimed registration number; fake trading-app profits then a fee or tax to withdraw; part-time task jobs asking for deposits; loan or KYC-update pretexts; customer-care and refund pretexts; courier or customs fees;
 romance then investment; crypto; "guaranteed" returns; impersonated bank or official staff; OTP or remote-access requests; payment details that change over days; payment to a personal-looking account, a firm-like account, a payment link or a QR mentioned in the chat. Vary how the payee is written: UPI ID, UPI ID with spaces or words, bank account with IFSC, phone-number UPI, link.
 GENUINE variety, including HARD ones that sound scary but are fine: brokerage account-opening fee from a registered-looking firm; SIP or insurance premium; rent split between friends; a shop purchase; a freelancer invoice; school fees; family support; utility bills through a payment gateway; bank customer care asking for no money;
 an investor group that shares tips but never asks for money; honest use of "pay by 5 pm", "limited seats", "returns are not guaranteed", "tax". About 15% of all chats should be genuinely ambiguous (a reasonable person would hesitate).
 Only about 15% of chats may write the payee in obfuscated form ("ravi dot k at okaxis"); the rest write it plainly.
 Also write data/blind_ai/labels.csv with EXACTLY these columns and this style: file,label,claimed_firm,bank_app_names
   c001.txt,scam,Aarohan Capital,ravi.k@okaxis=RAVI KUMAR STORES;00001234567890=SHREE TRADERS
 label is scam or genuine; claimed_firm is empty if the chat names no firm; bank_app_names lists, for EVERY payee in the chat, the CANONICAL identifier (lowercase UPI ID, or digits-only account) = the name the sender's bank app would display (leave the whole field empty if the sender never checked).
 Pick realistic display names: sometimes the firm, sometimes a personal name, sometimes an unrelated shop, sometimes a payment gateway, sometimes a look-alike of the firm.
 And write data/blind_ai/labels_extended.json: one object per chat: {"file","label","scenario","language","difficulty":"easy|medium|hard|ambiguous","claimed_firm",
 "payees":[{"identifier":"<canonical>","kind":"upi|account|phone_upi|link","message_index":<1-based>,"name_relation":"matches_firm|unrelated_business|personal_name|lookalike|payment_gateway|not_applicable","intended_risk":"risky|fine|unclear"}],
 "voice_transcripts":[{"file":"...","transcript":"..."}],"why":"<one sentence from the writer's view>"}. Label by REAL-WORLD INTENT, never by guessing what a tool would say.
 Quotas across all 80: at least 8 chats per language style; at least 12 "hard"; no two chats may share firm names, payees or opening lines.

D2 BLIND NAME PAIRS: data/names_blind/pairs.csv, columns id,claimed_firm,bank_app_name,relation,note. 200 rows. relation is one of same_entity, different_entity, lookalike_of_different_entity, cannot_tell. Distribution: 70 same_entity, 70 different_entity, 30 lookalike_of_different_entity, 30 cannot_tell.
 Cover: Pvt Ltd / Private Limited / LLP / & versus and; legal name versus trading brand; abbreviations and initials; Roman-script spelling variants of Hindi names (Shri/Shree, Laxmi/Lakshmi); reordered words; city or branch suffixes; typos; sole-proprietor shops named after a person; payment-gateway or aggregator names (fictional ones);
 holding company versus brand; deliberately close but different firms; very short names. Decide relations by real-world judgement.

D3 EXTRACTION TRUTH: data/extract_blind/cases.jsonl, 100 lines. Each line: {"id","text":"<1 to 6 messages in WhatsApp export lines>","expected":{"payees":[{"kind":"upi|account|ifsc|phone|link","value":"<canonical: lowercase UPI id, digits-only account, uppercase IFSC, 10-digit phone, full URL>"}],"amounts_inr":[<numbers>],
 "should_not_extract":["<strings in the text that look like payment details but are not>"]}}. 60 positive cases (obfuscated and plain: "ravi dot k at okaxis", spaced or hyphenated digits, Devanagari digits, number words, mixed case, "at the rate", account plus IFSC lines, amounts such as 10k, 25,000/-, Rs, rupees, one lakh)
 and 40 negative or tricky cases (email addresses, order or ticket ids, OTPs, phone numbers that must not be read as accounts, years, PIN codes, card-last-4, URLs that are not payment links, a QR mentioned with no identifier).

D4 VOICE SCRIPTS: data/voice_scripts/scripts.csv, columns id,language(en|hi|hinglish),type(scam_like|genuine),seconds_target,text. 60 rows, 30 and 30; each takes 5 to 25 seconds to read aloud; 10 of the scam_like and 10 of the genuine mention a payee spoken aloud ("ravi dot k at okaxis"); genuine ones must be similar in style and length
 (bank customer care, delivery update, family message, shop owner) so style alone does not separate them. Also data/voice_scripts/RECORDING_GUIDE.md for three teammates: consent and privacy (record only your own voice, with written consent; never clone another person; delete clips after the event), phone voice-note recording in a quiet room,
 file names genuine_<name>_<scriptid>.opus, and a labels template data/voice_scripts/audio_labels_template.csv with columns file,label(real|fake),source(human|open_tts|own_voice_clone),language,script_id.

FINAL step (when I say "Finish"): write data/GENERATION.md with the model name as you know it, the instruction "date: to be filled by the human", a summary table of counts per dataset by type, language and difficulty, the list of known weaknesses of this data (for example: written by an AI, may be more tidy than real chats, correlated with other AI-written code),
and then deliver the final zip veriq_datasets_all.zip.
Start with D1 batch 1 now.
```

---

## Where the outputs go in the repo

| Output | Path |
|---|---|
| D1 | `data/blind_ai/chats/*.txt`, `data/blind_ai/labels.csv`, `data/blind_ai/labels_extended.json` |
| D2 | `data/names_blind/pairs.csv` |
| D3 | `data/extract_blind/cases.jsonl` |
| D4 | `data/voice_scripts/` |
| Provenance | `data/GENERATION.md` (fill in the date) plus the raw outputs and this prompt |

Spot-check 5 chats and 10 name pairs before committing. Commit message: `FINALE: blind AI-generated datasets (before any run)`.
