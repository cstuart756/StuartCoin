from .wallet import Wallet
from .blockchain import Blockchain

def demo():
    stuart,alice=Wallet(),Wallet(); bc=Blockchain(difficulty=2)
    bc.mine_pending_transactions(stuart.address)
    tx=bc.create_transaction(stuart,alice.address,12.5); bc.add_transaction(tx); bc.mine_pending_transactions(stuart.address)
    print("Stuart",stuart.address,bc.get_balance(stuart.address)); print("Alice",alice.address,bc.get_balance(alice.address)); print("Valid",bc.is_chain_valid())
if __name__=="__main__": demo()
