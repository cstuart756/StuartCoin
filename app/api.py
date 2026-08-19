from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .node import Node
from .transaction import Transaction
from .merkle import create_merkle_proof, verify_merkle_proof

app=FastAPI(title="StuartCoin Node API",version="1.0.0")
node=Node()

class PeerIn(BaseModel): url:str
class MineIn(BaseModel): miner_address:str
class TxIn(BaseModel): transaction:dict

@app.get("/")
def root(): return {"name":"StuartCoin","version":"1.0.0","docs":"/docs"}
@app.get("/health")
def health(): return {"ok":True,"height":len(node.blockchain.chain)-1,"peers":len(node.peers)}
@app.get("/chain")
def chain(): return node.blockchain.to_dict()
@app.get("/blocks")
def blocks(): return [b.to_dict() for b in reversed(node.blockchain.chain)]
@app.get("/blocks/{index}")
def block(index:int):
    if index<0 or index>=len(node.blockchain.chain): raise HTTPException(404,"Block not found")
    return node.blockchain.chain[index].to_dict()
@app.get("/address/{address}")
def address(address:str): return {"address":address,"balance":node.blockchain.get_balance(address),"utxos":node.blockchain.get_utxos_for_address(address)}
@app.get("/mempool")
def mempool(): return [t.to_dict() for t in node.blockchain.pending_transactions]
@app.post("/transactions")
async def submit(body:TxIn):
    try: t=Transaction.from_dict(body.transaction); node.blockchain.add_transaction(t); node.persist(); await node.broadcast("/transactions",body.model_dump()); return {"accepted":True,"transaction_id":t.transaction_id}
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/mine")
async def mine(body:MineIn):
    try: b,stats=node.blockchain.mine_pending_transactions(body.miner_address); node.persist(); await node.broadcast("/blocks/receive",b.to_dict()); return {"block":b.to_dict(),"stats":stats}
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/blocks/receive")
def receive_block(block:dict):
    from .blockchain import Block
    b=Block.from_dict(block)
    if b.index==len(node.blockchain.chain) and b.previous_hash==node.blockchain.latest().hash:
        candidate=node.blockchain.chain+[b]
        if node.blockchain.is_chain_valid(candidate): node.blockchain.chain.append(b); node.blockchain.rebuild_utxos(); node.persist(); return {"accepted":True}
    return {"accepted":False,"sync_required":True}
@app.get("/peers")
def peers(): return {"peers":sorted(node.peers)}
@app.post("/peers")
def add_peer(body:PeerIn): node.register_peer(body.url); return {"peers":sorted(node.peers)}
@app.post("/sync")
async def sync(): return {"replaced":await node.sync(),"height":len(node.blockchain.chain)-1}
@app.get("/proof/{block_index}/{tx_index}")
def proof(block_index:int,tx_index:int):
    try:
        b=node.blockchain.chain[block_index]; ids=b.get_transaction_ids(); p=create_merkle_proof(ids,tx_index); txid=ids[tx_index]
        return {"transaction_id":txid,"merkle_root":b.merkle_root,"proof":p,"valid":verify_merkle_proof(txid,p,b.merkle_root)}
    except (IndexError,ValueError): raise HTTPException(404,"Transaction or block not found")
