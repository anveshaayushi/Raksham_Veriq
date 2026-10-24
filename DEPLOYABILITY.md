# Deployability: one page for judges

VERIQ is a local web app (Python, Streamlit, ffmpeg, optional PyTorch CPU model). No paid API, no cloud call, no live
bank link. Installs with one command, offline if needed, and runs on a laptop CPU (rules: under 1 ms per chat; voice:
about 0.5 s per clip). Every result names its evidence and the next step; it blocks nothing and contacts no one.

| Path | Who runs it | What it adds | Cost (ESTIMATES, not quotes) | What it needs first |
|---|---|---|---|---|
| 1. Citizen web app (today's build) | an NGO, a cyber-awareness cell, or the team | "check before you pay": per-payee answer, 1930 filing sheet | small cloud VM (2 vCPU, 4 GB) or a laptop; no licence fees | HTTPS, privacy notice, moderation of the registry |
| 2. Reviewer desk | a bank's fraud-operations team or a state cyber cell | review queue, overturn with audit trail, cross-victim registry (keyed hashes) | one server per desk; the real cost is reviewer time (the Round 1 deck's pilot goal: under 10 minutes per report, not measured) | security review, DPDP review, data-sharing agreement, partner's labelled cases |
| 3. At the payee screen of a UPI or bank app | a bank or UPI app (partner) | the same name check where the registered payee name is shown, before the money moves | integration work by the partner; models run on their servers | a partner; their registered-name data instead of user-typed names; regulator engagement |

What is proven today: the install path (clean venv and offline wheelhouse, smoke test 7/7), the rules and reports
(1,100+ automated tests, 17/17 planted bugs caught), payee extraction on synthetic chats, and honest failure of the
voice model across datasets (so it abstains). What is not proven: accuracy on real victims' chats, reviewer
throughput, and any partner integration. No partnership with I4C, SEBI, RBI, NPCI or any bank is claimed.
Details: DEPLOY.md.

## Cost: labelled ESTIMATES (assumptions stated; not quotes, not measured)
| Item | Estimate | Assumptions |
|---|---|---|
| Server for one reviewer desk | about Rs 3,000-6,000 per month | one 2 vCPU / 4-8 GB cloud VM or an existing on-premise server; no GPU (CPU timing measured: 2.94 s for a chat with 3 voice notes on 2 vCPUs) |
| Software licences | Rs 0 | all components are open source (DISCLOSURE.md); no paid API |
| Reviewer time | the main cost; about 5-10 minutes per review request (ESTIMATE, not measured; the Round 1 deck's pilot goal was under 10 minutes) | a trained fraud-desk analyst checks the payee on SEBI Check / bank records |
| Keeping the SEBI list fresh | a few hours per month | someone downloads the dated intermediary list and runs the loader |

## What a pilot needs
- **Data:** the partner's own consented, labelled cases (scam and genuine) to measure before any number is shown to
  users; a fresh dated SEBI intermediary list; ideally the bank's registered payee name instead of a user-typed one.
- **Consent:** a privacy notice and consent text reviewed for DPDP Act 2023; retention rules for the registry.
- **Review staff:** at least one trained reviewer per shift with authority to overturn; an escalation path to the
  bank's fraud team or the state cyber cell; the 1930 helpline stays the official reporting route.
- **Integration points:** (a) web app link shared by the bank or cyber cell; (b) reviewer desk on their network;
  (c) later, the same check at the payee-confirmation screen of a UPI or bank app (partner-side work).
- **Security:** HTTPS, reviewer authentication, a penetration test, key management for the registry secret.
No partnership with any bank, UPI app, I4C, SEBI, RBI or NPCI exists or is claimed.

