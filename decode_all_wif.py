import hashlib

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_decode(s):
    decoded = 0
    for char in s:
        decoded = decoded * 58 + BASE58_ALPHABET.index(char)
    return decoded.to_bytes(37, 'big')

def wif_to_private_key_hex(wif):
    try:
        decoded = base58_decode(wif)
        payload = decoded[:-4]
        checksum = decoded[-4:]
        hash_check = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        if checksum != hash_check:
            return None, None, "Invalid checksum"
        
        version = payload[0]
        if version != 0x80:
            return None, None, f"Invalid version: {version:02x}"
        
        if len(payload) == 33:
            private_key_hex = payload[1:33].hex()
            is_compressed = False
        elif len(payload) == 34:
            private_key_hex = payload[1:33].hex()
            is_compressed = True
        else:
            return None, None, f"Invalid payload length: {len(payload)}"
        
        return private_key_hex, is_compressed, "OK"
    except Exception as e:
        return None, None, str(e)

# Full list of all 160 WIF keys
wif_keys_full = """5KC7FNcyy5P4o7tvyTr8SDNNsoQh6DyUdovubWamo7Ah6q71sNN
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
5KcxeoPcnjobFX26wJv5UpJbVkcLu5NtMNpApxkeokXENkgESx7
5JHC3UTAtwLBLWo2oBDMqSChQ7JLoqtDU6zqfhhVJBkxfFkrDW3
5K4VKx9yLDPhqSDzZQmnKhUcdrBNLA1wSYLpY4At18zMCnDBDbB
5HviRxhRoTejnrrV3vWxAsv7exrooe7g9ZaxQES8TuCgz38rU9k
5JwXyuauxDcneqGE6wKoJM1Uwmo4jk8QkxSysjZWVH5o11fcPkc
5HpxiM6bYpzdvnrFE2aVoC3rNjn1p3G8sPCUEnXpn4DmD3QXBU9
5HxYz7iayxeCvcmQ4FqMhTBAthay5Jd8KZbGwN2Tz1qmx7PpTGW
5JQUmgAuW6Nnv8u2ViViXtVUikNGvwQozZo8RojX3kmG6ZF8bmp
5KAo9EqoaihLCAx8arrrTnfbZB1Y29iP3Hprbm3LtBASBfsr2Ej
5KeKTi9GXrrGrVGhqNwaxzpbqTEhgZcwAiA2uDVnE9TfQGyPyL8
5KVE5VxB5d3fSN6GFMqvEgyfZkPgVu9yJEFR1mEKv9RZPucjpr2
5KTTwbbhac1j2pD7r1a3gNERkHcuWLx42uo8r95MfguQGSHAHEB
5JrTZZi3sheeeG2yzr1kbhhwovjw9Ny8pCmuoZm92ewhF34wemq
5J5Jxd4qJXPm6oDAGJK2wDr9Yd9yaCdmEdeKEukoNtyYA4u6ueS
5JRvs5WbEYG5KTL7BdWaZwFJYjMLJ86EmR3qcp5mXcLwYder4Tv
5KLDjgbVbEkvTRqr8Ffug5sbh4duw6zFCewdJ7pWpe3cmYDPEcM
5JrAjPRkMNCLgkLw5VXD84duy3UmSS2CiCD94XN2qhP2bXcrKfR
5JLnBSkeTJm1NqvrEbcfQnhgM8jFtU4iEV6a7FkxirzhYuw2DhE
5K81rkJPX2KoeoE2AaXX6TQjj1s5zHS8rw3YSTMtohaFSGEfRNv
5KXQy1WJfUGLeuTPFNzP7PeH1jCuq5Vxp1cKEtDdPvB119Y6hed
5JhhVEhyhiCqwnVoF7Ftxv8GkWzJnJxmyhiqqiJhKx2VB8dfAVF
5JZqQP7QH1hpMUGnxhiDJsKSSyQPFebJRDn3egmfUnAbPBZZfej
5JGdwqbEA7deWq7MwYZfZwdWany87Ma2KiHC3sjsCTaoerWVqSd
5KCn4SXC7o8tA6WWq1yjunXewr5Q7KoAqSPAPujrXnjha41TEUb
5KBEmJ6pMDNHdBnmPxYnnizF3CEz1NaB71veeoz2PQwxfeTcPJc
5KG9UqF9YpJz7VsueRd6X72AU8He2oTAyfF6onV62ZGpbfLiEm8
5HrEnaGsn6EPLvaFdokXuapBEEstSWHcim8kBADqUWB78Y6qr5d
5Huze1ZJ9bqF2AWdm4cpii7AmDvFQjMpF7rdBU8ji3gLWExXpT9
5K3hqKY9jaW89jXRDUEU3LAekUw23pvei1gFK8Tk77xVgPknZCf
5K916jp3MLnvNmhK1QFHK738DKz7p9vixWsKUsLmCScjJQkU7Ep
5K5TfickSmhvD48vvrUhcGDkeYFeU5EHQ8pD4HVuSkFdzutvyJy
5JrU5qAuhBjid4ZmG6VtWR7ZX5ed3yemx1z2sJT1vQ4nLM52zDZ
5JQcsPcvq7HedgSCWjSiK9HDBk91g7Akp4sVutY9Q5WfSUdCMDA
5Khsf4PLecyUeKSxyJmN4MP3ennhUFxFALfQi1AVQUnXq88Fm1E
5JgbhEaLhknSzoVVN6jwcsaNQ282xpiedKhPK5LMwFuuLN3bc7o
5KDjGjyLENrZzaLdps3C1M5Vfij2q3zdgUrbcwWmtywsytFoCAK
5JH4ernGBVtXYFVd8TD1Cwnq3cdsJGjMkb6ZFhDm4uP8MBW3P7Z
5JJAQ3SoZSTM8drFRmAhU6sXS9xyjYJm9u8gGZtnbr9vPFVhw3b
5JNnPnVf9n5g9MosuqQ37BkyYNVZqkorBXPUqFSyrNAgi1Bkx3N
5Hvyyfy3MfhB1F3DuFTviBYcoRpKrEpd6hFu4dzaJ4FwxbQqCcN
5JK5pJn72X8QwyCCSHZCGth5p95u9nuCA6XtL5UJVAXwhT3hrL5
5JV1UUEzsudQqjnKgx3gYympLU43dQjy9eSzZHvdjJCowfW7xMT
5KcUBxxRkvHoAwt1Az5bkPHu1eJ2tWQU6aRMbcJWVUGSTGRRmiX
5JdXWcXxrYdaMfbpNC8YP23Tb7bsoikAF5U98dMV94RxRTpeJBK
5J5Tk5ATvCNNLzY4cKvnWoUfuM882wJbES9jKSE3t8gBi6yWmCg
5JrLDHp2fbF5AaAdDakbGJyEaCT3ukehonua6F3oDVjSdQGwTY8
5KJZy7jpcaCVLRh6kF6gAbkWtSuMWHH5L6NrxiFgEsNKAAqMtFF
5JrrVwRZz8LL7uBQ6F4ahPN1tawkcRYvgaVnSe4g2JhHthS67EK
5JhxfMxV4BLqbh1YsvEj1UmxDQgpdiYGjGwML1iQ1bekU9rnwKy
5JAnK8xn2qLaa3PFwP678TYzsEXWCchMLDAgCN78n7v9b2o1WLX
5KbfX2TAg9haxPAi27mE2xbX97E3KTa2Dv6TmU4d3ZsNWYjhASP
5JdcJmAPft7pQ3Kjac3PDKqbT55UKoqv5BnpBp46PhPaBunCfZt
5JMpT32mEtc3EeqFjY28SDQMkA7u3dmJa8n2YzHq21P6dJdjnYL
5JceznchHLkJWozPj4px4utZ1kmMKeV6tdEL52LUR2WHhgHaGni
5Jwb8Z1RPrYSsN75AoL1sMWmoysxASms9r6ftbBuqxT4nQiLujt
5J5tmBWqFCxUb9CL9f13kLjLZr68jaTxy1NEMtMFdQScif6dfG4
5K7XsJDCU5FKwSfyFYYcpniM9ejtRXPneLeqaAvsNLbzeDq3STS
5Kg5DvkbKDFYBfbg4SHhGZcerrSTXi7F7Y3w9pBzHQjCN3AaZxC
5K81enaTxrZKmi5jLRuexY2X8Uw9YYoj7KMAqNxem7YphjMvuqJ
5KFsXuASJCjce2sCLeKYqVuUc3xTUXpurr2nX6pnCCuMBcZpnsb
5KJcQRCCU59BXEiMNnMNCm2KLTiPeauKKeC9X3pzRuX7tHvdAgz
5KhDQrXNVec7pfbPGdNHHqTpqTcFPqam7qPeGzZMaweCFryzznJ
5KDrk3HRV1hvXzsRUyRqzfpkiR8WpumtWzshAA1oyscFret1MQ2
5HzCRsYaYQvCqdZWuzzEa9rP18wYPEokjKvgxhw7kEYvDDe4BMH
5KXspjg83R3JM5dDeFaRzwwEKtyNf72dQMJMPDpS7SXRNTYW6w5
5K82gi1UofmqJMfeyAaTXn1yuwW9SsZpYo2EYKHD6daCnqXPbNA
5JBv3dt2p8N96AoVD9NgVLWHyKWVE8iKf7sS5bRNQw3SyXp2Upx
5KTtSYb2A3UyMBsgMJ2NUdXWxy61yN4kRGbqjVvLyF2Q2qkGJWD
5K3LfaZ4jcKGejEHts4SeW9KDKwzYdpturG9d4HPPf9yMeUuehQ
5JEGiWy1nqct2Jr5EoTnFaKGFWAvamMEsiouDG73mY8tMTrHXKw
5JZz6FgRs4JeDGPqZsBij1U6qTNxCDTSxqpy35QUJXFuZChsFDw
5KipRJ9yan7q8qG9Z4ChesjxNBc56PTYvkS1rtRANmEBovgv1QR
5J8vG4MXaB1vt266YGihktfm1SVUM9AeoTGr8FCGVKEiMPqYosw
5JYxAxwHtouVV3mbVaRQm7BQtQBAdLUvCZKCMaawkUctDUN4YJY
5KUp27XQGfBP8L3xcnLvSJmAPcygKtQJGPUDNAG92Tn4LazgHDz
5KAxVUMc6C6ywfYyV7q2Q3gE4o2Z2bav4X9qXxyja42jM42dm4B
5JadB7Nkf29xcSFJTpkwrtVPuvXdTdWbvKapNZdvWz3hdokWqzA
5K3Fy8yZmtKQppWp3X6fAw6c8k7HyLXh9uG5F4nBdmNrVrZFDg5
5Kduaxo2CaJPRixFQYysDfhYV28jhQvKByLQwCkQHZkn5gadPtY
5JHTW8VTTeAFJwgfaSSk2EtFXr3NdtZgifjry6za2kpkoexPWQF
5Ke2JTmMZoavruBghjTwCTC2Uuo3VZgKSGccBcDm5hWMMts3uD8
5KUTejP5WUGDbUJUhEAeVSG7TjZF3tWnmPaeVbesSMBhYDGohXY
5JYQxX94ZY7Dj33WrcinbRBzhLX9w5WpB2BvnhDbksMoKzeMyw4
5J9NTGcMEyXWTqUQGaDJdgDeX7zd5rv5EpvjxTCTewps4kvrfsP
5JbwakrjgPuPvt7sdhMZYMzLB4SLa68bDYWHX491RUmrDX1QiMm
5KX74WdoGXokbE2RrmDQdB7Xdn9iyDcaZ8E9d5wNTWJcWB9pkaD
5JthWByG7kPsrNPxRvuFFTGqVULQwUgeub6GRZjsVipuyrvY3FE
5JM1xFGhPtepyGEJHskQ35SF81sThF6MaiAFjvre5YH3MPFEfzA
5JzfM7GvGUwjVwLBZVrkDcTfiUd9XAktYkN9TUXHt3TAVqAb3AZ
5K4oY3D65tZhRtdiAhMSM2G7fJBfYAyhWtkoHLm7aRyvciHzkhw
5KSg2nNuZ29L5CGTHp6XhKAgZygAhDXSpgd55JvcPzutDSc2SfE
5KDVjRTVVqqbRYaP6XMiKQXNxZKWsfpQagwSdYzLgdsg46ftHgF
5KD7Eg3sWXrUhAGKcYwiHNRTrMWC9v6MZMsPSuthBuMfveSYv2M
5JWg3Fq4S8T3Wq4P3W2DoMY2g1Kq6JjvWHP3ZmwGjPY9R9BC75h
5J7Yn2BoHduwDmKNskj5m4NZRq1fjNH49k554hGMAKg7YivKjY3
5KD6TQy1noTU4rMqqzCXVW8rhRCeB49QYrqXzPVmEFukkC7sxSj
5K1xdc3HJwwFv45333whaMijMLGqvUFFWEPEXdyTwgBzgVs4Eec
5JZPkUGZiXnkGP9ntSm5aRmZ6FCNkbBXPVJ9JX1RGRfe3RieFZg
5JrmP3CPv5tWz6NEAdFsBn38Ee49GTaZoiXkm6wRHZjmMBxFd9z
5KMmaRTKwyWEaVtLorR5XtAWHRU6g6VxEvHsNzgaWY9pBHsFzjc
5K4TSoM6ostaESi2wZFuXwnLos7VUxyDfPGSoio45CXFKapC9Pa
5Jzpai2srYvsPRbUT6wAFtXRTL2AKkbFX3myESwERDAhZngZNrd
5JgkEzxDoiamJSn2xBGXvt3SDLwvpkYqCS5MaDoDmwBMVJnry5N
5Hyb1M8RktxYVH2yFm2iD4wkheBBhv25jfE8PsR7wD2XhDJxm4n
5J5RjkuHUV2zuwhTybHmqzrEcK2bau5yzQFtED2WEdDSc2piV9q
5JS1YgFr7fMkdkLuvQDmVMSrZeuajUFueFVxF8kG54VWTWPXXzW
5J4eVcpEdkZnXBPGyh1NKsqGjtyXxffGDui7dF9Er2PpgnEJaFv
5JWtZUVS5z5Mr7iLhAXC4yBHmweL3AmuovSRY34EtmDodXVkcnC
5K9cfEvUQPt77B6kWYnRBpebJQScCkneyLVhnwZpNteLPDj33Cb
5JeZt96zs2kyumyNagoEETF1X4RUHib4Lrdk6nfHoXmoCKKnXfu
5JdZp75mhfWhXAi55wS3cYCyKnsLRms5HDUBmZu879WGejWPw7Z
5JKNi4ekc1HP7SLQ3CKezmZLned5y3hgVz2ssGbXVh1kirjkP9U
5K1hqAH28FWnujSfbWMviTJDAd1HGL43N4ee52Z5ooRuiwTC8Zj
5JVXdF27hRMyepZJ3hNFrTemYQ7yS3hSy8aT31KwXKwZ7dm6ey8
5Jf9cUsutLpJVsdoKNkqp6FUw5GqQd89mbh5gEjNa2wDYJzJXFr
5Jjt4cZbv6GybZnTHXx33AEJ6PQgYj1cXJ9Nny2dt2StPp9Dhpj
5KVwTZhHruxUrY5ZdHuj58A24wdMmMGoEDJsi76b3kuXVA3vtbc
5JDMcqbegafhXkAhtbP6mdXhWVCN2oebM4cMdqUCjn5HtBrgvYu
5JL3uiCejwNj7R5QfyN5zkrABeoe4ds7QQJxRNnCeQZFGUsSrPA
5HqhBYVfm8TpFu75GTN6575NedHyfKeFfdFGfAJK79LCnzfnxFM
5Jj4mtruvpopPjAxm9YpFVJJ7AUY9EUBMStH7mZUA8mF7tb7nMM
5K2N9tneF4JBAkwf6J6xJ4UkajpEpdqYTauCyzKwQVDoh4mWsfV
5KAGAJ4JmQm7vtZAtHR277aXb4gtJM5hG9UgN3UE9WKPncX7e2P
5J2VLSQS8DRMsRijdbpaufU1euD2YepyUyqi8JXBfbmThSQgYf4
5JmFwaYXCTTFLLXymkjV9iL95HJoJmg7EuEU6Z3ipx8QEz6Y2Mf
5JPZqTUvexxSnPGdAG8cLKJd2B3wX8bonZnweKYPkqWsaZCo7o9
5J7HtWetWmLN6vvRTa4JoKKoVtjBoMi5hf9P2n9kpnERFKLtEs1
5KDQQEbAKiJA8FF8CYuQNG6o6Qy7cAJaKNmAEv9TYqyjiTL9LsZ
5KfyGsNWpCkMU8XwKe9xdtRPgPEsEF2P9GWfRvE3PtsQqWTj5y3
5KhFQ6KExLi4okCQf4LjwCVCm56ksSQcc7pBeKmFLFP6YgJJNQX
5KLpvQ5PimPSQQF89FPtMPhCeFbbMbzm5Z8s5nBCCeUHirNYg7p
5JQmpchz7WNHsUPev6sxw2JmTGatU6TKUGxoGRGM8USk3FUrwqG
5K2qTycmUqo9gtQTC8BjPfGeKjjgkZRj14ZJ21eTJJ9gkNyQ852
5JUMxR2FZsj15CZAAurhg9KqKf7bmWJ8mEGN7rnW4ZrGeiTTS9H
5JjZWqE3Y5hTSkqGfQHMuqudoUto54v4taMsVcwbWU2Q12DzLDG
5KkCm7b3zbYVH1ALbX4C8i24u9uDKM6WxBs6MwMimyhPm2GBpVt
5JNyqXGS7WbXXa5o3TnpCFTmBL2p1Yg99m59cBxpWyTvzGiRW5S
5JCn7cxoSPtArx5V7eCB91iBPiqUYUrYYgBAKRLvA4BmoxGKtad
5JuYU77XRDu2VrqpB8EWto1DUVn24QYoVajCVsge1zT7dgSSgUM""".strip().split('\n')

