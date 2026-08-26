"""Chapter 6 configuration-driven purchasing/receiving experiment."""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .identity import IdentityType, load_identity_configuration
from .native_reporting import QuestionResult

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "purchasing"
DATA = ROOT / "data" / "purchasing" / "purchase_orders.json"


class PurchasingValidationError(ValueError): pass
class POStatus(StrEnum):
    DRAFT="DRAFT"; OPEN="OPEN"; PARTIALLY_RECEIVED="PARTIALLY_RECEIVED"; RECEIVED="RECEIVED"; CANCELLED="CANCELLED"; CLOSED="CLOSED"
class ReceivingStatus(StrEnum):
    NOT_RECEIVED="NOT_RECEIVED"; PARTIALLY_RECEIVED="PARTIALLY_RECEIVED"; FULLY_RECEIVED="FULLY_RECEIVED"; OVER_RECEIVED="OVER_RECEIVED"; REJECTED="REJECTED"; UNKNOWN="UNKNOWN"
class PurchasingResult(StrEnum):
    RECONCILED="RECONCILED"; PARTIAL_RECEIPT="PARTIAL_RECEIPT"; OVER_RECEIPT="OVER_RECEIPT"; LOCATION_EXCEPTION="LOCATION_EXCEPTION"; CANCELLED_PO_RECEIPT="CANCELLED_PO_RECEIPT"; UNRESOLVED_IDENTITY="UNRESOLVED_IDENTITY"; MISSING_RECEIPT="MISSING_RECEIPT"; INVENTORY_EFFECT_EXCEPTION="INVENTORY_EFFECT_EXCEPTION"; EXTERNAL_EVIDENCE_REQUIRED="EXTERNAL_EVIDENCE_REQUIRED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class SupplierItemMapping:
    supplier_id: str; supplier_item_id: str; aliases: tuple[str,...]; canonical_skus: tuple[str,...]; status: str; provenance: str
@dataclass(frozen=True)
class PurchasingConfiguration:
    supplier_items: tuple[SupplierItemMapping,...]; po_rules: dict[str,Any]; receiving_rules: dict[str,Any]; replenishment: dict[str,Any]
    def resolve_item(self, value: str) -> str | None:
        matches=[m for m in self.supplier_items if value == m.supplier_item_id or value in m.aliases]
        return matches[0].canonical_skus[0] if len(matches)==1 and matches[0].status=="RESOLVED" and len(matches[0].canonical_skus)==1 else None
@dataclass(frozen=True)
class POLine: line_id:str; supplier_item_id:str; ordered_quantity:int; line_status:str
@dataclass(frozen=True)
class PurchaseOrder:
    canonical_po_id:str; source_po_id:str; supplier_id:str; supplier_source_id:str; destination_store_id:str; status:POStatus; provenance:str; accounting_reference:str|None; accounting_evidence:bool; lines:tuple[POLine,...]
@dataclass(frozen=True)
class Receipt:
    receipt_id:str; po_reference:str; line_id:str; supplier_item_id:str; received_quantity:int; location_source_id:str; status:ReceivingStatus; inventory_effect:int
@dataclass(frozen=True)
class LineOutcome:
    po:PurchaseOrder; line:POLine; receipt:Receipt|None; canonical_sku:str|None; actual_location:str|None; result:PurchasingResult; accounting_evidence_required:bool
@dataclass(frozen=True)
class QuestionImpact: question_id:str; status:QuestionResult; reason:str
@dataclass(frozen=True)
class PurchasingExperiment:
    outcomes:tuple[LineOutcome,...]; before:dict[str,int]; question_impacts:tuple[QuestionImpact,...]
    @property
    def counts(self): return Counter(x.result for x in self.outcomes)
    @property
    def total_purchase_orders(self): return len({x.po.canonical_po_id for x in self.outcomes})
    @property
    def total_po_lines(self): return len(self.outcomes)
    @property
    def supplier_items_resolved(self): return sum(x.canonical_sku is not None for x in self.outcomes)
    @property
    def supplier_items_unresolved(self): return self.total_po_lines-self.supplier_items_resolved
    @property
    def inventory_effect_exceptions(self): return self.counts[PurchasingResult.INVENTORY_EFFECT_EXCEPTION]
    @property
    def records_requiring_external_accounting_evidence(self): return sum(x.accounting_evidence_required for x in self.outcomes)
    @property
    def manual_links_after(self): return sum(x.receipt is None or x.canonical_sku is None for x in self.outcomes)
    @property
    def purchasing_manual_reconciliation_reduction_ratio(self):
        before=self.before["manual_po_receipt_links"]; return (before-self.manual_links_after)/before if before else 0.0
    @property
    def po_line_reconciliation_rate(self):
        evaluable=[x for x in self.outcomes if x.canonical_sku is not None]
        return self.counts[PurchasingResult.RECONCILED]/len(evaluable) if evaluable else 0.0

