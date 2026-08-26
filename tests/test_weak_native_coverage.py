import json
from decimal import Decimal
import pytest
from retail_configuration_lab.models import CapabilityStatus
from retail_configuration_lab.strong_native_suite import load_strong_native_suite
from retail_configuration_lab.weak_native_coverage import (DATA_PATH,AnswerStatus,GapClassification,ScenarioResponse,
 WeakScenarioValidationError,derive_response,load_weak_native_coverage)

def mutate(tmp_path,fn):
 d=json.loads(DATA_PATH.read_text());fn(d);p=tmp_path/'bad.json';p.write_text(json.dumps(d));return p

def test_weak_scenario_structure_coverage_and_isolation():
 before=DATA_PATH.read_text(); strong_path=DATA_PATH.with_name('strong_native_suite.json'); strong_before=strong_path.read_text(); s=load_weak_native_coverage()
 assert DATA_PATH.read_text()==before and strong_path.read_text()==strong_before
 native={CapabilityStatus.SUPPORTED,CapabilityStatus.SUPPORTED_WITH_CONFIGURATION,CapabilityStatus.SUPPORTED_WITH_NATIVE_INTEGRATION}
 assert sum(c['status'] in native for c in s.capabilities)<sum(c['status'] in native for c in load_strong_native_suite().capabilities)
 by={c['capability_id']:c['status'] for c in s.capabilities}
 assert by['sales-store'] is CapabilityStatus.SUPPORTED and by['sales-sku'] is CapabilityStatus.SUPPORTED
 assert by['ecommerce-store-fulfillment'] is CapabilityStatus.GAP
 assert by['inventory-transfers'] is CapabilityStatus.GAP and by['accounting-reconciliation'] is CapabilityStatus.GAP
 assert any(w['workaround_type']=='EXPORT_WORKAROUND' for w in s.workarounds)
 assert (s.base_answered,s.strong_answered,s.weak_answered)==(11,15,1)
 assert s.coverage_counts=={AnswerStatus.ANSWERED:1,AnswerStatus.PARTIALLY_ANSWERED:9,AnswerStatus.NOT_ANSWERED:4,AnswerStatus.UNKNOWN:2}
 assert s.workaround_layer_count==12 and s.questions_dependent_on_workarounds==5
 assert s.workaround_dependency_ratio==Decimal(5)/Decimal(13)

def test_costs_gaps_response_and_no_custom_implementation():
 s=load_weak_native_coverage()
 assert (s.residual_operational_burden,s.support_admin_cost,s.platform_cost,s.setup_cost)==(Decimal('38200'),Decimal('48000'),Decimal('42000'),Decimal('72000'))
 assert s.annual_post_configuration_cost==Decimal('128200')
 bounded=[g for g in s.residual_gaps if g['classification'] is GapClassification.BOUNDED]
 assert bounded and bounded[0]['question_ids']==['ECOM-01','ECOM-02']
 assert any(g['classification'] is GapClassification.BROAD for g in s.residual_gaps)
 assert derive_response(s)[0] is ScenarioResponse.STANDARDIZE_FIRST and s.overall_lab_verdict=='UNTESTED'
 assert not any('adapter' in p.name or 'service' in p.name for p in DATA_PATH.parents[1].joinpath('retail_configuration_lab').iterdir())

def test_validation(tmp_path):
 with pytest.raises(WeakScenarioValidationError): load_weak_native_coverage(mutate(tmp_path,lambda d:d['workarounds'][0].__setitem__('dependency','NOPE')))
 with pytest.raises(WeakScenarioValidationError): load_weak_native_coverage(mutate(tmp_path,lambda d:d['costs'].__setitem__('annual_platform_cash','-1')))
 with pytest.raises(WeakScenarioValidationError): load_weak_native_coverage(mutate(tmp_path,lambda d:d['question_comparisons'][-2].__setitem__('weak_status','ANSWERED')))

def test_cli(capsys):
 from retail_configuration_lab.cli import main
 assert main(['weak-native-coverage'])==0; out=capsys.readouterr().out
 for text in ('Base configured ecosystem answered','Strong native suite answered','Weak native coverage answered','Workaround structure','Bounded gaps:','Broad gaps:','Scenario response: STANDARDIZE_FIRST','Overall lab verdict: UNTESTED','AUTOMATION CANNOT','BI cannot repair'):
  assert text in out