print("=" * 100)
print("WIF Private Key Decoder - Complete List")
print("=" * 100)
print(f"Total WIF keys to process: {len(wif_keys_full)}\n")

results = []
errors = []

for i, wif in enumerate(wif_keys_full, 1):
    privkey_hex, compressed, status = wif_to_private_key_hex(wif)
    if privkey_hex:
        results.append((i, wif, privkey_hex, compressed))
    else:
        errors.append((i, wif, status))

print(f"Successfully decoded: {len(results)}/{len(wif_keys_full)}")
print(f"Errors: {len(errors)}")

if errors:
    print("\nFailed WIF keys:")
    for idx, wif, err in errors:
        print(f"  #{idx}: {wif} - {err}")

# Save results
print("\nSaving results...")

# Full CSV with all details
with open('all_decoded_wif_keys.csv', 'w') as f:
    f.write("Index,WIF,Private_Key_Hex,Compressed\n")
    for idx, wif, hex_key, compressed in results:
        f.write(f"{idx},{wif},{hex_key},{compressed}\n")

# Hex only
with open('all_private_keys_hex.txt', 'w') as f:
    for idx, wif, hex_key, compressed in results:
        f.write(f"{hex_key}\n")

print(f"✓ Saved CSV: all_decoded_wif_keys.csv ({len(results)} keys)")
print(f"✓ Saved hex: all_private_keys_hex.txt ({len(results)} keys)")

# Display first 10 and last 10
print("\n" + "=" * 100)
print("First 10 decoded keys:")
print("=" * 100)
for idx, wif, hex_key, compressed in results[:10]:
    print(f"{idx:3d}. {hex_key}")

print("\n...")
print(f"\nLast 10 decoded keys:")
print("=" * 100)
for idx, wif, hex_key, compressed in results[-10:]:
    print(f"{idx:3d}. {hex_key}")
