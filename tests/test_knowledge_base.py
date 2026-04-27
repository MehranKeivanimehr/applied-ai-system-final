import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from knowledge_base import load_knowledge, retrieve_guidance


# ---------------------------------------------------------------------------
# 1. load_knowledge
# ---------------------------------------------------------------------------

def test_load_knowledge_returns_list():
    data = load_knowledge()
    assert isinstance(data, list)


def test_load_knowledge_is_nonempty():
    data = load_knowledge()
    assert len(data) > 0


def test_load_knowledge_entries_have_required_keys():
    data = load_knowledge()
    required = {"id", "species", "keywords", "title", "guidance"}
    for entry in data:
        missing = required - entry.keys()
        assert not missing, f"Entry '{entry.get('id')}' missing keys: {missing}"


# ---------------------------------------------------------------------------
# 2. retrieve_guidance — basic behaviour
# ---------------------------------------------------------------------------

def test_empty_query_returns_empty_list():
    result = retrieve_guidance("", species="dog")
    assert result == []


def test_whitespace_query_returns_empty_list():
    result = retrieve_guidance("   ", species="dog")
    assert result == []


def test_returns_list_type():
    result = retrieve_guidance("walk exercise", species="dog")
    assert isinstance(result, list)


def test_returns_at_most_top_k():
    result = retrieve_guidance("walk feed medication groom play vet", species="dog", top_k=3)
    assert len(result) <= 3


def test_custom_top_k_respected():
    result = retrieve_guidance("walk feed medication groom play vet", species="dog", top_k=2)
    assert len(result) <= 2


# ---------------------------------------------------------------------------
# 3. retrieve_guidance — keyword matching
# ---------------------------------------------------------------------------

def test_walk_query_returns_exercise_entry():
    results = retrieve_guidance("morning walk exercise", species="dog")
    titles = [r["title"].lower() for r in results]
    assert any("exercise" in t or "walk" in t for t in titles)


def test_feed_query_returns_feeding_entry():
    results = retrieve_guidance("feeding meal schedule", species="dog")
    titles = [r["title"].lower() for r in results]
    assert any("feed" in t or "meal" in t for t in titles)


def test_medication_query_returns_medication_entry():
    results = retrieve_guidance("medication pill dose", species="dog", top_k=5)
    titles = [r["title"].lower() for r in results]
    assert any("medication" in t or "med" in t for t in titles)


def test_no_matching_keywords_returns_empty():
    # Highly specific nonsense that won't match any entry
    result = retrieve_guidance("xyzzy quantum flux nonsense zzzzz", species="dog")
    assert result == []


# ---------------------------------------------------------------------------
# 4. retrieve_guidance — species filtering
# ---------------------------------------------------------------------------

def test_cat_only_entry_excluded_for_dog():
    # 'litter box' is a cat-only entry — should not appear for dog queries
    results = retrieve_guidance("litter box bathroom", species="dog")
    for r in results:
        species_list = [s.lower() for s in r["species"]]
        assert "dog" in species_list or "all" in species_list, (
            f"Cat-only entry '{r['title']}' returned for dog query"
        )


def test_dog_only_entry_excluded_for_cat():
    # 'heat safety' is a dog-only entry — should not appear for cat queries
    results = retrieve_guidance("heat pavement heatstroke", species="cat")
    for r in results:
        species_list = [s.lower() for s in r["species"]]
        assert "cat" in species_list or "all" in species_list, (
            f"Dog-only entry '{r['title']}' returned for cat query"
        )


def test_all_species_entry_appears_for_any_species():
    # Water / hydration entry has species=["all"]
    results_dog = retrieve_guidance("water drinking hydration", species="dog")
    results_cat = retrieve_guidance("water drinking hydration", species="cat")
    assert len(results_dog) > 0
    assert len(results_cat) > 0


def test_retrieved_entries_are_dicts():
    results = retrieve_guidance("walk exercise", species="dog")
    for r in results:
        assert isinstance(r, dict)


def test_retrieved_entries_contain_guidance_text():
    results = retrieve_guidance("walk exercise", species="dog")
    for r in results:
        assert "guidance" in r
        assert len(r["guidance"]) > 10
