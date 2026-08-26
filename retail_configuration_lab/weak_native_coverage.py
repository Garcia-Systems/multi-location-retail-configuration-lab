"""Chapter 16 synthetic weak-native-coverage boundary analysis (no custom implementation)."""
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import json
from pathlib import Path
from .evidence import EvidenceCategory
from .models import CapabilityStatus
from .questions import load_questions

DATA_PATH=Path(__file__).resolve().parents[1]/'data'/'weak_native_coverage.json'
class WeakScenarioValidationError(ValueError): pass
class AnswerStatus(StrEnum):
 ANSWERED='ANSWERED'; PARTIALLY_ANSWERED='PARTIALLY_ANSWERED'; NOT_ANSWERED='NOT_ANSWERED'; UNKNOWN='UNKNOWN'
class WorkaroundType(StrEnum):
 EXPORT_WORKAROUND='EXPORT_WORKAROUND'; MAPPING_WORKAROUND='MAPPING_WORKAROUND'; AUTOMATION_WORKAROUND='AUTOMATION_WORKAROUND'; BI_WORKAROUND='BI_WORKAROUND'; MANUAL_RECONCILIATION='MANUAL_RECONCILIATION'; PROCESS_WORKAROUND='PROCESS_WORKAROUND'
class GapClassification(StrEnum):
 BOUNDED='BOUNDED'; BROAD='BROAD'; PROCESS='PROCESS'; ADMINISTRATION='ADMINISTRATION'; UNKNOWN='UNKNOWN'
class ScenarioResponse(StrEnum):
 CONFIGURE='CONFIGURE'; CONFIGURE_PLUS_AUTOMATION='CONFIGURE_PLUS_AUTOMATION'; NARROW_CUSTOM_EDGE='NARROW_CUSTOM_EDGE'; STANDARDIZE_FIRST='STANDARDIZE_FIRST'; MIGRATE_SYSTEM='MIGRATE_SYSTEM'; PROMISING_VALIDATE_IN_DISCOVERY='PROMISING_VALIDATE_IN_DISCOVERY'; ONE_OFF_CUSTOM_PROJECT='ONE_OFF_CUSTOM_PROJECT'; NO_DEAL='NO_DEAL'; INVESTIGATE='INVESTIGATE'; UNKNOWN='UNKNOWN'
def money(v,name):
 try: d=Decimal(str(v))
 except (InvalidOperation,ValueError,TypeError) as e: raise WeakScenarioValidationError(f'invalid {name}') from e
 if not d.is_finite() or d<0: raise WeakScenarioValidationError(f'{name} cannot be negative')
 return d
@dataclass(frozen=True)
class WeakScenario:
 raw:dict; capabilities:tuple; questions:tuple; workarounds:tuple; residual_gaps:tuple; setup_cost:Decimal; platform_cost:Decimal; support_admin_cost:Decimal; residual_operational_burden:Decimal; administration_burden:Decimal; unknown_burden:Decimal; response:ScenarioResponse
 @property
 def coverage_counts(self): return Counter(x['weak_status'] for x in self.questions)
 @property
 def base_answered(self): return sum(x['base_status'] is AnswerStatus.ANSWERED for x in self.questions)
 @property
 def strong_answered(self): return sum(x['strong_status'] is AnswerStatus.ANSWERED for x in self.questions)
 @property
 def weak_answered(self): return self.coverage_counts[AnswerStatus.ANSWERED]
 @property
 def workaround_layer_count(self): return len(self.workarounds)
 @property
 def questions_dependent_on_workarounds(self): return len({q for w in self.workarounds for q in w['affected_business_questions']})
 @property
 def workaround_dependency_ratio(self):
  ids=set(self.raw['cross_system_question_ids']); dependent={q for w in self.workarounds for q in w['affected_business_questions']}; return Decimal(len(ids&dependent))/Decimal(len(ids))
 @property
 def annual_post_configuration_cost(self): return self.platform_cost+self.support_admin_cost+self.residual_operational_burden
 @property
 def overall_lab_verdict(self): return 'UNTESTED'
