import hashlib
import os
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from itertools import product, permutations
import random

PASSWORD_FILE = "passwords.txt"
DICTIONARY_FILE = "dictionary.txt"
CACHE_FILE = "cracked_cache.txt"

# ==========================
# SMART WORD-COMBO PARAMETERS
# ==========================

MAX_MULTI_WORDS = 4

# Different word list sizes for different combo lengths
WORDS_FOR_2_COMBO = 6000     
WORDS_FOR_3_COMBO = 3000     
WORDS_FOR_4_COMBO = 1000     

# Smart strategies for 4-word
TRY_4_WORD_SMART = True        
SAMPLE_4_WORD_COMBOS = 50000000  
TRY_4_WORD_NO_REPEATS = True  

PROGRESS_INTERVAL = 1000000

# ==========================
# UTILITIES
# ==========================

def sha1_hex(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def load_hashes(password_file: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    id_to_hash = {}
    hash_to_ids = defaultdict(list)
    
    with open(password_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                user_id, hash_hex = parts
                hash_hex = hash_hex.lower()
                id_to_hash[user_id] = hash_hex
                hash_to_ids[hash_hex].append(user_id)
    
    return id_to_hash, dict(hash_to_ids)

def load_dictionary(dict_file: str) -> List[str]:
    words = []
    seen = set()
    with open(dict_file, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w and w not in seen:
                words.append(w)
                seen.add(w)
    return words

def load_cache(cache_file: str) -> Dict[str, str]:
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split(" ", 1)
                if len(parts) == 2:
                    cache[parts[0].lower()] = parts[1]
    return cache

def save_cache(cache_file: str, cache_dict: Dict[str, str]):
    with open(cache_file, "w", encoding="utf-8") as f:
        for h, pw in sorted(cache_dict.items()):
            f.write(f"{h} {pw}\n")

# ==========================
# SMART WORD CRACKER
# ==========================

class SmartWordCracker:
    
    def __init__(self, hash_to_ids: Dict[str, List[str]], found: Dict[str, str]):
        self.hash_to_ids = hash_to_ids
        self.found = found
        self.remaining_hashes = set(hash_to_ids.keys()) - set(found.keys())
        self.total_hashes = len(hash_to_ids)
        self.attempts = 0
        
    def test(self, candidate: str) -> bool:
        """Test single candidate."""
        self.attempts += 1
        
        if self.attempts % PROGRESS_INTERVAL == 0:
            print(f"    [{self.attempts:,} attempts, {len(self.found)}/{self.total_hashes} found]")
        
        h = sha1_hex(candidate)
        
        if h in self.remaining_hashes:
            self.found[h] = candidate
            self.remaining_hashes.remove(h)
            for uid in self.hash_to_ids[h]:
                print(f"\n>>> CRACKED! User {uid}: {candidate} <<<\n")
            
            if not self.remaining_hashes:
                print(f"\n*** ALL PASSWORDS CRACKED! ({self.attempts:,} attempts) ***")
                return True
        return False

    def single_word_attack(self, words: List[str]) -> bool:
        """Try single words."""
        print(f"[*] Single words ({len(words)} words)...")
        
        for w in words:
            if self.test(w):
                return True
        
        return False

    def two_word_attack(self, words: List[str]) -> bool:
        """2-word combinations."""
        working_words = sorted(words, key=len)[:WORDS_FOR_2_COMBO]
        total = len(working_words) ** 2
        print(f"\n[2-WORD] Using {len(working_words)} words = {total:,} combinations")
        
        checked = 0
        for word_combo in product(working_words, repeat=2):
            if self.test(''.join(word_combo)):
                return True
            checked += 1
            if checked % 1000000 == 0:
                print(f"    Progress: {checked:,}/{total:,} ({100*checked//total}%)")
        
        return False

    def three_word_attack(self, words: List[str]) -> bool:
        """3-word combinations."""
        working_words = sorted(words, key=len)[:WORDS_FOR_3_COMBO]
        total = len(working_words) ** 3
        print(f"\n[3-WORD] Using {len(working_words)} words = {total:,} combinations")
        
        checked = 0
        for word_combo in product(working_words, repeat=3):
            if self.test(''.join(word_combo)):
                return True
            checked += 1
            if checked % 1000000 == 0:
                print(f"    Progress: {checked:,}/{total:,} ({100*checked//total}%)")
        
        return False

    def four_word_attack_smart(self, words: List[str]) -> bool:
        """
        Smart 4-word attack with multiple strategies.
        """
        working_words = sorted(words, key=len)[:WORDS_FOR_4_COMBO]
        total_possible = len(working_words) ** 4
        
        print(f"\n[4-WORD SMART] Using {len(working_words)} words")
        print(f"  Full exhaustive search: {total_possible:,} combinations (TOO MANY!)")
        print(f"  Using smart strategies instead...\n")
        
        # Strategy 1: No repeated words (reduces space significantly)
        if TRY_4_WORD_NO_REPEATS and len(working_words) >= 4:
            print(f"  Strategy 1: 4 DIFFERENT words")

            n = len(working_words)
            total_unique = n * (n-1) * (n-2) * (n-3)
            print(f"    Combinations: {total_unique:,}")
            
            checked = 0
            for w1 in working_words:
                for w2 in working_words:
                    if w2 == w1:
                        continue
                    for w3 in working_words:
                        if w3 == w1 or w3 == w2:
                            continue
                        for w4 in working_words:
                            if w4 == w1 or w4 == w2 or w4 == w3:
                                continue
                            
                            if self.test(w1 + w2 + w3 + w4):
                                return True
                            
                            checked += 1
                            if checked % 1000000 == 0:
                                print(f"      Progress: {checked:,}/{total_unique:,}")
        
        # Strategy 2: Random sampling of full space
        if TRY_4_WORD_SMART:
            print(f"\n  Strategy 2: Random sampling ({SAMPLE_4_WORD_COMBOS:,} attempts)")
            print(f"    Sampling from full {total_possible:,} combination space")
            
            for i in range(SAMPLE_4_WORD_COMBOS):
                # Pick 4 random words
                word_combo = random.choices(working_words, k=4)
                if self.test(''.join(word_combo)):
                    return True
                
                if (i + 1) % 1000000 == 0:
                    print(f"      Progress: {i+1:,}/{SAMPLE_4_WORD_COMBOS:,}")
        
        # Strategy 3: Specific patterns (short+short+short+short)
        print(f"\n  Strategy 3: Shortest words only (2-4 letters)")
        very_short = [w for w in working_words if len(w) <= 4]
        if len(very_short) >= 4:
            total_short = len(very_short) ** 4
            print(f"    Using {len(very_short)} words = {total_short:,} combinations")
            
            if total_short < 10000000:  
                checked = 0
                for word_combo in product(very_short, repeat=4):
                    if self.test(''.join(word_combo)):
                        return True
                    checked += 1
                    if checked % 100000 == 0:
                        print(f"      Progress: {checked:,}/{total_short:,}")
            else:
                print(f"    Still too many, skipping exhaustive...")
        
        return False

def main():
    print("=" * 70)
    print(" SMART WORD CRACKER - Multi-Strategy Attack")
    print("=" * 70)
    
    # Load data
    id_to_hash, hash_to_ids = load_hashes(PASSWORD_FILE)
    words = load_dictionary(DICTIONARY_FILE)
    cache = load_cache(CACHE_FILE)
    
    print(f"\n[+] Users: {len(id_to_hash)}")
    print(f"[+] Unique hashes: {len(hash_to_ids)}")
    print(f"[+] Dictionary words: {len(words)}")
    print(f"[+] Cached: {len(cache)}")
    
    # Show strategy
    print(f"\nAttack Strategy:")
    print(f"  2-word: Use {WORDS_FOR_2_COMBO} words")
    print(f"  3-word: Use {WORDS_FOR_3_COMBO} shortest words")
    print(f"  4-word: Use {WORDS_FOR_4_COMBO} shortest words + smart sampling")
    
    # Check cache
    found = {}
    print("\n[*] Checking cache...")
    cache_hits = 0
    for uid, h in id_to_hash.items():
        if h in cache:
            found[h] = cache[h]
            cache_hits += 1
            print(f"[CACHE] User {uid}: {cache[h]}")
    
    if cache_hits > 0:
        print(f"\n[+] Found {cache_hits} passwords in cache")
    
    if len(found) == len(hash_to_ids):
        print("\n[*] All passwords in cache!")
    else:
        remaining = len(hash_to_ids) - len(found)
        print(f"\n[*] Need to crack {remaining} more passwords...\n")
        
        cracker = SmartWordCracker(hash_to_ids, found)
        
        # Attack sequence
        if cracker.remaining_hashes:
            cracker.single_word_attack(words)
        
        if cracker.remaining_hashes:
            cracker.two_word_attack(words)
        
        if cracker.remaining_hashes:
            cracker.three_word_attack(words)
        
        if cracker.remaining_hashes:
            cracker.four_word_attack_smart(words)
        
        print(f"\n[*] Attack complete")
        print(f"[*] Total attempts: {cracker.attempts:,}")
        print(f"[*] Cracked: {len(found)}/{len(hash_to_ids)}")
    
    # Update cache
    updated_cache = dict(cache)
    updated_cache.update(found)
    save_cache(CACHE_FILE, updated_cache)
    
    new_cracks = len([h for h in found if h not in cache])
    if new_cracks > 0:
        print(f"[*] Cache: +{new_cracks} new passwords saved")
    
    # Summary
    print("\n" + "=" * 70)
    print(" FINAL RESULTS")
    print("=" * 70)
    
    cracked = 0
    not_cracked = []
    for uid in sorted(id_to_hash.keys(), key=lambda x: int(x) if x.isdigit() else x):
        h = id_to_hash[uid]
        if h in found:
            print(f"User {uid:>4}: {found[h]}")
            cracked += 1
        else:
            print(f"User {uid:>4}: <NOT CRACKED>")
            not_cracked.append(uid)
    
    print(f"\n{'='*70}")
    print(f"Success: {cracked}/{len(id_to_hash)} ({100*cracked//max(len(id_to_hash),1)}%)")
    if not_cracked:
        print(f"Still need: {', '.join(not_cracked)}")
    print("=" * 70)

if __name__ == "__main__":
    main()