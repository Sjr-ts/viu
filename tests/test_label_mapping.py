"""Automated tests for scripts/label_mapping.py (CASOS 1-5)."""

from __future__ import annotations

import pytest

from label_mapping import (
    consolidate_states,
    evaluate_mapping,
    is_state_valid,
    list_rules,
)


# ---------------------------------------------------------------------------
# CASO 1: drowsy must never auto-convert to PRESENT
# ---------------------------------------------------------------------------

def test_caso1_drowsy_is_pending():
    d = evaluate_mapping("SRC002", "drowsy", "SLEEPINESS", "SLEEP_001")
    assert d.decision == "PENDING"
    assert d.case_ref == "CASO 1"
    assert d.compatibility_level == "PARTIAL"


def test_caso1_video_level_labels_are_pending():
    for label in ("low vigilant", "session condition: Drowsy",
                  "Sleepy driving"):
        d = evaluate_mapping("SRC001", label, "SLEEPINESS", "SLEEP_001")
        assert d.decision == "PENDING", label


# ---------------------------------------------------------------------------
# CASO 2: KSS is complementary only
# ---------------------------------------------------------------------------

def test_caso2_kss_allowed_complementary():
    d = evaluate_mapping("SRC004", "KSS", "SLEEPINESS", "SLEEP_004")
    assert d.decision == "ALLOWED"
    assert d.compatibility_level == "COMPLEMENTARY"
    assert d.case_ref == "CASO 2"


def test_caso2_kss_cannot_target_visual_behavior():
    d = evaluate_mapping("SRC004", "KSS", "SLEEPINESS", "SLEEP_001")
    assert d.decision in ("PENDING", "REJECTED")
    assert d.decision != "ALLOWED"


# ---------------------------------------------------------------------------
# CASO 3: yawning requires temporal verification
# ---------------------------------------------------------------------------

def test_caso3_yawning_pending():
    d = evaluate_mapping("SRC003", "Yawning", "SLEEPINESS", "SLEEP_003")
    assert d.decision == "PENDING"
    assert d.case_ref == "CASO 3"
    assert "interval" in " ".join(d.conditions).lower() or \
        any("interval" in c.lower() for c in d.conditions)


def test_caso3_yawn_variant():
    d = evaluate_mapping("SRC005", "mouth: yawning", "SLEEPINESS",
                         "SLEEP_003")
    # rule matches source label 'yawn'? -> no exact match; falls back to PENDING
    assert d.decision == "PENDING"


# ---------------------------------------------------------------------------
# CASO 4: phone presence is never distraction PRESENT
# ---------------------------------------------------------------------------

def test_caso4_phone_visible_rejected():
    d = evaluate_mapping("SRC006", "Phone Visible", "DISTRACTION",
                         "DIST_003")
    assert d.decision == "REJECTED"
    assert d.case_ref == "CASO 4"


def test_caso4_phone_usage_pending():
    d = evaluate_mapping("SRC006", "Phone Right", "DISTRACTION", "DIST_004")
    assert d.decision == "PENDING"
    assert d.case_ref == "CASO 4"


def test_caso4_incompatible_usage_for_presence_behavior():
    # asking to map phone usage into DIST_003 (presence) is rejected
    d = evaluate_mapping("SRC006", "Phone Right", "DISTRACTION", "DIST_003")
    assert d.decision == "REJECTED"


# ---------------------------------------------------------------------------
# CASO 5 / unknown labels
# ---------------------------------------------------------------------------

def test_unknown_label_is_pending_never_auto():
    d = evaluate_mapping("SRC007", "some brand new label", "DISTRACTION",
                         "DIST_001")
    assert d.decision == "PENDING"
    assert d.compatibility_level == "UNVERIFIED"
    assert d.rule_id is None


def test_invalid_domain_rejected():
    d = evaluate_mapping("SRC001", "drowsy", "INTOXICATION", "SLEEP_001")
    assert d.decision == "REJECTED"


def test_behavior_domain_mismatch_rejected():
    d = evaluate_mapping("SRC001", "drowsy", "FATIGUE", "SLEEP_001")
    assert d.decision == "REJECTED"
    assert "belongs to domain" in d.notes


def test_unknown_behavior_rejected():
    d = evaluate_mapping("SRC001", "drowsy", "SLEEPINESS", "SLEEP_999")
    assert d.decision == "REJECTED"


# ---------------------------------------------------------------------------
# Ground truth independence (V0.1 section 7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label", ["EAR", "MAR", "PERCLOS", "fatigue score",
                                   "risk classification"])
def test_forbidden_engine_signals(label):
    d = evaluate_mapping("SRC001", label, "SLEEPINESS", "SLEEP_001")
    assert d.decision == "FORBIDDEN"


def test_rules_are_registered():
    rules = list_rules()
    assert len(rules) >= 10
    assert all(r.decision in
               ("ALLOWED", "PENDING", "REJECTED", "FORBIDDEN")
               for r in rules)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def test_state_validation():
    assert is_state_valid("PRESENT")
    assert is_state_valid("UNOBSERVABLE")
    assert not is_state_valid("MAYBE")
    assert not is_state_valid("true")


def test_consolidate_never_collapses_uncertain():
    assert consolidate_states(["UNCERTAIN", "PRESENT"]) == "UNCERTAIN"
    assert consolidate_states(["UNOBSERVABLE", "ABSENT"]) == "UNOBSERVABLE"
    assert consolidate_states(["PRESENT", "PRESENT"]) == "PRESENT"
    assert consolidate_states(["ABSENT", "ABSENT"]) == "ABSENT"
    assert consolidate_states(["PRESENT", "ABSENT"]) == "UNCERTAIN"
    assert consolidate_states([]) == "UNCERTAIN"
