import json
from decimal import Decimal
import pytest
from retail_configuration_lab.models import CapabilityStatus
from retail_configuration_lab.strong_native_suite import (DATA_PATH, AnswerStatus, CustomRelevance,
    ReconciliationStatus, ScenarioVerdict, StrongSuiteValidationError, derive_verdict, load_strong_native_suite)


def test_scenario_coverage_accounting_costs_and_verdict():
    s=load_strong_native_suite()
    native={CapabilityStatus.SUPPORTED,CapabilityStatus.SUPPORTED_WITH_CONFIGURATION,CapabilityStatus.SUPPORTED_WITH_NATIVE_INTEGRATION}
    assert sum(c['status'] in native for c in s.capabilities) > 30
    assert {CapabilityStatus.GAP,CapabilityStatus.UNKNOWN} <= {c['status'] for c in s.capabilities}
    by_type={x.record_type:x for x in s.accounting_results if x.status is ReconciliationStatus.RECONCILED}
    assert {'SALES','RETURN','PURCHASING'} <= by_type.keys()
    assert any(x.status is ReconciliationStatus.EXCEPTION for x in s.accounting_results)
    fin=next(x for x in s.question_comparisons if x['question_id']=='FIN-01')
    assert (fin['base_status'],fin['strong_status']) == (AnswerStatus.PARTIALLY_ANSWERED,AnswerStatus.ANSWERED)
    assert (s.total_questions,s.base_questions_answered,s.strong_questions_answered,s.strong_suite_question_gain)==(16,11,15,4)
    assert s.strong_questions_answered >= s.base_questions_answered
    assert s.base_residual_operational_burden == Decimal('50920.00')
    assert s.strong_residual_operational_burden == Decimal('11300.00')
    assert s.administration_cost == Decimal('18000.00') and s.recurring_platform_cost == Decimal('90000.00')
    assert s.setup_migration_cost == Decimal('92000.00')
    assert s.custom_relevance is CustomRelevance.NARROW_TECHNICAL_EDGE
    assert derive_verdict(s)[0] is ScenarioVerdict.BUY_CONFIGURE
    assert s.overall_lab_verdict == 'UNTESTED'


def mutated(tmp_path, change):
    data=json.loads(DATA_PATH.read_text()); change(data); p=tmp_path/'bad.json';p.write_text(json.dumps(data));return p


def test_negative_migration_rejected(tmp_path):
    p=mutated(tmp_path,lambda d:d['costs']['setup_migration'].__setitem__('migration','-1'))
    with pytest.raises(StrongSuiteValidationError): load_strong_native_suite(p)


def test_invalid_question_reference_rejected(tmp_path):
    p=mutated(tmp_path,lambda d:d['question_comparisons'][0].__setitem__('question_id','NOPE'))
    with pytest.raises(StrongSuiteValidationError): load_strong_native_suite(p)


def test_cli(capsys):
    from retail_configuration_lab.cli import main
    assert main(['strong-native-suite']) == 0
    out=capsys.readouterr().out
    for text in ('Base configured ecosystem answered','Strong native suite answered','Base residual operational burden',
                 'Strong-suite platform cash cost','Scenario verdict:','Overall lab verdict: UNTESTED'):
        assert text in out
