import asyncio, os
import httpx
from .blockchain import Blockchain
from .transaction import Transaction
from .store import JsonStore

class Node:
    def __init__(self):
        self.store=JsonStore(os.getenv("STC_DATA","data/node.json")); loaded,peers=self.store.load(); self.blockchain=loaded or Blockchain(int(os.getenv("STC_DIFFICULTY","3")),float(os.getenv("STC_REWARD","50"))); self.peers=peers
    def persist(self): self.store.save(self.blockchain,self.peers)
    def register_peer(self,url): self.peers.add(url.rstrip('/')); self.persist()
    async def broadcast(self,path,payload):
        async with httpx.AsyncClient(timeout=3) as c:
            await asyncio.gather(*(c.post(p+path,json=payload) for p in self.peers),return_exceptions=True)
    async def sync(self):
        best=None
        async with httpx.AsyncClient(timeout=3) as c:
            for p in list(self.peers):
                try:
                    r=await c.get(p+"/chain"); r.raise_for_status(); data=r.json()
                    if not best or data["height"]>best["height"]: best=data
                except Exception: pass
        if best and self.blockchain.replace_chain(best["chain"]): self.persist(); return True
        return False