def derive_response(s):
 broad=sum(g['classification'] is GapClassification.BROAD for g in s.residual_gaps); bounded=sum(g['classification'] is GapClassification.BOUNDED for g in s.residual_gaps)
 if broad and s.support_admin_cost>=s.platform_cost: return ScenarioResponse.STANDARDIZE_FIRST,'Broad workflow gaps coexist with permanent support/admin cost at least as high as platform cash cost.'
 if bounded==1 and broad==0: return ScenarioResponse.NARROW_CUSTOM_EDGE,'One bounded material technical residual dominates.'
 if any(g['classification'] is GapClassification.UNKNOWN for g in s.residual_gaps): return ScenarioResponse.INVESTIGATE,'Material discovery remains incomplete.'
 return ScenarioResponse.CONFIGURE_PLUS_AUTOMATION,'Residual gaps are small enough for bounded configuration and automation.'
def load_weak_native_coverage(path=DATA_PATH):
 raw=json.loads(Path(path).read_text());
 try: EvidenceCategory(raw['scenario_evidence'])
 except (KeyError,ValueError) as e: raise WeakScenarioValidationError('missing evidence classification') from e
 caps=tuple(raw.get('capabilities',())); ids=[c.get('capability_id') for c in caps]
 if None in ids or len(ids)!=len(set(ids)): raise WeakScenarioValidationError('duplicate weak-scenario capability IDs')
 for c in caps:
  try: c['status']=CapabilityStatus(c['status']); EvidenceCategory(c['evidence'])
  except (KeyError,ValueError) as e: raise WeakScenarioValidationError('invalid capability status or evidence') from e
 validq={q.question_id for q in load_questions().questions}; questions=tuple(raw.get('question_comparisons',()))
 if {q.get('question_id') for q in questions}!=validq: raise WeakScenarioValidationError('question references do not resolve')
 for q in questions:
  try:
   for k in ('base_status','strong_status','weak_status'): q[k]=AnswerStatus(q[k])
   EvidenceCategory(q['evidence'])
  except (KeyError,ValueError) as e: raise WeakScenarioValidationError('invalid question or evidence classification') from e
 layers=tuple(raw.get('workarounds',())); layerids={w.get('control_id') for w in layers}
 for w in layers:
  try: WorkaroundType(w['workaround_type']); EvidenceCategory(w['evidence'])
  except (KeyError,ValueError) as e: raise WeakScenarioValidationError('invalid workaround or missing evidence classification') from e
  if w.get('underlying_gap') not in ids or not set(w.get('affected_business_questions',()))<=validq: raise WeakScenarioValidationError('workaround reference does not resolve')
  if w.get('dependency') is not None and w['dependency'] not in layerids: raise WeakScenarioValidationError('invalid workaround dependency')
 # cycle detection
 byid={w['control_id']:w for w in layers}
 for start in byid:
  seen=set(); cur=start
  while cur:
   if cur in seen: raise WeakScenarioValidationError('cyclic workaround dependency')
   seen.add(cur); cur=byid[cur].get('dependency')
 gaps=tuple(raw.get('residual_gaps',()))
 for g in gaps:
  try: g['classification']=GapClassification(g['classification']); EvidenceCategory(g['evidence']); g['modeled_burden']=money(g['modeled_burden'],'gap burden')
  except (KeyError,ValueError) as e: raise WeakScenarioValidationError('invalid residual-gap classification or evidence') from e
  if not set(g.get('question_ids',()))<=validq: raise WeakScenarioValidationError('residual question does not resolve')
 costs=raw['costs']; setup=sum((money(v,'setup cost') for v in costs['setup_configuration'].values()),Decimal())
 s=WeakScenario(raw,caps,questions,layers,gaps,setup,money(costs['annual_platform_cash'],'platform cost'),money(costs['annual_support_admin'],'support cost'),money(costs['residual_operational_burden'],'residual burden'),money(costs['administration_burden'],'administration burden'),money(costs['unknown_burden'],'unknown burden'),ScenarioResponse(raw['response']['value']))
 derived,rationale=derive_response(s)
 if not raw['response'].get('rationale') or derived is not s.response: raise WeakScenarioValidationError('scenario response without rationale or inconsistent with rules')
 # An answer cannot claim unavailable evidence: GAP capabilities used by these explicit traces remain partial/not answered.
 if next(q for q in questions if q['question_id']=='FIN-01')['weak_status'] is AnswerStatus.ANSWERED: raise WeakScenarioValidationError('question answered while required accounting evidence unavailable')
 return s
run_weak_native_coverage=load_weak_native_coverage
