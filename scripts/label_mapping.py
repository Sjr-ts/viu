"""NightEyes label mapping module.

Explicit rules for converting (or refusing to convert) original dataset
labels into NightEyes standardized states. No automatic conversion is
performed without a registered rule. Unknown labels return PENDING.

States (NightEyes V0.1):
    PRESENT, ABSENT, UNCERTAIN, UNOBSERVABLE

Mapping decisions:
    ALLOWED, PENDING, REJECTED, FORBIDDEN

See documentation/label_mapping_rules.md for the human-readable spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

NIGHTEYES_STATES = ("PRESENT", "ABSENT", "UNCERTAIN", "UNOBSERVABLE")

COMPATIBILITY_LEVELS = (
    "DIRECT",
    "PARTIAL",
    "COMPLEMENTARY",
    "INCOMPATIBLE",
    "UNVERIFIED",
)

DECISION_STATES = ("ALLOWED", "PENDING", "REJECTED", "FORBIDDEN")

DOMAINS = ("FATIGUE", "SLEEPINESS", "DISTRACTION", "QUALITY")

# Behavior codes must match documentation/behavior_dictionary.csv
BEHAVIOR_DOMAIN = {
    "EYE_001": "FATIGUE",
    "EYE_002": "FATIGUE",
    "EYE_003": "FATIGUE",
    "EYE_004": "FATIGUE",
    "SLEEP_001": "SLEEPINESS",
    "SLEEP_002": "SLEEPINESS",
    "SLEEP_003": "SLEEPINESS",
    "SLEEP_004": "SLEEPINESS",
    "DIST_001": "DISTRACTION",
    "DIST_002": "DISTRACTION",
    "DIST_003": "DISTRACTION",
    "DIST_004": "DISTRACTION",
    "QUALITY_001": "QUALITY",
    "QUALITY_002": "QUALITY",
    "QUALITY_003": "QUALITY",
    "QUALITY_004": "QUALITY",
}

# Forbidden signal sources (NightEyes V0.1 section 7 - ground truth independence)
FORBIDDEN_SIGNALS = (
    "EAR",
    "MAR",
    "PERCLOS",
    "BLINK_RATE_ENGINE",
    "FATIGUE_SCORE",
    "SLEEPINESS_SCORE",
    "DISTRACTION_SCORE",
    "RISK_CLASSIFICATION",
)


@dataclass(frozen=True)
class MappingRule:
    """A single registered conversion rule."""

    rule_id: str
    dataset_id: str
    source_label: str  # normalized (case-insensitive match)
    target_domain: str
    target_behavior: str
    decision: str  # ALLOWED | PENDING | REJECTED | FORBIDDEN
    compatibility_level: str
    case_ref: str  # CASO 1..5 or "-"
    conditions: tuple = field(default_factory=tuple)

    def matches(self, dataset_id: str, source_label: str,
                target_domain: str, target_behavior: str) -> bool:
        if self.dataset_id not in ("*", dataset_id):
            return False
        if self.source_label.lower() != source_label.strip().lower():
            return False
        if self.target_domain not in ("*", target_domain):
            return False
        if self.target_behavior not in ("*", target_behavior):
            return False
        return True


@dataclass(frozen=True)
class MappingDecision:
    """Result of evaluating a mapping request."""

    dataset_id: str
    source_label: str
    target_domain: str
    target_behavior: str
    decision: str
    compatibility_level: str
    case_ref: str
    conditions: tuple
    rule_id: Optional[str]
    notes: str


# ---------------------------------------------------------------------------
# Registered rules (documentation/label_mapping_rules.md section 4)
# ---------------------------------------------------------------------------

RULES: tuple[MappingRule, ...] = (
    MappingRule(
        "R001", "*", "drowsy", "SLEEPINESS", "SLEEP_001", "PENDING", "PARTIAL",
        "CASO 1",
        ("Video/session-level label must not become PRESENT for all windows",
         "Requires episode-level human reannotation"),
    ),
    MappingRule(
        "R002", "*", "low vigilant", "SLEEPINESS", "SLEEP_001", "PENDING",
        "PARTIAL", "CASO 1",
        ("Video-level KSS-based state", "Requires episode-level human reannotation"),
    ),
    MappingRule(
        "R003", "*", "alert", "SLEEPINESS", "SLEEP_001", "PENDING", "PARTIAL",
        "CASO 1",
        ("Negative reference only after visual verification",),
    ),
    MappingRule(
        "R004", "*", "sleepy driving", "SLEEPINESS", "SLEEP_001", "PENDING",
        "PARTIAL", "CASO 1",
        ("Scripted activity label", "Requires episode-level human reannotation"),
    ),
    MappingRule(
        "R005", "*", "kss", "SLEEPINESS", "SLEEP_004", "ALLOWED",
        "COMPLEMENTARY", "CASO 2",
        ("Store separately from visual observation",
         "Never convert directly to visual PRESENT"),
    ),
    MappingRule(
        "R006", "*", "yawning", "SLEEPINESS", "SLEEP_003", "PENDING",
        "PARTIAL", "CASO 3",
        ("Preserve original interval", "Perform temporal verification",
         "New episode annotation if source has no temporal labels"),
    ),
    MappingRule(
        "R007", "*", "yawn", "SLEEPINESS", "SLEEP_003", "PENDING", "PARTIAL",
        "CASO 3",
        ("Preserve original interval", "Perform temporal verification"),
    ),
    MappingRule(
        "R008", "*", "phone visible", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Phone presence is not distraction",
         "DIST_003 records presence only - never PRESENT distraction"),
    ),
    MappingRule(
        "R009", "*", "phone presence", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Phone presence is not distraction"),
    ),
    MappingRule(
        "R010", "*", "phone right", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "CASO 4",
        ("Usage class - requires verified attention deviation in same interval"),
    ),
    MappingRule(
        "R011", "*", "phone left", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "CASO 4",
        ("Usage class - requires verified attention deviation in same interval"),
    ),
    MappingRule(
        "R012", "*", "text right", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "CASO 4",
        ("Usage class - requires verified attention deviation in same interval"),
    ),
    MappingRule(
        "R013", "*", "text left", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "CASO 4",
        ("Usage class - requires verified attention deviation in same interval"),
    ),
    MappingRule(
        "R014", "*", "talking on phone", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "CASO 4",
        ("Usage class - requires verified attention deviation in same interval"),
    ),
    MappingRule(
        "R015", "*", "texting", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "CASO 4",
        ("Usage class - requires verified attention deviation in same interval"),
    ),
    MappingRule(
        "R016", "*", "talking and laughing", "DISTRACTION", "DIST_001",
        "REJECTED", "INCOMPATIBLE", "-",
        ("Does not match NightEyes distraction indicators"),
    ),
    MappingRule(
        "R017", "*", "talking or singing", "DISTRACTION", "DIST_001",
        "REJECTED", "UNVERIFIED", "-",
        ("Class name does not establish attention deviation"),
    ),
    MappingRule(
        "R018", "*", "gaze on road", "DISTRACTION", "DIST_001", "PENDING",
        "PARTIAL", "-",
        ("Align persistence definition before use"),
    ),
    MappingRule(
        "R019", "*", "eyes: sleepy", "FATIGUE", "EYE_002", "PENDING",
        "PARTIAL", "-",
        ("Verify thresholds in source annotation files"),
    ),
    MappingRule(
        "R020", "*", "eyes: sleepy", "SLEEPINESS", "SLEEP_001", "PENDING",
        "PARTIAL", "-",
        ("Verify thresholds in source annotation files"),
    ),
    MappingRule(
        "R021", "*", "head: looking aside", "DISTRACTION", "DIST_002",
        "PENDING", "PARTIAL", "-",
        ("Persistence requirement not encoded in source labels"),
    ),
    MappingRule(
        "R022", "*", "head: nodding", "SLEEPINESS", "SLEEP_001", "PENDING",
        "COMPLEMENTARY", "-",
        ("Complementary drowsiness evidence only"),
    ),
    MappingRule(
        "R023", "*", "microsleep", "SLEEPINESS", "SLEEP_001", "PENDING",
        "PARTIAL", "CASO 1",
        ("Scripted/session-scoped - requires episode verification"),
    ),
    MappingRule(
        "R024", "*", "session condition: drowsy", "SLEEPINESS", "SLEEP_001",
        "PENDING", "PARTIAL", "CASO 1",
        ("Session-level condition - requires episode reannotation"),
    ),
    MappingRule(
        "R025", "*", "session condition: awake", "SLEEPINESS", "SLEEP_001",
        "PENDING", "PARTIAL", "CASO 1",
        ("Session-level condition - requires episode reannotation"),
    ),
    MappingRule(
        "R026", "*", "safe driving", "DISTRACTION", "DIST_004", "PENDING",
        "PARTIAL", "-",
        ("Negative reference - verify absence of phone usage visually"),
    ),
    MappingRule(
        "R027", "*", "c1 texting - right", "DISTRACTION", "DIST_004",
        "PENDING", "PARTIAL", "CASO 4",
        ("Image-level usage class - attention deviation unverified"),
    ),
    MappingRule(
        "R028", "*", "c3 texting - left", "DISTRACTION", "DIST_004",
        "PENDING", "PARTIAL", "CASO 4",
        ("Image-level usage class - attention deviation unverified"),
    ),
    MappingRule(
        "R029", "*", "c2 talking on phone - right", "DISTRACTION", "DIST_004",
        "PENDING", "PARTIAL", "CASO 4",
        ("Image-level usage class - attention deviation unverified"),
    ),
    MappingRule(
        "R030", "*", "c4 talking on phone - left", "DISTRACTION", "DIST_004",
        "PENDING", "PARTIAL", "CASO 4",
        ("Image-level usage class - attention deviation unverified"),
    ),
    # Hard prohibitions (ground truth independence)
    MappingRule(
        "R031", "*", "ear", "*", "*", "FORBIDDEN", "INCOMPATIBLE", "V0.1-7",
        ("Engine EAR must never define reference labels",),
    ),
    MappingRule(
        "R032", "*", "mar", "*", "*", "FORBIDDEN", "INCOMPATIBLE", "V0.1-7",
        ("Engine MAR must never define reference labels",),
    ),
    MappingRule(
        "R033", "*", "perclos", "*", "*", "FORBIDDEN", "INCOMPATIBLE",
        "V0.1-7",
        ("Engine PERCLOS must never define reference labels",),
    ),
    MappingRule(
        "R034", "*", "fatigue score", "*", "*", "FORBIDDEN", "INCOMPATIBLE",
        "V0.1-7",
        ("Engine scores must never define reference labels",),
    ),
    MappingRule(
        "R035", "*", "sleepiness score", "*", "*", "FORBIDDEN",
        "INCOMPATIBLE", "V0.1-7",
        ("Engine scores must never define reference labels",),
    ),
    MappingRule(
        "R036", "*", "distraction score", "*", "*", "FORBIDDEN",
        "INCOMPATIBLE", "V0.1-7",
        ("Engine scores must never define reference labels",),
    ),
    MappingRule(
        "R037", "*", "risk classification", "*", "*", "FORBIDDEN",
        "INCOMPATIBLE", "V0.1-7",
        ("Global risk class must never define reference labels",),
    ),
    # Usage labels must never be encoded as mere phone presence (CASO 4)
    MappingRule(
        "R038", "*", "phone right", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Usage label cannot be mapped to presence code DIST_003",),
    ),
    MappingRule(
        "R039", "*", "phone left", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Usage label cannot be mapped to presence code DIST_003",),
    ),
    MappingRule(
        "R040", "*", "text right", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Usage label cannot be mapped to presence code DIST_003",),
    ),
    MappingRule(
        "R041", "*", "text left", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Usage label cannot be mapped to presence code DIST_003",),
    ),
    MappingRule(
        "R042", "*", "talking on phone", "DISTRACTION", "DIST_003",
        "REJECTED", "INCOMPATIBLE", "CASO 4",
        ("Usage label cannot be mapped to presence code DIST_003",),
    ),
    MappingRule(
        "R043", "*", "texting", "DISTRACTION", "DIST_003", "REJECTED",
        "INCOMPATIBLE", "CASO 4",
        ("Usage label cannot be mapped to presence code DIST_003",),
    ),
)


def evaluate_mapping(
    dataset_id: str,
    source_label: str,
    target_domain: str,
    target_behavior: str,
) -> MappingDecision:
    """Evaluate a requested label conversion.

    Returns a MappingDecision. Unknown labels yield decision=PENDING with an
    explanatory note - never a silent conversion.
    """
    # Validation of inputs
    if target_domain not in DOMAINS:
        return MappingDecision(
            dataset_id, source_label, target_domain, target_behavior,
            "REJECTED", "INCOMPATIBLE", "-",
            ("Invalid target domain",), None,
            f"Invalid target domain '{target_domain}'.",
        )
    expected_domain = BEHAVIOR_DOMAIN.get(target_behavior)
    if expected_domain is None:
        return MappingDecision(
            dataset_id, source_label, target_domain, target_behavior,
            "REJECTED", "INCOMPATIBLE", "-",
            ("Unknown behavior code",), None,
            f"Unknown behavior code '{target_behavior}'.",
        )
    if expected_domain != target_domain:
        return MappingDecision(
            dataset_id, source_label, target_domain, target_behavior,
            "REJECTED", "INCOMPATIBLE", "-",
            ("Behavior/domain mismatch",), None,
            f"Behavior '{target_behavior}' belongs to domain "
            f"'{expected_domain}', not '{target_domain}'.",
        )

    # Forbidden signal check (any mention of engine signals)
    lowered = source_label.strip().lower()
    tokens = lowered.replace("_", " ").replace("-", " ").split()
    for sig in FORBIDDEN_SIGNALS:
        sig_norm = sig.lower().replace("_", " ")
        hit = (
            lowered == sig_norm
            or (len(sig_norm.split()) == 1 and sig_norm in tokens)
            or (len(sig_norm.split()) > 1 and sig_norm in lowered)
        )
        if hit:
            return MappingDecision(
                dataset_id, source_label, target_domain, target_behavior,
                "FORBIDDEN", "INCOMPATIBLE", "V0.1-7",
                ("Ground truth independence",), None,
                f"Source label references forbidden engine signal '{sig}' "
                "(NightEyes V0.1 section 7).",
            )

    # Find first matching registered rule
    for rule in RULES:
        if rule.matches(dataset_id, source_label, target_domain,
                        target_behavior):
            return MappingDecision(
                dataset_id, source_label, target_domain, target_behavior,
                rule.decision, rule.compatibility_level, rule.case_ref,
                rule.conditions, rule.rule_id,
                f"Rule {rule.rule_id} applied.",
            )

    # No rule registered -> PENDING (never silent conversion)
    return MappingDecision(
        dataset_id, source_label, target_domain, target_behavior,
        "PENDING", "UNVERIFIED", "-",
        ("No registered conversion rule - human review required",), None,
        "No registered rule for this source label. Conversion is pending "
        "manual review (see documentation/label_mapping_rules.md).",
    )


def is_state_valid(state: str) -> bool:
    """Return True if state is a standard NightEyes label."""
    return state in NIGHTEYES_STATES


def consolidate_states(states: list) -> str:
    """Consolidate annotator states without collapsing UNCERTAIN/UNOBSERVABLE.

    Rules:
    - Any UNOBSERVABLE -> UNOBSERVABLE.
    - Any UNCERTAIN (and no UNOBSERVABLE) -> UNCERTAIN.
    - All PRESENT -> PRESENT.
    - All ABSENT -> ABSENT.
    - Mixed PRESENT/ABSENT -> UNCERTAIN (divergence unresolved).
    """
    if not states:
        return "UNCERTAIN"
    if any(s == "UNOBSERVABLE" for s in states):
        return "UNOBSERVABLE"
    if any(s == "UNCERTAIN" for s in states):
        return "UNCERTAIN"
    if all(s == "PRESENT" for s in states):
        return "PRESENT"
    if all(s == "ABSENT" for s in states):
        return "ABSENT"
    return "UNCERTAIN"


def list_rules() -> tuple:
    """Return all registered rules."""
    return RULES
