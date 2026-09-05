"""Explainable keyword and regex patterns for refund-scam social engineering.

Deliberately rule-based: every detection maps back to the exact phrase that
triggered it, which is what makes the output defensible in an incident report.
An optional spaCy pass can be layered on later without changing this contract.
"""
from __future__ import annotations

PatternGroup = dict[str, object]

# weight = points contributed to the 0-100 message risk score when the group fires.
# Each group saturates: matching six urgency words is not six times one word.
PATTERN_GROUPS: list[PatternGroup] = [
    {
        "code": "URGENCY",
        "label": "Urgency and time pressure",
        "weight": 22,
        "patterns": [
            r"\burgent(?:ly)?\b", r"\bimmediat(?:e|ely)\b", r"\bright now\b", r"\basap\b",
            r"\bquick(?:ly)?\b", r"\bfast\b", r"\bhurry\b", r"\bemergency\b",
            r"\bwithin \d+ ?(?:min|minute|hour)", r"\bjaldi\b", r"\bturant\b",
        ],
    },
    {
        "code": "ACCIDENTAL_PAYMENT",
        "label": "Accidental payment claim",
        "weight": 24,
        "patterns": [
            r"\bby mistake\b", r"\bmistakenly\b", r"\baccident(?:al|ally|ly)?\b",
            r"\bwrong (?:number|account|upi|person|id)\b", r"\bwrongly (?:sent|transferred)\b",
            r"\bsent (?:it |the money |amount )?to you by\b", r"\bgalti se\b",
        ],
    },
    {
        "code": "THIRD_PARTY_DESTINATION",
        "label": "Money requested to a different account",
        "weight": 25,
        "patterns": [
            r"\bmy (?:wife|husband|brother|sister|friend|father|mother|son|daughter|partner)'?s? (?:upi|account|number|gpay|paytm|phonepe)\b",
            r"\bsend (?:it )?to (?:this|another|different|new) (?:upi|account|number|id)\b",
            r"\bdifferent (?:upi|account|number)\b",
            r"\banother (?:upi|account|number)\b",
            r"\buse this (?:upi|id|number)\b",
        ],
    },
    {
        "code": "REFUND_REQUEST",
        "label": "Request to return money manually",
        "weight": 18,
        "patterns": [
            r"\breturn (?:the |my )?(?:money|amount|payment|funds)\b",
            r"\bsend (?:it |the money |amount )?back\b", r"\brefund\b",
            r"\bgive (?:it |the money )?back\b", r"\bpay(?: it)? back\b",
            r"\bwapas\b", r"\btransfer (?:it |the amount )?back\b",
        ],
    },
    {
        "code": "PRESSURE",
        "label": "Emotional pressure or guilt",
        "weight": 16,
        "patterns": [
            r"\bplease+ (?:help|sir|madam|bro|bhai)\b", r"\bi will lose\b", r"\bmy job\b",
            r"\bhospital\b", r"\bmedical\b", r"\bfamily\b", r"\bbeg(?:ging)?\b",
            r"\btrust me\b", r"\bgood (?:person|man|human)\b", r"\bhelp me\b",
        ],
    },
    {
        "code": "AUTHORITY_IMPERSONATION",
        "label": "Claimed authority or official identity",
        "weight": 20,
        "patterns": [
            r"\bbank (?:officer|official|executive|manager)\b", r"\bcustomer (?:care|support)\b",
            r"\bcyber ?(?:cell|crime|police)\b", r"\bpolice\b", r"\bfir\b",
            r"\blegal action\b", r"\bcomplaint (?:will|has) be(?:en)? (?:filed|registered)\b",
            r"\baccount will be (?:frozen|blocked|suspended)\b", r"\brbi\b", r"\bnpci\b",
        ],
    },
    {
        "code": "ACCOUNT_EXCUSE",
        "label": "Excuse for why the original account cannot be used",
        "weight": 14,
        "patterns": [
            r"\baccount (?:is |isn'?t |not )?(?:working|blocked|frozen|closed|deactivated)\b",
            r"\bupi (?:is |not )?(?:working|down|failing)\b",
            r"\bcan'?t receive\b", r"\bunable to receive\b", r"\bapp (?:is )?not working\b",
        ],
    },
    {
        "code": "CREDENTIAL_REQUEST",
        "label": "Request for credentials or codes",
        "weight": 30,
        "patterns": [
            r"\botp\b", r"\bupi pin\b", r"\bmpin\b", r"\bcvv\b", r"\bpassword\b",
            r"\bshare (?:the )?code\b", r"\bscan (?:this )?(?:qr|code)\b",
            r"\bcollect request\b", r"\bapprove (?:the )?request\b",
        ],
    },
    {
        "code": "OFF_PLATFORM",
        "label": "Push to move the conversation off-platform",
        "weight": 10,
        "patterns": [
            r"\bwhatsapp me\b", r"\bcall me on\b", r"\btelegram\b",
            r"\bdon'?t tell\b", r"\bkeep (?:this )?between us\b",
            r"\b(?:message|msg|dm|contact|ping) me on\b", r"\bon whats ?app\b",
            r"\bwhats ?app (?:par|pe|number)\b",
        ],
    },
    {
        # The scam only works if the victim leaves the refund rail, so a message
        # that argues for leaving it is the clearest signal there is. Scanning a
        # QR to "receive" money is the same move: in UPI, scanning pays out.
        "code": "RAIL_BYPASS",
        "label": "Pushed to bypass the app's own refund",
        "weight": 22,
        "patterns": [
            r"\b(?:do not|don'?t|na)\s+(?:use|refund|return|send)\s+(?:it\s+)?(?:through|via|from|using)?\s*the\s+app\b",
            r"\bdon'?t use (?:the )?(?:app|refund)\b",
            r"\bscan (?:the |this |my )?(?:qr|code)\b", r"\bqr code\b",
            r"\bscan karo\b", r"\bqr bhej\b",
            r"\b(?:click|open|use) (?:this|the) link\b",
            r"\brefund (?:option|button) (?:will|may) (?:not work|fail|lock)\b",
            r"\bwill lock the (?:amount|money|funds)\b",
        ],
    },
]

# Phrases that reduce risk: normal, benign settlement language between known parties.
MITIGATING_PATTERNS: list[tuple[str, str, int]] = [
    ("KNOWN_CONTEXT", r"\b(?:as discussed|as agreed|invoice|order id|order no|booking)\b", 8),
    ("SAME_ACCOUNT", r"\b(?:same (?:upi|account)|original account|source account)\b", 10),
]
