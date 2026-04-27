import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from guardrails import check_safety, SafetyResult


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _check(text: str, species: str = "dog") -> SafetyResult:
    return check_safety(text, pet_species=species)


# ---------------------------------------------------------------------------
# 1. Safe inputs pass through cleanly
# ---------------------------------------------------------------------------

def test_safe_input_returns_not_blocked():
    result = _check("My dog needs a 30-minute walk at 8am and feeding at 6pm.")
    assert result.blocked is False


def test_safe_input_has_no_warnings():
    result = _check("Morning walk for 30 minutes, then grooming session.")
    assert result.warnings == []


def test_safe_to_proceed_property_matches_blocked():
    result = _check("Feed the cat twice daily.")
    assert result.safe_to_proceed is True
    assert result.blocked is False


# ---------------------------------------------------------------------------
# 2. Toxic substances — hard block
# ---------------------------------------------------------------------------

def test_chocolate_blocks_dog():
    result = _check("Give the dog some chocolate as a treat.", species="dog")
    assert result.blocked is True
    assert any("chocolate" in w.lower() for w in result.warnings)


def test_grapes_blocks_dog():
    result = _check("Feed Max grapes after his walk.", species="dog")
    assert result.blocked is True


def test_xylitol_blocks_dog():
    result = _check("I used xylitol gum to hide the pill.", species="dog")
    assert result.blocked is True


def test_aspirin_blocks_dog():
    result = _check("Give aspirin for joint pain.", species="dog")
    assert result.blocked is True


def test_lily_blocks_cat():
    result = _check("Put some lilies near the cat bed.", species="cat")
    assert result.blocked is True


def test_permethrin_blocks_cat():
    result = _check("Apply permethrin flea treatment to the cat.", species="cat")
    assert result.blocked is True


def test_chocolate_safe_for_rabbit_is_still_blocked():
    # Chocolate is in the rabbit toxic list too
    result = _check("Give the rabbit chocolate.", species="rabbit")
    assert result.blocked is True


# ---------------------------------------------------------------------------
# 3. Emergency symptoms — hard block
# ---------------------------------------------------------------------------

def test_seizure_blocks():
    result = _check("My dog is seizing on the floor.")
    assert result.blocked is True
    assert any("EMERGENCY" in w for w in result.warnings)


def test_not_breathing_blocks():
    result = _check("The cat is not breathing properly.")
    assert result.blocked is True


def test_collapse_blocks():
    result = _check("My dog collapsed after the walk.")
    assert result.blocked is True


def test_blue_gums_blocks():
    result = _check("The dog has blue gums and is unresponsive.")
    assert result.blocked is True


# ---------------------------------------------------------------------------
# 4. Specific dosages — soft warning only (NOT blocked)
# ---------------------------------------------------------------------------

def test_dosage_mg_warns_but_not_blocked():
    result = _check("Give 250 mg of the antibiotic twice daily.")
    assert result.blocked is False
    assert any("VET REQUIRED" in w for w in result.warnings)


def test_dosage_tablets_warns_but_not_blocked():
    result = _check("Heart medication: 1 tablet every morning at 9am.")
    assert result.blocked is False
    assert any("VET REQUIRED" in w for w in result.warnings)


def test_dosage_ml_warns_but_not_blocked():
    result = _check("Give 5 ml of the liquid medication after meals.")
    assert result.blocked is False
    assert len(result.warnings) >= 1


# ---------------------------------------------------------------------------
# 5. Vet-bypass language — hard block
# ---------------------------------------------------------------------------

def test_vet_bypass_instead_of_blocks():
    result = _check("Use honey instead of the vet for the wound.", species="dog")
    assert result.blocked is True
    assert any("GUARDRAIL" in w for w in result.warnings)


def test_vet_bypass_avoid_blocks():
    result = _check("We want to avoid the vet and handle this at home.", species="cat")
    assert result.blocked is True


def test_vet_bypass_dont_need_blocks():
    result = _check("I don't need a vet, just schedule the treatments.")
    assert result.blocked is True


# ---------------------------------------------------------------------------
# 6. Multiple issues all reported
# ---------------------------------------------------------------------------

def test_multiple_toxics_all_reported():
    result = _check("Give chocolate and grapes to the dog.", species="dog")
    assert result.blocked is True
    # Both toxic items should generate separate warnings
    assert len(result.warnings) >= 2


def test_dosage_plus_emergency_reports_both():
    result = _check("Dog is seizing — give 500 mg of phenobarbital.")
    assert result.blocked is True
    # Should have at least one emergency warning and one dosage warning
    categories = [w.split(":")[0] for w in result.warnings]
    assert any("EMERGENCY" in c for c in categories)
    assert any("VET REQUIRED" in c for c in categories)
