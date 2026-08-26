"""Chapter 12: recurring configuration support surface and modeled economics."""
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .evidence import EvidenceCategory
from .residual_gaps import analyze_residual_gaps

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUPPORT_SURFACE_PATH = ROOT / "data" / "support_surface.json"

class SupportSurfaceError(ValueError): pass
class FrequencyModel(StrEnum):
    PER_INCIDENT="PER_INCIDENT"; WEEKLY="WEEKLY"; MONTHLY="MONTHLY"; QUARTERLY="QUARTERLY"; ANNUAL="ANNUAL"; ON_CHANGE="ON_CHANGE"
class SupportRisk(StrEnum): LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"; UNKNOWN="UNKNOWN"
class SupportCategory(StrEnum):
    MAPPING_MAINTENANCE="MAPPING_MAINTENANCE"; NATIVE_INTEGRATION_MONITORING="NATIVE_INTEGRATION_MONITORING"; AUTOMATION_FAILURE_HANDLING="AUTOMATION_FAILURE_HANDLING"; BI_REPORT_MAINTENANCE="BI_REPORT_MAINTENANCE"; ROLE_ACCESS_ADMINISTRATION="ROLE_ACCESS_ADMINISTRATION"; SUBSCRIPTION_PLATFORM_ADMINISTRATION="SUBSCRIPTION_PLATFORM_ADMINISTRATION"; VENDOR_SCHEMA_CONFIGURATION_CHANGES="VENDOR_SCHEMA_CONFIGURATION_CHANGES"; STORE_ONBOARDING_SUPPORT_PREPARATION="STORE_ONBOARDING_SUPPORT_PREPARATION"; USER_SUPPORT_OPERATIONAL_QUESTIONS="USER_SUPPORT_OPERATIONAL_QUESTIONS"; EXCEPTION_RULE_MAINTENANCE="EXCEPTION_RULE_MAINTENANCE"

def _decimal(value: Any, field: str) -> Decimal:
    try: result=Decimal(str(value))
    except Exception as exc: raise SupportSurfaceError(f"invalid {field}") from exc
    if result < 0: raise SupportSurfaceError(f"{field} cannot be negative")
    return result

@dataclass(frozen=True)
class SupportObligation:
    obligation_id:str; category:SupportCategory; name:str; description:str; triggering_condition:str; responsible_role:str; frequency_model:FrequencyModel; modeled_incidents_per_year:Decimal; modeled_hours_per_incident:Decimal; modeled_hourly_cost:Decimal; annual_modeled_effort:Decimal; annual_modeled_cost:Decimal; source_dependency:str; evidence_classification:EvidenceCategory; uncertainty_note:str; existed_before_configuration:bool; risk:SupportRisk; risk_rationale:str; external_platform_dependency:bool
    @property
    def annual_effort_hours(self): return self.modeled_incidents_per_year*self.modeled_hours_per_incident
    @property
    def annual_support_cost(self): return self.annual_effort_hours*self.modeled_hourly_cost

@dataclass(frozen=True)
class PlatformCost:
    cost_id:str; name:str; annual_cost:Decimal; evidence_classification:EvidenceCategory
@dataclass(frozen=True)
class SupportInventory:
    customer_name:str; obligations:tuple[SupportObligation,...]; platform_costs:tuple[PlatformCost,...]; replaces_chapter11_admin_estimate:bool
@dataclass(frozen=True)
class SupportAnalysis:
    annual_support_labor_hours:Decimal; annual_support_labor_cost:Decimal; annual_platform_cash_cost:Decimal; annual_total_configuration_support_cost:Decimal; residual_operational_burden:Decimal; chapter11_new_administration_burden:Decimal; chapter11_modeled_burden_reduction:Decimal; support_cost_as_share_of_modeled_burden_reduction:Decimal|None; net_modeled_burden_reduction_after_support:Decimal; active_mappings:int; configured_reports:int; automations:int; native_integration_configurations:int; external_platform_obligations:int

