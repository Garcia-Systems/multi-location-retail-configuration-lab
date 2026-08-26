"""Chapter 8's bounded, deterministic RiverFlow automation simulation."""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any

from .capabilities import load_inventory
from .ecommerce_reconciliation import run_ecommerce_reconciliation
from .evidence import EvidenceCategory
from .native_reporting import QuestionResult
from .returns_transfers import ReturnStatus, TransferStatus, load_returns_transfers_records

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "config" / "automation" / "automations.json"

class AutomationValidationError(ValueError): pass
class AutomationType(StrEnum):
    SCHEDULED_EXPORT="SCHEDULED_EXPORT"; MISSING_RECORD_ALERT="MISSING_RECORD_ALERT"; EXCEPTION_ALERT="EXCEPTION_ALERT"; RECONCILIATION_TRIGGER="RECONCILIATION_TRIGGER"; MAPPING_VALIDATION="MAPPING_VALIDATION"; REPORT_DISTRIBUTION="REPORT_DISTRIBUTION"
class TriggerType(StrEnum):
    SCHEDULE="SCHEDULE"; RECORD_AVAILABLE="RECORD_AVAILABLE"; AGE_THRESHOLD="AGE_THRESHOLD"; VALIDATION_FAILURE="VALIDATION_FAILURE"; RECONCILIATION_EXCEPTION="RECONCILIATION_EXCEPTION"
class ActionType(StrEnum):
    MOVE_EXPORT="MOVE_EXPORT"; CREATE_ALERT="CREATE_ALERT"; RUN_RECONCILIATION="RUN_RECONCILIATION"; VALIDATE_MAPPING="VALIDATE_MAPPING"; DISTRIBUTE_REPORT="DISTRIBUTE_REPORT"
class ExecutionStatus(StrEnum):
    SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; SKIPPED="SKIPPED"; RETRY_EXHAUSTED="RETRY_EXHAUSTED"; BLOCKED_BY_VALIDATION="BLOCKED_BY_VALIDATION"; DUPLICATE_SUPPRESSED="DUPLICATE_SUPPRESSED"

@dataclass(frozen=True)
class AutomationDefinition:
    automation_id:str; name:str; automation_type:AutomationType; trigger:dict[str,Any]; input_source:str; rule:str; action:dict[str,Any]; destination:str; max_attempts:int; failure_behavior:str; owner:str; enabled:bool; evidence_classification:EvidenceCategory; idempotent:bool; mapping_dependency:str; change_sensitivity:str
@dataclass(frozen=True)
class AutomationConfiguration:
    platform:str; automations:tuple[AutomationDefinition,...]; manual_steps_before:int; manual_steps_after:int
@dataclass(frozen=True)
class ExecutionRecord:
    execution_id:str; automation_id:str; trigger_reference:str; status:ExecutionStatus; attempt_count:int; action_summary:str; error_reason:str|None; evidence_classification:EvidenceCategory=EvidenceCategory.OBSERVED_LAB_RESULT
@dataclass(frozen=True)
class AutomationExperiment:
    configuration:AutomationConfiguration; executions:tuple[ExecutionRecord,...]; alerts:tuple[dict,...]; validation_exceptions:tuple[dict,...]; reconciliation_runs:int; distributions:tuple[dict,...]; question_impacts:tuple[tuple[str,QuestionResult,str],...]
    @property
    def counts(self): return Counter(x.status for x in self.executions)
    @property
    def manual_step_reduction_ratio(self):
        before=self.configuration.manual_steps_before
        return (before-self.configuration.manual_steps_after)/before if before else 0.0
    @property
    def automation_success_rate(self):
        """SUCCEEDED divided by terminal action outcomes (success, failed, exhausted)."""
        denominator=sum(self.counts[x] for x in (ExecutionStatus.SUCCEEDED,ExecutionStatus.FAILED,ExecutionStatus.RETRY_EXHAUSTED))
        return self.counts[ExecutionStatus.SUCCEEDED]/denominator if denominator else 0.0

def configuration_from_dict(raw:dict[str,Any])->AutomationConfiguration:
    systems={x.identifier for x in load_inventory().systems}; ids=set(); definitions=[]
    if raw.get("platform")!="RiverFlow": raise AutomationValidationError("automation platform must be RiverFlow")
    for row in raw.get("automations",[]):
        aid=row.get("automation_id")
        if not aid or aid in ids: raise AutomationValidationError("duplicate or missing automation ID")
        ids.add(aid)
        try: kind=AutomationType(row.get("automation_type")); evidence=EvidenceCategory(row.get("evidence_classification"))
        except (ValueError,TypeError) as exc: raise AutomationValidationError("unknown automation type or evidence classification") from exc
        trigger=row.get("trigger"); action=row.get("action")
        if row.get("enabled") and (not trigger or not action): raise AutomationValidationError("enabled automation missing trigger or action")
        try: TriggerType(trigger.get("type")); ActionType(action.get("type"))
        except (ValueError,TypeError,AttributeError) as exc: raise AutomationValidationError("unknown trigger or action type") from exc
        if trigger.get("type")=="SCHEDULE" and not re.fullmatch(r"(?:\S+\s+){4}\S+",str(trigger.get("schedule",""))): raise AutomationValidationError("malformed schedule representation")
        if row.get("input_source") not in systems: raise AutomationValidationError("nonexistent source system")
        if not isinstance(row.get("max_attempts"),int) or row["max_attempts"]<0: raise AutomationValidationError("negative retry count")
        if not row.get("owner"): raise AutomationValidationError("missing owner")
        if row.get("idempotent") is None: raise AutomationValidationError("missing idempotency configuration")
        required=("name","rule","destination","failure_behavior","mapping_dependency","change_sensitivity")
        if any(not row.get(x) for x in required): raise AutomationValidationError("incomplete automation support contract")
        definitions.append(AutomationDefinition(aid,row["name"],kind,trigger,row["input_source"],row["rule"],action,row["destination"],row["max_attempts"],row["failure_behavior"],row["owner"],row["enabled"],evidence,row["idempotent"],row["mapping_dependency"],row["change_sensitivity"]))
    if not definitions: raise AutomationValidationError("no automations configured")
    before,after=raw.get("manual_steps_before"),raw.get("manual_steps_after")
    if not all(isinstance(x,int) and x>=0 for x in (before,after)) or after>before: raise AutomationValidationError("invalid manual-step fixture")
    return AutomationConfiguration(raw["platform"],tuple(definitions),before,after)

