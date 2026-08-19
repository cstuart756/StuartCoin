import json, os
from .blockchain import Blockchain, Block

class JsonStore:
    def __init__(self,path="data/node.json"): self.path=path
    def save(self,bc,peers):
        os.makedirs(os.path.dirname(self.path) or ".",exist_ok=True)
        with open(self.path,"w",encoding="utf-8") as f: json.dump({"difficulty":bc.difficulty,"mining_reward":bc.mining_reward,"chain":[b.to_dict() for b in bc.chain],"peers":sorted(peers)},f,indent=2)
    def load(self):
        if not os.path.exists(self.path): return None,set()
        with open(self.path,encoding="utf-8") as f: d=json.load(f)
        bc=Blockchain(d["difficulty"],d["mining_reward"]); bc.chain=[Block.from_dict(x) for x in d["chain"]]; bc.rebuild_utxos(); return bc,set(d.get("peers",[]))
