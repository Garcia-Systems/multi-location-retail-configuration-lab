import copy
import json
import subprocess
import sys

import pytest

from retail_configuration_lab.capabilities import load_inventory
from retail_configuration_lab.cli import main
from retail_configuration_lab.models import (FreshnessRequirement, QuestionCoverageStatus, QuestionScope)
from retail_configuration_lab.questions import (DEFAULT_QUESTIONS_PATH, BusinessQuestionError, analyze_questions, load_questions, questions_from_dict)


def raw_questions(): return json.loads(DEFAULT_QUESTIONS_PATH.read_text(encoding="utf-8"))

def test_fixture_loads_and_requirements_are_complete():
    inventory = load_questions()
    assert len(inventory.questions) == 16
    assert len({q.question_id for q in inventory.questions}) == 16
    assert all(q.primary_owner and q.decision_action and q.required_evidence for q in inventory.questions)
    assert all(isinstance(q.freshness, FreshnessRequirement) and isinstance(q.scope, QuestionScope) for q in inventory.questions)

def test_capabilities_resolve_and_coverage_counts_match():
    questions = load_questions(); known = {x.capability.identifier for x in load_inventory().assessments}
    assert all(set(q.related_capability_ids) <= known for q in questions.questions)
    result = analyze_questions(questions)
    assert result.count_by_coverage_status == {
        QuestionCoverageStatus.DIRECT: 2, QuestionCoverageStatus.PARTIAL: 2,
        QuestionCoverageStatus.MULTIPLE_CAPABILITIES_REQUIRED: 9,
        QuestionCoverageStatus.NO_KNOWN_CAPABILITY: 2, QuestionCoverageStatus.UNKNOWN: 1,
    }
    assert not result.quality_failures

@pytest.mark.parametrize("coverage,caps,error", [
    ("DIRECT", [], "DIRECT coverage requires"),
    ("MULTIPLE_CAPABILITIES_REQUIRED", ["sales-store"], "at least two"),
    ("NO_KNOWN_CAPABILITY", ["sales-store"], "cannot claim related"),
])
def test_coverage_relationships_are_validated(coverage,caps,error):
    raw=raw_questions(); raw["business_questions"][0]["coverage_status"]=coverage; raw["business_questions"][0]["related_capability_ids"]=caps
    with pytest.raises(BusinessQuestionError, match=error): questions_from_dict(raw)

def test_invalid_capability_reference_is_rejected():
    raw=raw_questions(); raw["business_questions"][0]["related_capability_ids"]=["not-real"]
    with pytest.raises(BusinessQuestionError, match="nonexistent Chapter 1 capability"): questions_from_dict(raw)

def test_duplicate_question_ids_are_rejected():
    raw=raw_questions(); duplicate=copy.deepcopy(raw["business_questions"][0]); raw["business_questions"].append(duplicate)
    with pytest.raises(BusinessQuestionError, match="duplicate question ID"): questions_from_dict(raw)

def test_questions_cli_and_filters(capsys):
    assert main(["questions"]) == 0; output=capsys.readouterr().out
    assert "Current lab verdict: UNTESTED" in output
    assert "not evidence that the business question has been solved" in output
    assert main(["questions","--area","inventory"]) == 0
    filtered=capsys.readouterr().out.split("Question inventory (filtered questions)",1)[1]
    assert "INV-01" in filtered and "SAL-01" not in filtered
    assert main(["questions","--coverage","NO_KNOWN_CAPABILITY"]) == 0
    filtered=capsys.readouterr().out.split("Question inventory (filtered questions)",1)[1]
    assert "SAL-03" in filtered and "INV-01" not in filtered

def test_module_questions_command_exits_successfully():
    result=subprocess.run([sys.executable,"-m","retail_configuration_lab","questions"],capture_output=True,text=True)
    assert result.returncode == 0 and "Business questions: 16" in result.stdout
