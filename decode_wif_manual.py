import hashlib

# Base58 alphabet
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_decode(s):
    """Decode a Base58 encoded string to bytes"""
    decoded = 0
    for char in s:
        decoded = decoded * 58 + BASE58_ALPHABET.index(char)
    return decoded.to_bytes(37, 'big')  # WIF is typically 37 bytes when decoded

def wif_to_private_key_hex(wif):
    """Convert WIF to hexadecimal private key"""
    try:
        # Decode base58
        decoded = base58_decode(wif)
        
        # Verify checksum
        payload = decoded[:-4]
        checksum = decoded[-4:]
        hash_check = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        if checksum != hash_check:
            return None, None, "Invalid checksum"
        
        # Extract private key
        # First byte is version (0x80 for mainnet)
        # Next 32 bytes are the private key
        # Optional last byte 0x01 indicates compressed
        
        version = payload[0]
        if version != 0x80:
            return None, None, f"Invalid version: {version:02x}"
        
        if len(payload) == 33:
            # Uncompressed
            private_key_hex = payload[1:33].hex()
            is_compressed = False
        elif len(payload) == 34:
            # Compressed
            private_key_hex = payload[1:33].hex()
            is_compressed = True
        else:
            return None, None, f"Invalid payload length: {len(payload)}"
        
        return private_key_hex, is_compressed, "OK"
    except Exception as e:
        return None, None, str(e)

wif_keys = """5KC7FNcyy5P4o7tvyTr8SDNNsoQh6DyUdovubWamo7Ah6q71sNN
5KBVNusnnAyijeJu76GSYUDbfmRruXGhJmoG317gcrAygBJVrNn
5KLEa4gAbbkYJoDfV919Lkh8ZFMNKrvCj7m5RZDt9iQwSc7tNDz
5JQskA7hBDRNtRiPEwfjWHMLt6naobixZXPBGnESGFz8hp3F9SB
5JMSj82vfRcevR1Z6KrHr3gGhRsJa2Mh8dVHQsM2WTtQ2apnP14
5JA9qKY6exzmuh5ELCZXTphFpycsUDYfHt4zytZBG4yJD1iE3Cz
5Ju2JP8A7MgqiX8dfK7yVwNzLq5MuQcYMa2GVc9vTHZAxFoa9up
5JWbGgpbqsursDfccNVJ2tPHzPLAkHRUHUP3PVFFo4QDCpqSpJ4
5JkaXuhTZddPf3xFeGgP9gTdwABxkW62N19t2NPthb6BX5gPjWs
5JoqgQMKeooxcs4xDtKx39Hht9ThLNb6Q3eZaYEhE7NLXJqFhyr
5K2WFTP4NFanj82N8o4NHMAc7GTiGSNccD9i21YxiEYNce2WKa8
5Jo2P1X6DWKDTTY9916YcDULi38PkXUP6ks7os9Tw6Z8g6g5njJ
5Jm4GPNCYcFDmUv7PzaCzhXzrwnH6D8wkzVZLNurfPMEwmj3hoH
5KT7djdQ3FKzJiqmay9erCyToMynCcpzh8s28HRDvnAdV7Zwg6Y
5KRLwEChNLesphRA4QDoDnmKPbU3tvsc4Q9e3yXbZkVu9faoRnN
5KDDkvkb2GsveSz83AhpYSi4wZo5tZQ1VMCSuHzb4VmDUZxDAfU
5Hwz3gkin3i8P5kkoLiBD72qV4gfnCZ1Y4hsTPEtRLtqwtA3ufm
5KLAJX6SkcPDdGPYsHQVmUVtWTD9Da5w8gmLriRCmad7HMw1N4Q
5JegBGihAdQA3jznH6pWy2e3rwXrfTmyDo8zxZLtXF2wqAPJcXk
5KcxeoPcnjobFX26wJv5UpJbVkcLu5NtMNpApxkeokXENkgESx7""".strip().split('\n')

print("=" * 100)
print("WIF to Private Key Hex Conversion")
print("=" * 100)
print(f"Total WIF keys to decode: {len(wif_keys)}\n")

print(f"{'#':<4} {'WIF':<52} {'Private Key (Hex)':<66} {'Compressed'}")
print("-" * 100)

results = []
for i, wif in enumerate(wif_keys, 1):
    privkey_hex, compressed, status = wif_to_private_key_hex(wif)
    if privkey_hex:
        results.append((wif, privkey_hex, compressed))
        comp_str = "Yes" if compressed else "No"
        print(f"{i:<4} {wif:<52} {privkey_hex:<66} {comp_str}")
    else:
        print(f"{i:<4} {wif:<52} ERROR: {status}")

print("\n" + "=" * 100)
print(f"Successfully decoded: {len(results)} private keys")
print("=" * 100)

# Save to CSV
with open('decoded_private_keys.csv', 'w') as f:
    f.write("Index,WIF,Private_Key_Hex,Compressed\n")
    for i, (wif, hex_key, compressed) in enumerate(results, 1):
        f.write(f"{i},{wif},{hex_key},{compressed}\n")

print("\n✓ Saved to: decoded_private_keys.csv")

# Also save hex-only format
with open('private_keys_hex_only.txt', 'w') as f:
    for wif, hex_key, compressed in results:
        f.write(f"{hex_key}\n")

print("✓ Saved hex-only to: private_keys_hex_only.txt")
