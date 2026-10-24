# Blind chat set: instructions for the writers (Q2 item c)

Who: teammates who have NOT read VERIQ's rules, code or benchmark. Each writes **10 scam and 5 genuine** chats.

How:
1. Use two phones or two WhatsApp accounts. One plays the "broker / advisor / support agent", the other the investor.
   Write naturally, in any language mix you like (English, Hindi, Hinglish, ...).
2. Use MADE-UP names, firms and UPI IDs or account numbers (e.g. `ravi.k@okaxis`). No real people's details,
   no real company names, no real SEBI numbers.
3. Genuine chats: ordinary broker or support conversations, including payment instructions.
4. Export each chat: WhatsApp > three dots > More > Export chat > **Without media**. Name it `<yourname>_<01..15>.txt`.
5. Add one line per chat to `labels.csv`:

```
file,label,claimed_firm,bank_app_names
asha_03.txt,scam,Navyug Capital,ravi.k@okaxis=RAVI KUMAR STORES
asha_11.txt,genuine,Aarohan Securities,aarohan.sec@icici=AAROHAN SECURITIES PVT LTD
```

`bank_app_names` = the name YOUR bank app would show for each UPI ID / account in that chat (you decide; separate
several with `;`). Leave it empty if the investor never checked.

Then: `python -m bench.blind.run` (once). Do not change the rules after seeing the result; report it as it is.
