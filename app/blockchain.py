import hashlib, json, time
from datetime import datetime, timezone
from .transaction import Transaction, TransactionInput, TransactionOutput
from .wallet import Wallet
from .merkle import calculate_merkle_root

class Block:
    def __init__(self,index,transactions,previous_hash,difficulty):
        self.index=index; self.timestamp=datetime.now(timezone.utc).isoformat(); self.transactions=transactions; self.previous_hash=previous_hash; self.difficulty=difficulty; self.nonce=0
        self.merkle_root=self.calculate_merkle_root(); self.hash=self.calculate_hash()
    def get_transaction_ids(self): return [t['transaction_id'] for t in self.transactions]
    def calculate_merkle_root(self): return calculate_merkle_root(self.get_transaction_ids())
    def block_header(self): return {"index":self.index,"timestamp":self.timestamp,"previous_hash":self.previous_hash,"merkle_root":self.merkle_root,"difficulty":self.difficulty,"nonce":self.nonce}
    def calculate_hash(self): return hashlib.sha256(json.dumps(self.block_header(),sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def mine_block(self):
        target='0'*self.difficulty; attempts=0; started=time.time()
        while not self.hash.startswith(target): self.nonce+=1; attempts+=1; self.hash=self.calculate_hash()
        return {"attempts":attempts,"seconds":time.time()-started,"hash":self.hash}
    def to_dict(self): return {"index":self.index,"timestamp":self.timestamp,"transactions":self.transactions,"previous_hash":self.previous_hash,"difficulty":self.difficulty,"nonce":self.nonce,"merkle_root":self.merkle_root,"hash":self.hash}
    @classmethod
    def from_dict(cls,d):
        b=cls(d['index'],d['transactions'],d['previous_hash'],d['difficulty']); b.timestamp=d['timestamp']; b.nonce=d['nonce']; b.merkle_root=d['merkle_root']; b.hash=d['hash']; return b

class Blockchain:
    def __init__(self,difficulty=3,mining_reward=50):
        self.difficulty=difficulty; self.mining_reward=float(mining_reward); self.chain=[self.create_genesis_block()]; self.pending_transactions=[]; self.utxos={}
    def create_genesis_block(self): return Block(0,[],"0",self.difficulty)
    def latest(self): return self.chain[-1]
    @staticmethod
    def utxo_key(txid,idx): return f"{txid}:{idx}"
    def _add_outputs(self,t):
        for idx,o in enumerate(t.outputs): self.utxos[self.utxo_key(t.transaction_id,idx)]={"transaction_id":t.transaction_id,"output_index":idx,"recipient":o.recipient,"amount":o.amount}
    def _remove_inputs(self,t):
        for i in t.inputs: self.utxos.pop(self.utxo_key(i.transaction_id,i.output_index),None)
    def get_utxos_for_address(self,address): return [u for u in self.utxos.values() if u['recipient']==address]
    def get_balance(self,address): return sum(u['amount'] for u in self.get_utxos_for_address(address))
    def pending_spent_keys(self): return {self.utxo_key(i.transaction_id,i.output_index) for t in self.pending_transactions for i in t.inputs}
    def create_transaction(self,wallet,recipient,amount):
        amount=float(amount)
        if amount<=0: raise ValueError("Amount must be greater than zero")
        reserved=self.pending_spent_keys(); available=[u for u in self.get_utxos_for_address(wallet.address) if self.utxo_key(u['transaction_id'],u['output_index']) not in reserved]
        selected=[]; total=0
        for u in available:
            selected.append(u); total+=u['amount']
            if total>=amount: break
        if total<amount: raise ValueError("Insufficient funds")
        inputs=[TransactionInput(u['transaction_id'],u['output_index']) for u in selected]
        outputs=[TransactionOutput(recipient,amount)]
        if total>amount: outputs.append(TransactionOutput(wallet.address,total-amount))
        t=Transaction(inputs,outputs); t.sign(wallet); return t
    def validate_transaction(self,t,utxo_set=None):
        utxo_set=self.utxos if utxo_set is None else utxo_set
        if t.transaction_id!=t.calculate_transaction_id(): return False
        if t.coinbase: return (not t.inputs and len(t.outputs)==1 and t.outputs[0].amount==self.mining_reward)
        if not t.inputs or not t.outputs: return False
        seen=set(); input_total=0
        for i in t.inputs:
            key=self.utxo_key(i.transaction_id,i.output_index)
            if key in seen or key not in utxo_set: return False
            seen.add(key); ref=utxo_set[key]
            if not i.public_key or Wallet.address_from_public_key(i.public_key)!=ref['recipient'] or not t.verify_input_signature(i): return False
            input_total+=ref['amount']
        output_total=sum(o.amount for o in t.outputs)
        return all(o.amount>0 for o in t.outputs) and abs(input_total-output_total)<1e-9
    def add_transaction(self,t):
        if t.coinbase: raise ValueError("Users cannot submit coinbase transactions")
        reserved=self.pending_spent_keys()
        if any(self.utxo_key(i.transaction_id,i.output_index) in reserved for i in t.inputs): raise ValueError("Double spend detected")
        if not self.validate_transaction(t): raise ValueError("Transaction validation failed")
        self.pending_transactions.append(t)
    def mine_pending_transactions(self,miner_address):
        height=len(self.chain); coinbase=Transaction.create_coinbase(miner_address,self.mining_reward,height); txs=self.pending_transactions+[coinbase]
        b=Block(height,[t.to_dict() for t in txs],self.latest().hash,self.difficulty); stats=b.mine_block(); self.chain.append(b)
        for t in self.pending_transactions: self._remove_inputs(t); self._add_outputs(t)
        self._add_outputs(coinbase); self.pending_transactions=[]; return b,stats
    def is_chain_valid(self, chain=None):
        chain=self.chain if chain is None else chain; temp={}; target='0'*self.difficulty
        if not chain or chain[0].index != 0 or chain[0].previous_hash != "0": return False
        genesis = chain[0]
        if genesis.merkle_root != genesis.calculate_merkle_root() or genesis.hash != genesis.calculate_hash(): return False
        for bi in range(1,len(chain)):
            b=chain[bi]; prev=chain[bi-1]
            if b.merkle_root!=b.calculate_merkle_root() or b.hash!=b.calculate_hash() or b.previous_hash!=prev.hash or not b.hash.startswith(target): return False
            coinbases=0
            for td in b.transactions:
                t=Transaction.from_dict(td)
                if t.coinbase: coinbases+=1
                if not self.validate_transaction(t,temp): return False
                if not t.coinbase:
                    for i in t.inputs: temp.pop(self.utxo_key(i.transaction_id,i.output_index),None)
                for idx,o in enumerate(t.outputs): temp[self.utxo_key(t.transaction_id,idx)]={"transaction_id":t.transaction_id,"output_index":idx,"recipient":o.recipient,"amount":o.amount}
            if coinbases!=1: return False
        return True
    def chain_work(self, chain=None): return len(self.chain if chain is None else chain)
    def replace_chain(self, blocks):
        candidate=[Block.from_dict(x) if isinstance(x,dict) else x for x in blocks]
        if len(candidate)<=len(self.chain): return False
        if not self.is_chain_valid(candidate): return False
        self.chain=candidate; self.rebuild_utxos(); return True
    def rebuild_utxos(self):
        self.utxos={}
        for b in self.chain[1:]:
            for td in b.transactions:
                t=Transaction.from_dict(td)
                if not t.coinbase: self._remove_inputs(t)
                self._add_outputs(t)
    def to_dict(self): return {"difficulty":self.difficulty,"mining_reward":self.mining_reward,"height":len(self.chain)-1,"pending":len(self.pending_transactions),"chain":[b.to_dict() for b in self.chain]}
