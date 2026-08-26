import json
import pytest

from retail_configuration_lab.automation import (
    ActionType, AutomationValidationError, ExecutionStatus, TriggerType,
    configuration_from_dict, load_automation_configuration, missing_return_reason,
    missing_transfer_receipt, run_automation_experiment, validate_mapping,
)
from retail_configuration_lab.returns_transfers import load_returns_transfers_records


def test_configuration_and_vocabulary_load():
    config=load_automation_configuration()
    assert len(config.automations)==6
    assert len({x.automation_id for x in config.automations})==6
    assert {TriggerType(x.trigger["type"]) for x in config.automations}
    assert {ActionType(x.action["type"]) for x in config.automations}


def test_transfer_and_return_conditions_have_no_false_alerts():
    returns,transfers,_=load_returns_transfers_records()
    assert missing_transfer_receipt(next(x for x in transfers if x.transfer_id=="JRO-TR-1007"))
    assert not missing_transfer_receipt(next(x for x in transfers if x.transfer_id=="JRO-TR-1001"))
    assert missing_return_reason(next(x for x in returns if x.return_id=="JRO-RET-1008"))
    assert not missing_return_reason(next(x for x in returns if x.return_id=="JRO-RET-1001"))


def test_mapping_validation_never_guesses_and_valid_mapping_passes():
    assert validate_mapping("UNKNOWN",())
    assert validate_mapping("SHIRT-M",("A","B"))["canonical_id"]=="UNRESOLVED"
    assert validate_mapping("KNOWN",("JRO-1042-BLU-M",)) is None


def test_outcomes_retry_idempotency_and_existing_routine_trigger():
    result=run_automation_experiment(); counts=result.counts
    assert result.reconciliation_runs==1 and len(result.distributions)==1
    assert counts[ExecutionStatus.DUPLICATE_SUPPRESSED]==1
    assert any(x.status is ExecutionStatus.SUCCEEDED and x.attempt_count==2 for x in result.executions)
    assert counts[ExecutionStatus.RETRY_EXHAUSTED]==1
    assert counts[ExecutionStatus.BLOCKED_BY_VALIDATION]==1


def test_before_after_metrics_and_residual_problems():
    result=run_automation_experiment()
    assert result.configuration.manual_steps_before==6
    assert result.configuration.manual_steps_after==2
    assert result.manual_step_reduction_ratio==pytest.approx(4/6)
    assert result.automation_success_rate==pytest.approx(6/7)
    returns,transfers,_=load_returns_transfers_records()
    assert missing_transfer_receipt(next(x for x in transfers if x.transfer_id=="JRO-TR-1007"))
    assert missing_return_reason(next(x for x in returns if x.return_id=="JRO-RET-1008"))


def test_configuration_rejects_duplicate_and_invalid_contract(tmp_path):
    raw=json.loads((__import__('pathlib').Path('config/automation/automations.json')).read_text())
    raw["automations"].append(dict(raw["automations"][0]))
    with pytest.raises(AutomationValidationError): configuration_from_dict(raw)
    raw.pop("automations"); raw["automations"]=[{"automation_id":"bad","automation_type":"NOPE"}]
    with pytest.raises(AutomationValidationError): configuration_from_dict(raw)


def test_question_impacts_are_conservative():
    impacts={qid:status.value for qid,status,_ in run_automation_experiment().question_impacts}
    assert impacts["MGT-01"]=="PARTIALLY_ANSWERED"
    assert impacts["PUR-01"]=="PARTIALLY_ANSWERED"
