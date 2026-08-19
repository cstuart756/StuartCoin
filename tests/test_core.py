import pytest
from app.blockchain import Blockchain
from app.wallet import Wallet
from app.merkle import calculate_merkle_root, create_merkle_proof, verify_merkle_proof, sha256_hex


def funded(difficulty=1):
    w=Wallet(); bc=Blockchain(difficulty=difficulty); bc.mine_pending_transactions(w.address); return bc,w

def test_mining_reward_and_balance():
    bc,w=funded(); assert bc.get_balance(w.address)==50

def test_utxo_payment_and_change():
    bc,a=funded(); b=Wallet(); tx=bc.create_transaction(a,b.address,12.5); assert [o.amount for o in tx.outputs]==[12.5,37.5]; bc.add_transaction(tx); bc.mine_pending_transactions(a.address); assert bc.get_balance(b.address)==12.5; assert bc.get_balance(a.address)==87.5

def test_overspend_rejected():
    bc,a=funded(); b=Wallet()
    with pytest.raises(ValueError): bc.create_transaction(a,b.address,60)

def test_pending_double_spend_prevented():
    bc,a=funded(); b,c=Wallet(),Wallet(); tx=bc.create_transaction(a,b.address,50); bc.add_transaction(tx)
    with pytest.raises(ValueError): bc.create_transaction(a,c.address,50)

def test_chain_valid_and_tamper_detected():
    bc,a=funded(); assert bc.is_chain_valid(); bc.chain[1].transactions[0]['outputs'][0]['amount']=999; assert not bc.is_chain_valid()

def test_merkle_proof():
    ids=[sha256_hex(f"tx-{i}") for i in range(5)]; root=calculate_merkle_root(ids); proof=create_merkle_proof(ids,3); assert verify_merkle_proof(ids[3],proof,root); assert not verify_merkle_proof(sha256_hex("fake"),proof,root)

def test_merkle_proof_rejects_unknown_position():
    ids=[sha256_hex("tx-1"), sha256_hex("tx-2")]
    proof=create_merkle_proof(ids, 0)
    proof[0]["position"]="middle"
    assert not verify_merkle_proof(ids[0], proof, calculate_merkle_root(ids))

def test_merkle_empty_tree_and_invalid_indexes():
    assert len(calculate_merkle_root([])) == 64
    with pytest.raises(ValueError, match="empty tree"):
        create_merkle_proof([], 0)
    with pytest.raises(ValueError, match="Invalid transaction index"):
        create_merkle_proof([sha256_hex("tx")], 1)
