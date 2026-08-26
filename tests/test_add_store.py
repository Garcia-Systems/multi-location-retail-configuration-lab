import json
from pathlib import Path
import subprocess, sys
import pytest
from retail_configuration_lab.add_store import (DATA_PATH, STORE7_ID, OnboardingValidationError,
    TaskClassification, load_store7_experiment)


def test_standardized_store_identity_mapping_groups_and_catalog_reuse():
    x=load_store7_experiment()
    assert len(x.before_store_ids)==6 and len(x.after_store_ids)==7
    assert x.before_store_ids == tuple(f'JRO-STORE-{i:03}' for i in range(1,7))
    assert x.after_store_ids[-1]==STORE7_ID
    assert x.source_mappings == {'RiverPOS':'STORE-RW','RiverStock':'STORE_7','RiverBooks':'LOC-RICHMOND-WEST','RiverCommerce':'fulfillment_richmond_west'}
    assert STORE7_ID in x.store_groups['ALL_STORES']
    assert x.assortment == ('JRO-1042-BLU-M',) and x.excluded_skus == ('JRO-1055-GRN-L',)


def test_transactions_cover_reused_ecosystem_and_preserve_exception():
    x=load_store7_experiment(); tx=x.transactions
    assert {'SALE','ONLINE_FULFILLMENT','RECEIPT','RETURN','TRANSFER'} <= {t['kind'] for t in tx}
    online=next(t for t in tx if t['kind']=='ONLINE_FULFILLMENT')
    assert online['channel']=='ONLINE' and online['store']==STORE7_ID
    assert any(t.get('result')=='RECONCILED' and t['kind']=='RECEIPT' for t in tx)
    assert any(t.get('result')=='CROSS_STORE_RECONCILED' for t in tx)
    assert any(t.get('from_store')==STORE7_ID for t in tx if t['kind']=='TRANSFER')
    assert any(t.get('to_store')==STORE7_ID for t in tx if t['kind']=='TRANSFER')
    assert any(t.get('result')=='PARTIAL_RECEIPT' for t in tx)


def test_metrics_and_definition_growth_are_deterministic():
    x=load_store7_experiment()
    assert x.total_onboarding_tasks==20
    assert x.count(TaskClassification.REUSED_UNCHANGED)==11
    assert x.count(TaskClassification.REUSED_WITH_STORE_CONFIGURATION)==3
    assert x.count(TaskClassification.NEW_MAPPING)==1
    assert x.count(TaskClassification.NEW_CONFIGURATION)==5
    assert x.count(TaskClassification.NEW_CAPABILITY_REQUIRED)==0
    assert x.structural_reuse_ratio==pytest.approx(.7)
    assert x.new_capability_ratio==0
    assert x.growth['report_definitions']==(5,5)
    assert x.growth['automation_definitions']==(6,6)
    assert x.growth['bi_report_definitions']==(7,7)


def test_invalid_duplicate_mapping_and_duplicate_onboarding_are_rejected(tmp_path):
    raw=json.loads(DATA_PATH.read_text())
    raw['store']['source_mappings']['RiverPOS']='WBG-01'
    p=tmp_path/'bad.json'; p.write_text(json.dumps(raw))
    with pytest.raises(OnboardingValidationError, match='duplicate source'): load_store7_experiment(p)
    raw=json.loads(DATA_PATH.read_text()); raw['store_groups']['ALL_STORES'].append(STORE7_ID)
    p.write_text(json.dumps(raw))
    with pytest.raises(OnboardingValidationError): load_store7_experiment(p)


def test_invalid_transaction_and_same_store_transfer_are_rejected(tmp_path):
    raw=json.loads(DATA_PATH.read_text()); raw['transactions'][0]['sku']='MISSING'
    p=tmp_path/'bad.json'; p.write_text(json.dumps(raw))
    with pytest.raises(OnboardingValidationError, match='nonexistent SKU'): load_store7_experiment(p)
    raw=json.loads(DATA_PATH.read_text()); raw['transactions'][-1]['to_store']=STORE7_ID
    p.write_text(json.dumps(raw))
    with pytest.raises(OnboardingValidationError, match='same sending'): load_store7_experiment(p)


def test_cli_add_store():
    done=subprocess.run([sys.executable,'-m','retail_configuration_lab','add-store'],capture_output=True,text=True)
    assert done.returncode==0
    for text in ('Stores: 6','Stores: 7','Structural reuse ratio: 70.00%',
                 'New capability ratio: 0.00%','REUSED UNCHANGED','NEW MAPPING',
                 'Current lab verdict: UNTESTED'):
        assert text in done.stdout
