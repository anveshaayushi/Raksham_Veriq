"""Plain-language result labels and next steps, English and Hindi (keys = core.schemas DECISION_RESULTS).

FINALE, 24 Oct 2026. Claude A's bilingual templates, ported onto the contract's result names by Claude C (CR-C13).
The Hindi text is machine-drafted and must be checked by a Hindi speaker before it is shown to users.
"""

from core.schemas import NOT_A_GUARANTEE

NEXT_STEP = {
    "LINKED": "Don't pay. Other people independently reported this payee. If money was sent, call 1930 now.",
    "NAME_DISCREPANCY": "Pause: don't pay until you verify. Contact the organisation through a number or website you "
                        "find yourself, not one from this chat. If money was sent, call 1930.",
    "REGISTRATION_CONFLICT": "Don't pay yet. The registration quoted in the chat doesn't match the dated public list. "
                             "Check it yourself on SEBI's website. If money was sent, call 1930.",
    "HUMAN_REVIEW": "Don't pay yet. Something here needs a person to look at it. Contact the firm through a number "
                    "or website you find yourself. If money was sent, call 1930.",
    "INCONCLUSIVE": "Don't pay yet. Find the firm's contact yourself, not from the chat. If money was sent, call 1930.",
    "NO_MAJOR_ISSUE": f"Checks run found no major issue. {NOT_A_GUARANTEE} Before paying, confirm the firm's contact "
                      "details through a number or website you find yourself.",
}

LABEL = {
    "LINKED": {"en": "Reported by other people", "hi": "दूसरे लोगों ने इसकी शिकायत की है"},
    "NAME_DISCREPANCY": {"en": "Payee name doesn't match the firm", "hi": "प्राप्तकर्ता का नाम कंपनी से मेल नहीं खाता"},
    "REGISTRATION_CONFLICT": {"en": "Registration doesn't match the public list",
                              "hi": "पंजीकरण सार्वजनिक सूची से मेल नहीं खाता"},
    "HUMAN_REVIEW": {"en": "Needs a person to review", "hi": "किसी व्यक्ति द्वारा जाँच ज़रूरी"},
    "INCONCLUSIVE": {"en": "Not enough evidence yet", "hi": "अभी पर्याप्त प्रमाण नहीं"},
    "NO_MAJOR_ISSUE": {"en": "No major issue found", "hi": "कोई बड़ी समस्या नहीं मिली"},
}

NEXT_STEP_HI = {
    "LINKED": "भुगतान न करें। दूसरे लोगों ने अलग-अलग इस प्राप्तकर्ता की शिकायत की है। पैसे भेज दिए हों तो तुरंत 1930 पर कॉल करें।",
    "NAME_DISCREPANCY": "रुकें: जाँच किए बिना भुगतान न करें। कंपनी से उस नंबर या वेबसाइट पर संपर्क करें जो आपने खुद ढूँढी हो, इस चैट से नहीं। पैसे भेज दिए हों तो 1930 पर कॉल करें।",
    "REGISTRATION_CONFLICT": "अभी भुगतान न करें। चैट में दिया पंजीकरण सार्वजनिक सूची से मेल नहीं खाता। SEBI की वेबसाइट पर खुद जाँचें। पैसे भेज दिए हों तो 1930 पर कॉल करें।",
    "HUMAN_REVIEW": "अभी भुगतान न करें। इसे किसी व्यक्ति को देखना होगा। पैसे भेज दिए हों तो 1930 पर कॉल करें।",
    "INCONCLUSIVE": "अभी भुगतान न करें। कंपनी का संपर्क खुद ढूँढें, चैट से नहीं। पैसे भेज दिए हों तो 1930 पर कॉल करें।",
    "NO_MAJOR_ISSUE": "जाँच में कोई बड़ी समस्या नहीं मिली। यह कोई गारंटी नहीं है। भुगतान से पहले कंपनी का संपर्क खुद ढूँढकर पुष्टि करें।",
}