def _load(path):
    with Path(path).open(encoding="utf-8") as f: return json.load(f)

def load_purchasing_configuration(directory:Path=CONFIG)->PurchasingConfiguration:
    raw=_load(directory/"supplier_items.json"); po=_load(directory/"po_rules.json"); receiving=_load(directory/"receiving_rules.json"); repl=_load(directory/"replenishment.json")
    identity=load_identity_configuration(); skus={x.canonical_id for x in identity.identities[IdentityType.SKU]}; stores={x.canonical_id for x in identity.identities[IdentityType.STORE]}; suppliers={x.canonical_id for x in identity.identities[IdentityType.SUPPLIER]}
    mappings=[]; keys={}
    for row in raw.get("mappings",[]):
        if raw.get("identity_type")!="SUPPLIER_ITEM": raise PurchasingValidationError("supplier-item mapping has incompatible identity type")
        key=(row.get("supplier_id"),row.get("supplier_item_id")); signature=tuple(row.get("canonical_skus",[]))
        if key[0] not in suppliers: raise PurchasingValidationError("supplier-item mapping references nonexistent supplier")
        if key in keys and keys[key]!=signature: raise PurchasingValidationError("conflicting duplicate supplier-item mapping")
        keys[key]=signature
        if row.get("status")=="RESOLVED" and (len(signature)!=1 or signature[0] not in skus): raise PurchasingValidationError("resolved supplier item references nonexistent SKU")
        mappings.append(SupplierItemMapping(*key,tuple(row.get("aliases",[])),signature,row.get("status"),row.get("provenance","")))
    if set(po.get("allowed_statuses",[])) != {x.value for x in POStatus}: raise PurchasingValidationError("invalid PO status configuration")
    if set(receiving.get("allowed_statuses",[])) != {x.value for x in ReceivingStatus}: raise PurchasingValidationError("invalid receiving status configuration")
    if set(receiving.get("location_mappings",{}).values())-stores: raise PurchasingValidationError("invalid location ownership mapping")
    allowed=set(repl.get("allowed_categories",[]))
    if set(repl.get("sku_categories",{}))-skus or set(repl.get("sku_categories",{}).values())-allowed: raise PurchasingValidationError("invalid replenishment category")
    return PurchasingConfiguration(tuple(mappings),po,receiving,repl)

