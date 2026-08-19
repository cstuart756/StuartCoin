import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

class Wallet:
    def __init__(self):
        self.private_key = ec.generate_private_key(ec.SECP256K1())
        self.public_key = self.private_key.public_key()
        self.public_key_hex = self.public_key.public_bytes(Encoding.X962, PublicFormat.CompressedPoint).hex()
        self.address = self.address_from_public_key(self.public_key_hex)

    @staticmethod
    def address_from_public_key(public_key_hex: str) -> str:
        return "STC_" + hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]