def support_inventory_from_dict(data:dict[str,Any], root:Path=ROOT)->SupportInventory:
    if not isinstance(data,dict) or not isinstance(data.get("obligations"),list): raise SupportSurfaceError("support inventory must be structured")
    obligations=[]; seen=set()
    for raw in data["obligations"]:
        oid=str(raw.get("obligation_id","")).strip()
        if not oid or oid in seen: raise SupportSurfaceError(f"duplicate or missing support obligation ID: {oid}")
        seen.add(oid)
        try:
            category=SupportCategory(raw["category"]); frequency=FrequencyModel(raw["frequency_model"]); risk=SupportRisk(raw["risk"]); evidence=EvidenceCategory(raw["evidence_classification"])
        except (KeyError,ValueError) as exc: raise SupportSurfaceError(f"{oid}: invalid classification") from exc
        owner=str(raw.get("responsible_role","")).strip(); trigger=str(raw.get("triggering_condition","")).strip(); dependency=str(raw.get("source_dependency","")).strip()
        if not owner: raise SupportSurfaceError(f"{oid}: missing owner")
        if not trigger: raise SupportSurfaceError(f"{oid}: missing triggering condition")
        if not dependency or dependency.startswith("/") or not (root/dependency).is_file(): raise SupportSurfaceError(f"{oid}: source dependency does not resolve: {dependency}")
        incidents=_decimal(raw.get("modeled_incidents_per_year"),"incidents/year"); hours=_decimal(raw.get("modeled_hours_per_incident"),"effort"); rate=_decimal(raw.get("modeled_hourly_cost"),"hourly cost")
        annual_hours=_decimal(raw.get("annual_modeled_effort"),"annual effort"); annual_cost=_decimal(raw.get("annual_modeled_cost"),"annual cost")
        if annual_hours != incidents*hours: raise SupportSurfaceError(f"{oid}: annual effort calculation mismatch")
        if annual_cost != annual_hours*rate: raise SupportSurfaceError(f"{oid}: annual cost calculation mismatch")
        obligations.append(SupportObligation(oid,category,str(raw.get("name","")),str(raw.get("description","")),trigger,owner,frequency,incidents,hours,rate,annual_hours,annual_cost,dependency,evidence,str(raw.get("uncertainty_note","")),bool(raw.get("existed_before_configuration")),risk,str(raw.get("risk_rationale","")),bool(raw.get("external_platform_dependency"))))
    if {x.category for x in obligations} != set(SupportCategory): raise SupportSurfaceError("all support categories must occur exactly in the bounded inventory")
    costs=[]; cost_ids=set()
    for raw in data.get("platform_costs",[]):
        cid=str(raw.get("cost_id","")).strip()
        if not cid or cid in cost_ids: raise SupportSurfaceError(f"duplicate or missing platform cost ID: {cid}")
        cost_ids.add(cid)
        try: evidence=EvidenceCategory(raw["evidence_classification"])
        except (KeyError,ValueError) as exc: raise SupportSurfaceError(f"{cid}: invalid evidence classification") from exc
        costs.append(PlatformCost(cid,str(raw.get("name","")),_decimal(raw.get("annual_cost"),"platform cost"),evidence))
    replaces=data.get("replaces_chapter11_admin_estimate") is True
    if not replaces: raise SupportSurfaceError("Chapter 11 administration estimate would be double-counted")
    return SupportInventory(str(data.get("customer_name","")),tuple(obligations),tuple(costs),replaces)

def load_support_inventory(path: str|Path=DEFAULT_SUPPORT_SURFACE_PATH)->SupportInventory:
    try:
        with Path(path).open(encoding="utf-8") as f: return support_inventory_from_dict(json.load(f))
    except (OSError,json.JSONDecodeError) as exc: raise SupportSurfaceError(f"Could not load support inventory {path}: {exc}") from exc

def _count_list(path:Path,key:str)->int: return len(json.loads(path.read_text())[key])
def analyze_support_surface(inventory:SupportInventory|None=None)->SupportAnalysis:
    inv=inventory or load_support_inventory(); chapter11=analyze_residual_gaps()
    hours=sum((x.annual_effort_hours for x in inv.obligations),Decimal()); labor=sum((x.annual_support_cost for x in inv.obligations),Decimal()); cash=sum((x.annual_cost for x in inv.platform_costs),Decimal()); total=labor+cash
    reduction=chapter11.modeled_burden_reduction
    share=total/reduction if reduction else None
    mappings=sum(_count_list(ROOT/p,"mappings") for p in ("config/identity/channels.json","config/identity/products.json","config/identity/skus.json","config/identity/stores.json","config/identity/suppliers.json","config/identity/variants.json"))
    reports=_count_list(ROOT/"config/bi/reports.json","reports")+_count_list(ROOT/"config/reporting/native_reports.json","reports")
    return SupportAnalysis(hours,labor,cash,total,chapter11.residual_operational_burden,chapter11.new_administration_burden,reduction,share,reduction-total,mappings,reports,_count_list(ROOT/"config/automation/automations.json","automations"),1,sum(x.external_platform_dependency for x in inv.obligations))

analyze_support_inventory = analyze_support_surface