def load_automation_configuration(path:Path|str=DEFAULT_CONFIG_PATH):
        with Path(path).open(encoding="utf-8") as stream: return configuration_from_dict(json.load(stream))

def missing_transfer_receipt(record) -> bool:
    """The narrow alert condition; received transfers never produce a false alert."""
    return record.status is TransferStatus.SENT and record.sent_status and not record.received_status

def missing_return_reason(record) -> bool:
    """The narrow notification condition; a valid reason makes it false."""
    return record.status is ReturnStatus.COMPLETED and record.reason is None

def validate_mapping(source_id:str, canonical_ids:tuple[str,...]) -> dict[str,str]|None:
    """Return an exception without guessing; exactly one canonical ID is valid."""
    if len(canonical_ids)==1: return None
    return {"source_id":source_id,"canonical_id":"UNRESOLVED","reason":"unmapped identity" if not canonical_ids else "ambiguous mapping"}

def run_automation_experiment(configuration:AutomationConfiguration|None=None)->AutomationExperiment:
    config=configuration or load_automation_configuration(); by={x.automation_id:x for x in config.automations}; executions=[]; alerts=[]; validations=[]; distributions=[]; sequence=0; processed=set()
    def record(aid,ref,status,attempts,summary,error=None):
        nonlocal sequence
        sequence+=1; executions.append(ExecutionRecord(f"AUTO-EXEC-{sequence:03d}",aid,ref,status,attempts,summary,error))
    def act(aid,ref,failures=0,summary="action completed"):
        automation=by[aid]; key=f"{aid}:{ref}:v1"
        if automation.idempotent and key in processed: record(aid,ref,ExecutionStatus.DUPLICATE_SUPPRESSED,0,"duplicate side effect suppressed"); return
        attempts=min(failures+1,max(1,automation.max_attempts))
        if failures>=max(1,automation.max_attempts): record(aid,ref,ExecutionStatus.RETRY_EXHAUSTED,attempts,summary,"configured synthetic action failure"); return
        processed.add(key); record(aid,ref,ExecutionStatus.SUCCEEDED,attempts,summary)
    act("scheduled-export-movement","RB-EXPORT-2026-07",1,"export moved to reconciliation input")
    returns,transfers,_=load_returns_transfers_records()
    missing=next(x for x in transfers if x.transfer_id=="JRO-TR-1007")
    if missing_transfer_receipt(missing):
        alerts.append({"record_id":missing.transfer_id,"owner":by["missing-transfer-receipt-alert"].owner,"sending_store":missing.sending_store,"receiving_store":missing.receiving_store,"quantity":missing.quantity_sent})
        act("missing-transfer-receipt-alert",missing.transfer_id,summary="missing transfer receipt alert created")
        act("missing-transfer-receipt-alert",missing.transfer_id,summary="missing transfer receipt alert created")
    bad_return=next(x for x in returns if missing_return_reason(x))
    alerts.append({"record_id":bad_return.return_id,"owner":"Store Manager","store":bad_return.return_store})
    act("missing-return-reason-notification",bad_return.return_id,summary="missing return reason notification created")
    validations.append({"source_id":"SKU-UNKNOWN","canonical_id":"UNRESOLVED","reason":"unmapped SKU"})
    record("mapping-validation","SKU-UNKNOWN",ExecutionStatus.SUCCEEDED,1,"validation exception list produced")
    record("mapping-validation","SHIRT-M",ExecutionStatus.BLOCKED_BY_VALIDATION,1,"unsafe downstream action blocked","ambiguous canonical identity")
    run_ecommerce_reconciliation(); act("ecommerce-reconciliation-trigger","ECOM-EXPORT-2026-07",summary="existing Chapter 5 reconciliation invoked")
    distributions.append({"report":"Store Sales Summary","recipient_role":"Central Operations Manager"})
    act("native-report-distribution","REPORT-2026-W31",2,"report distribution recorded")
    # A second modeled delivery demonstrates visible retry exhaustion without a duplicate side effect.
    act("native-report-distribution","REPORT-2026-W32",3,"report distribution failed")
    impacts=(("TRN-01",QuestionResult.ANSWERED,"Existing receipt evidence is surfaced sooner; the missing receipt remains."),("RET-02",QuestionResult.ANSWERED,"Missing reason evidence is notified; the data-quality problem remains."),("INV-03",QuestionResult.PARTIALLY_ANSWERED,"Validation routes unresolved identity without guessing."),("PUR-01",QuestionResult.PARTIALLY_ANSWERED,"No new purchasing evidence is created."),("MGT-01",QuestionResult.PARTIALLY_ANSWERED,"Narrow alerts improve visibility but do not create a cross-area briefing."))
    return AutomationExperiment(config,tuple(executions),tuple(alerts),tuple(validations),1,tuple(distributions),impacts)
