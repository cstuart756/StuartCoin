import hashlib


def sha256_hex(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def calculate_merkle_root(transaction_ids):
    if not transaction_ids:
        return sha256_hex("")
    level = list(transaction_ids)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            sha256_hex(level[index] + level[index + 1])
            for index in range(0, len(level), 2)
        ]
    return level[0]


def create_merkle_proof(transaction_ids, target_index):
    if not transaction_ids:
        raise ValueError("Cannot create proof for empty tree.")
    if target_index < 0 or target_index >= len(transaction_ids):
        raise ValueError("Invalid transaction index.")
    level, index, proof = list(transaction_ids), target_index, []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sibling_index = index + 1 if index % 2 == 0 else index - 1
        proof.append({
            "hash": level[sibling_index],
            "position": "right" if index % 2 == 0 else "left",
        })
        level = [
            sha256_hex(level[position] + level[position + 1])
            for position in range(0, len(level), 2)
        ]
        index //= 2
    return proof


def verify_merkle_proof(transaction_id, proof, merkle_root):
    current_hash = transaction_id
    for step in proof:
        sibling_hash = step["hash"]
        if step["position"] == "left":
            current_hash = sha256_hex(sibling_hash + current_hash)
        elif step["position"] == "right":
            current_hash = sha256_hex(current_hash + sibling_hash)
        else:
            return False
    return current_hash == merkle_root