def load_purchasing_records(path:Path=DATA, configuration:PurchasingConfiguration|None=None):
    c=configuration or load_purchasing_configuration(); raw=_load(path); identity=load_identity_configuration()
    suppliers={x.canonical_id for x in identity.identities[IdentityType.SUPPLIER]}; stores={x.canonical_id for x in identity.identities[IdentityType.STORE]}
    supplier_sources={m.source_identifier:m.canonical_ids[0] for m in identity.mappings if m.identity_type is IdentityType.SUPPLIER and len(m.canonical_ids)==1}
    pos=[]; canonical=set(); source=set()
    for row in raw.get("purchase_orders",[]):
        if row.get("canonical_po_id") in canonical or row.get("source_po_id") in source: raise PurchasingValidationError("duplicate canonical or source PO ID")
        canonical.add(row.get("canonical_po_id")); source.add(row.get("source_po_id"))
        supplier=supplier_sources.get(row.get("supplier_source_id"))
        if supplier not in suppliers: raise PurchasingValidationError("PO references nonexistent supplier")
        if row.get("destination_store_id") not in stores: raise PurchasingValidationError("PO references nonexistent destination store")
        if not row.get("provenance"): raise PurchasingValidationError("missing PO provenance")
        try: status=POStatus(row.get("status"))
        except ValueError as e: raise PurchasingValidationError("invalid PO status") from e
        lines=[]
        for line in row.get("lines",[]):
            if not isinstance(line.get("ordered_quantity"),int) or line["ordered_quantity"]<0: raise PurchasingValidationError("negative or invalid ordered quantity")
            lines.append(POLine(line["line_id"],line["supplier_item_id"],line["ordered_quantity"],line["line_status"]))
        pos.append(PurchaseOrder(row["canonical_po_id"],row["source_po_id"],supplier,row["supplier_source_id"],row["destination_store_id"],status,row["provenance"],row.get("accounting_reference"),bool(row.get("accounting_evidence")),tuple(lines)))
    receipts=[]
    for row in raw.get("receipts",[]):
        if not isinstance(row.get("received_quantity"),int) or row["received_quantity"]<0: raise PurchasingValidationError("negative or invalid received quantity")
        suffix=row.get("po_reference","").removeprefix(c.po_rules["receipt_reference_prefix"]); canonical_id=c.po_rules["canonical_prefix"]+suffix
        if canonical_id not in canonical and not row.get("intentional_orphan_exception"): raise PurchasingValidationError("receipt references nonexistent PO")
        try: status=ReceivingStatus(row.get("status"))
        except ValueError as e: raise PurchasingValidationError("invalid receiving status") from e
        receipts.append(Receipt(row["receipt_id"],row["po_reference"],row["line_id"],row["supplier_item_id"],row["received_quantity"],row["location_source_id"],status,row["inventory_effect"]))
    return tuple(pos),tuple(receipts),raw["before"]

def run_purchasing_experiment(configuration=None,path:Path=DATA):
    c=configuration or load_purchasing_configuration(); pos,receipts,before=load_purchasing_records(path,c); receipt_by={(r.po_reference.removeprefix(c.po_rules["receipt_reference_prefix"]),r.line_id):r for r in receipts}; outcomes=[]
    for po in pos:
      suffix=po.source_po_id.removeprefix(c.po_rules["source_prefix"])
      for line in po.lines:
        receipt=receipt_by.get((suffix,line.line_id)); sku=c.resolve_item(line.supplier_item_id); actual=c.receiving_rules["location_mappings"].get(receipt.location_source_id) if receipt else None
        receipt_sku=c.resolve_item(receipt.supplier_item_id) if receipt else None
        if sku is None or (receipt is not None and receipt_sku != sku): result=PurchasingResult.UNRESOLVED_IDENTITY
        elif receipt is None: result=PurchasingResult.MISSING_RECEIPT
        elif po.status is POStatus.CANCELLED and receipt.received_quantity: result=PurchasingResult.CANCELLED_PO_RECEIPT
        elif actual != po.destination_store_id: result=PurchasingResult.LOCATION_EXCEPTION
        elif receipt.received_quantity < line.ordered_quantity: result=PurchasingResult.PARTIAL_RECEIPT
        elif receipt.received_quantity > line.ordered_quantity: result=PurchasingResult.OVER_RECEIPT
        elif receipt.inventory_effect != receipt.received_quantity: result=PurchasingResult.INVENTORY_EFFECT_EXCEPTION
        else: result=PurchasingResult.RECONCILED
        outcomes.append(LineOutcome(po,line,receipt,sku,actual,result,not po.accounting_evidence))
    impacts=(QuestionImpact("PUR-01",QuestionResult.ANSWERED,"Configured exception results identify records needing attention."),QuestionImpact("PUR-02",QuestionResult.ANSWERED,"Ordered, received, location, and inventory effects are classified."),QuestionImpact("INV-03",QuestionResult.PARTIALLY_ANSWERED,"Supplier-item mapping defects are separated from physical discrepancies."),QuestionImpact("FIN-01",QuestionResult.PARTIALLY_ANSWERED,"References are retained, but accounting evidence is external."))
    return PurchasingExperiment(tuple(outcomes),before,impacts)
