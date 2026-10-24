# Problem and user

## The user: Meera (persona; fictional, built from the public warnings cited below)
Meera Kulkarni, 52, a retired schoolteacher in Pune, saves through a bank FD and recently opened a demat account.
She is added to a WhatsApp group, "Navyug Wealth VIP Research", where an "analyst" posts winning stock tips and
members post screenshots of profits. A "relationship manager" then messages her directly, sends a SEBI registration
number, voice notes and a QR code, and asks her to "add funds" by UPI. Each payment goes to a different UPI ID or bank
account. When she asks to withdraw her "profit", she is told to first pay an 18% "tax". She never pays a firm: she
pays mule accounts. She needs one answer before she taps Pay: **who would actually receive this money?**

## Three UPI-fraud scenarios VERIQ is built for
1. **Fake advisory group, rotating payees (scenario A in the app).** Impersonates a registered intermediary; payment
   requests move between several UPI IDs and an account; "fee to withdraw" at the end. SEBI describes this pattern:
   unsolicited WhatsApp group invitations, impersonation of SEBI-registered intermediaries and public figures, fake
   profit testimonials, and money induced into the scammers' bank accounts [2].
2. **QR code and voice notes to rush the payment (scenarios C and the QR demo).** A QR code whose embedded payee name
   (typed by the scammer) differs from the firm; voice notes that sound like a real advisor; "today only" pressure.
   VERIQ reads the UPI ID inside the QR and treats the voice only as a review cue.
3. **Genuine broker, mismatched-looking name (scenario D).** A real broker's account shows a short trading name in the
   bank app. A tool that accused on name alone would harm a genuine user; VERIQ sends it to human review and shows how
   it is cleared.

## How victims get hurt today (sourced; numbers are as reported, not verified by us)
- Indians lost **Rs 11,333 crore** to cyber fraud in 2024 as reported in November 2024; **stock-trading scams: Rs 4,636
  crore from 2,28,094 complaints**, **investment scams: Rs 3,216 crore from 1,00,360 cases** [1] (The Wire, citing The
  Indian Express; the exact period covered: needs source check against the I4C/MHA original).
- SEBI's press release of 21 May 2025 warns of exactly the group-plus-impersonation pattern above [2].
- Regulators now expose the *payee name* before money moves: verified recipient names in UPI from 30 June 2025 [4],
  beneficiary-name look-up for RTGS/NEFT [5], and SEBI's validated **@valid** UPI handles with the **SEBI Check** tool
  for payments to registered intermediaries [3]. VERIQ's core check builds on this: the name *the user's own app*
  shows, compared with the firm the chat claims to be.
- How many victims could have been stopped by a payee-name check: **needs source** (we have no data on this).

## Sources
[1] The Wire, "India lost Rs 11,333 crore to cyber fraud in 2024", 28 Nov 2024: https://thewire.in/tech/india-lost-rs-11333-crore-to-cyber-fraud-in-2024
[2] SEBI press release PR No. 27/2025, 21 May 2025 (copy hosted by HDFC AMC): https://files.hdfcfund.com/s3fs-public/inline-files/2025-05-21-SEBI%20Press%20Release%20%282%29.pdf
[3] Business Standard, "Curbing frauds: Sebi brings more checks for investors via valid UPI handle", 12 Jun 2025: https://www.business-standard.com/amp/markets/news/curbing-frauds-sebi-brings-more-checks-for-investors-via-valid-upi-handle-125061201126_1.html
[4] Outlook Money, "UPI to display verified names of recipients from June 30, 2025": https://www.outlookmoney.com/banking/upi-to-display-verified-names-of-recipients-from-june-30-2025
[5] Business Standard, "RBI proposes look-up facility for NEFT/RTGS; banks to comply by April 1": https://www.business-standard.com/economy/news/rbi-proposes-lookup-facility-for-neft-rtgs-banks-to-comply-by-april-1-124123000984_1.html
Secondary sources were used where the primary document was not reachable from our build environment; check the primary
(I4C/MHA, SEBI, NPCI, RBI) before quoting a number on stage.
