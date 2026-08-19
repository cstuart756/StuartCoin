import hashlib, json
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from .wallet import Wallet

class TransactionInput:
    def __init__(self, transaction_id, output_index, public_key=None, signature=None):
        self.transaction_id, self.output_index, self.public_key, self.signature = transaction_id, output_index, public_key, signature
    def to_dict(self): return vars(self)
    @classmethod
    def from_dict(cls,d): return cls(d['transaction_id'], d['output_index'], d.get('public_key'), d.get('signature'))

class TransactionOutput:
    def __init__(self, recipient, amount): self.recipient, self.amount = recipient, float(amount)
    def to_dict(self): return vars(self)
    @classmethod
    def from_dict(cls,d): return cls(d['recipient'], d['amount'])

class Transaction:
    def __init__(self, inputs, outputs, coinbase=False, coinbase_tag=None):
        self.inputs, self.outputs, self.coinbase, self.coinbase_tag = inputs, outputs, coinbase, coinbase_tag
        self.transaction_id = self.calculate_transaction_id()
    def signing_data(self):
        data={"inputs":[{"transaction_id":i.transaction_id,"output_index":i.output_index,"public_key":i.public_key} for i in self.inputs],"outputs":[o.to_dict() for o in self.outputs],"coinbase":self.coinbase,"coinbase_tag":self.coinbase_tag}
        return json.dumps(data,sort_keys=True,separators=(",",":")).encode()
    def calculate_transaction_id(self):
        data={"inputs":[i.to_dict() for i in self.inputs],"outputs":[o.to_dict() for o in self.outputs],"coinbase":self.coinbase,"coinbase_tag":self.coinbase_tag}
        return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def sign(self,wallet):
        if self.coinbase: raise ValueError("Coinbase transactions are not signed")
        for i in self.inputs: i.public_key=wallet.public_key_hex
        msg=self.signing_data()
        for i in self.inputs: i.signature=wallet.private_key.sign(msg,ec.ECDSA(hashes.SHA256())).hex()
        self.transaction_id=self.calculate_transaction_id()
    def verify_input_signature(self,i):
        if not i.public_key or not i.signature: return False
        try:
            pk=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(),bytes.fromhex(i.public_key))
            pk.verify(bytes.fromhex(i.signature),self.signing_data(),ec.ECDSA(hashes.SHA256())); return True
        except (InvalidSignature, ValueError): return False
    def to_dict(self): return {"transaction_id":self.transaction_id,"inputs":[i.to_dict() for i in self.inputs],"outputs":[o.to_dict() for o in self.outputs],"coinbase":self.coinbase,"coinbase_tag":self.coinbase_tag}
    @classmethod
    def from_dict(cls,d):
        t=cls([TransactionInput.from_dict(x) for x in d['inputs']],[TransactionOutput.from_dict(x) for x in d['outputs']],d.get('coinbase',False),d.get('coinbase_tag')); t.transaction_id=d['transaction_id']; return t
    @classmethod
    def create_coinbase(cls,recipient,amount,block_height): return cls([], [TransactionOutput(recipient,amount)], True, f"block-{block_height}")
