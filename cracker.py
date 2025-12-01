import hashlib
import os
from typing import Dict, List, Tuple
from collections import defaultdict
from itertools import product
import random

PASSWORD_FILE = "passwords.txt"
DICTIONARY_FILE = "dictionary.txt"
CACHE_FILE = "cracked_cache.txt"

# ==========================
# CREATIVE STRATEGY PARAMETERS
# ==========================

# Try variations we might have missed
TRY_DIGITS_BETWEEN_WORDS = True    # word1word2, word12word34
TRY_DIGITS_PREFIX = True           # 10wordwordword
TRY_SPECIAL_CHARS = True           # word-word, word_word, word.word
TRY_CAPITALIZATION = True          # WordWord, WORDword
TRY_REVERSE_WORDS = True           # drowdrow (reverse)
TRY_PARTIAL_WORDS = True           # First 3-4 letters of words

# Sampling
SAMPLE_SIZE = 200000000 

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
# CREATIVE CRACKER
# ==========================

class CreativeCracker:
    
    def __init__(self, hash_to_ids: Dict[str, List[str]], found: Dict[str, str], words: List[str]):
        self.hash_to_ids = hash_to_ids
        self.found = found
        self.remaining_hashes = set(hash_to_ids.keys()) - set(found.keys())
        self.total_hashes = len(hash_to_ids)
        self.attempts = 0
        self.words = words
        self.short_words = sorted(words, key=len)[:500]  # 500 shortest
        
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

    def digits_between_words(self) -> bool:
        """
        Try patterns like: word1word2word3, word12word34, word1word2word
        Focused search with digits between specific positions.
        """
        if not TRY_DIGITS_BETWEEN_WORDS:
            return False
        
        print("\n[DIGITS BETWEEN WORDS]")
        print(f"  Using {len(self.short_words)} short words")
        
        # 2 words with 1-3 digits between
        print("\n  Pattern: word[1-3 digits]word")
        for w1 in self.short_words:
            for w2 in self.short_words:
                for d in range(1000):  # 0-999
                    if self.test(f"{w1}{d}{w2}"):
                        return True
        
        # 3 words with 1-2 digits between first two
        print("\n  Pattern: word[1-2 digits]wordword")
        for w1 in self.short_words[:200]:
            for w2 in self.short_words[:200]:
                for w3 in self.short_words[:200]:
                    for d in range(100):  # 0-99
                        if self.test(f"{w1}{d}{w2}{w3}"):
                            return True
        
        # 4 words with single digit between first two
        print("\n  Pattern: word[digit]wordwordword")
        for w1 in self.short_words[:100]:
            for w2 in self.short_words[:100]:
                for w3 in self.short_words[:100]:
                    for w4 in self.short_words[:100]:
                        for d in range(10):
                            if self.test(f"{w1}{d}{w2}{w3}{w4}"):
                                return True
        
        return False

    def digits_prefix(self) -> bool:
        """Try 1-4 digits as prefix."""
        if not TRY_DIGITS_PREFIX:
            return False
        
        print("\n[DIGITS PREFIX]")
        print("  Pattern: [1-4 digits]word1word2word3...")
        
        for num_digits in range(1, 5):
            print(f"\n  Trying {num_digits} digit prefix...")
            for d in range(10 ** num_digits):
                prefix = str(d).zfill(num_digits)
                
                # prefix + 2 words
                for w1 in self.short_words[:300]:
                    for w2 in self.short_words[:300]:
                        if self.test(f"{prefix}{w1}{w2}"):
                            return True
                
                # prefix + 3 words
                if num_digits <= 2:  # Only for 1-2 digits
                    for w1 in self.short_words[:100]:
                        for w2 in self.short_words[:100]:
                            for w3 in self.short_words[:100]:
                                if self.test(f"{prefix}{w1}{w2}{w3}"):
                                    return True
        
        return False

    def special_characters(self) -> bool:
        """Try special characters as separators."""
        if not TRY_SPECIAL_CHARS:
            return False
        
        print("\n[SPECIAL CHARACTERS]")
        separators = ['', '-', '_', '.', '!', '@']
        print(f"  Separators: {separators}")
        
        # 2-3 words with separators
        for sep in separators:
            if sep == '':
                continue  # Already tried
            
            print(f"\n  Trying separator: '{sep}'")
            
            # 2 words
            for w1 in self.short_words[:300]:
                for w2 in self.short_words[:300]:
                    if self.test(f"{w1}{sep}{w2}"):
                        return True
            
            # 3 words
            for w1 in self.short_words[:100]:
                for w2 in self.short_words[:100]:
                    for w3 in self.short_words[:100]:
                        if self.test(f"{w1}{sep}{w2}{sep}{w3}"):
                            return True
        
        return False

    def capitalization_patterns(self) -> bool:
        """Try capitalization: WordWord, WORDword, etc."""
        if not TRY_CAPITALIZATION:
            return False
        
        print("\n[CAPITALIZATION PATTERNS]")
        
        # 2-3 words with various caps
        patterns = [
            lambda w: w.capitalize(),  # Word
            lambda w: w.upper(),       # WORD
            lambda w: w,               # word
        ]
        
        print("  Trying 2-word with caps...")
        for w1 in self.short_words[:300]:
            for w2 in self.short_words[:300]:
                for p1 in patterns:
                    for p2 in patterns:
                        if self.test(f"{p1(w1)}{p2(w2)}"):
                            return True
        
        print("  Trying 3-word with first capitalized...")
        for w1 in self.short_words[:150]:
            for w2 in self.short_words[:150]:
                for w3 in self.short_words[:150]:
                    if self.test(f"{w1.capitalize()}{w2}{w3}"):
                        return True
        
        return False

    def reverse_words(self) -> bool:
        """Try reversed words: drowdrow."""
        if not TRY_REVERSE_WORDS:
            return False
        
        print("\n[REVERSE WORDS]")
        
        # Single reversed words
        print("  Single reversed words...")
        for w in self.short_words:
            if self.test(w[::-1]):
                return True
        
        # Reversed + normal
        print("  Reversed + normal combinations...")
        for w1 in self.short_words[:200]:
            for w2 in self.short_words[:200]:
                if self.test(f"{w1[::-1]}{w2}"):
                    return True
                if self.test(f"{w1}{w2[::-1]}"):
                    return True
        
        return False

    def partial_words(self) -> bool:
        """Try truncated words: first 3-4 letters."""
        if not TRY_PARTIAL_WORDS:
            return False
        
        print("\n[PARTIAL WORDS]")
        print("  Using first 3-4 letters of words...")
        
        partials = []
        for w in self.short_words:
            if len(w) >= 3:
                partials.append(w[:3])
            if len(w) >= 4:
                partials.append(w[:4])
        
        partials = list(set(partials))[:500]  # Dedupe and limit
        
        # 3-4 partial words
        print(f"  Trying {len(partials)} partial words in combinations...")
        for p1 in partials[:150]:
            for p2 in partials[:150]:
                for p3 in partials[:150]:
                    if self.test(f"{p1}{p2}{p3}"):
                        return True
        
        return False

    def mega_random_creative(self) -> bool:
        """
        Random sampling with creative variations.
        """
        print("\n[MEGA RANDOM CREATIVE SAMPLING]")
        print(f"  {SAMPLE_SIZE:,} attempts with multiple strategies...")
        
        separators = ['', '1', '2', '10', '12', '-', '_']
        
        for i in range(SAMPLE_SIZE):
            # Pick random strategy
            strategy = random.randint(1, 8)
            
            if strategy == 1:
                # 4 words, no separator
                words = random.choices(self.short_words, k=4)
                candidate = ''.join(words)
            
            elif strategy == 2:
                # 3 words + digit suffix
                words = random.choices(self.short_words, k=3)
                digit = random.randint(0, 999)
                candidate = ''.join(words) + str(digit)
            
            elif strategy == 3:
                # 4 words with random digit between first two
                words = random.choices(self.short_words, k=4)
                digit = random.randint(0, 99)
                candidate = words[0] + str(digit) + words[1] + words[2] + words[3]
            
            elif strategy == 4:
                # Digit prefix + 3 words
                digit = random.randint(0, 999)
                words = random.choices(self.short_words, k=3)
                candidate = str(digit) + ''.join(words)
            
            elif strategy == 5:
                # 2-3 words with separator
                n = random.choice([2, 3])
                words = random.choices(self.short_words, k=n)
                sep = random.choice(separators)
                candidate = sep.join(words)
            
            elif strategy == 6:
                # Capitalized first word
                words = random.choices(self.short_words, k=random.choice([2, 3, 4]))
                words[0] = words[0].capitalize()
                candidate = ''.join(words)
            
            elif strategy == 7:
                # Mixed case random
                words = random.choices(self.short_words, k=random.choice([2, 3]))
                words = [w.upper() if random.random() > 0.5 else w for w in words]
                candidate = ''.join(words)
            
            else:  # strategy == 8
                # Partial words (first 3-4 letters)
                words = random.choices(self.short_words, k=4)
                partials = [w[:random.choice([3, 4])] if len(w) >= 3 else w for w in words]
                candidate = ''.join(partials)
            
            if self.test(candidate):
                return True
            
            if (i + 1) % 1000000 == 0:
                print(f"    Progress: {i+1:,}/{SAMPLE_SIZE:,}")
        
        return False

def main():
    print("=" * 70)
    print(" CREATIVE PASSWORD CRACKER - Kitchen Sink Edition")
    print("=" * 70)
    
    # Load data
    id_to_hash, hash_to_ids = load_hashes(PASSWORD_FILE)
    words = load_dictionary(DICTIONARY_FILE)
    cache = load_cache(CACHE_FILE)
    
    print(f"\n[+] Users: {len(id_to_hash)}")
    print(f"[+] Unique hashes: {len(hash_to_ids)}")
    print(f"[+] Dictionary words: {len(words)}")
    print(f"[+] Cached: {len(cache)}")
    
    # Check cache
    found = {}
    for uid, h in id_to_hash.items():
        if h in cache:
            found[h] = cache[h]
    
    print(f"[+] Found {len(found)} passwords in cache")
    
    if len(found) == len(hash_to_ids):
        print("\n[*] All passwords already cracked!")
    else:
        remaining = len(hash_to_ids) - len(found)
        print(f"\n[*] Need to crack {remaining} more passwords...")
        print("\n[*] Trying creative strategies...\n")
        
        cracker = CreativeCracker(hash_to_ids, found, words)
        
        # Try all creative strategies
        strategies = [
            ("Digits Between Words", cracker.digits_between_words),
            ("Digits Prefix", cracker.digits_prefix),
            ("Special Characters", cracker.special_characters),
            ("Capitalization", cracker.capitalization_patterns),
            ("Reverse Words", cracker.reverse_words),
            ("Partial Words", cracker.partial_words),
            ("Mega Random Creative", cracker.mega_random_creative),
        ]
        
        for name, strategy in strategies:
            if cracker.remaining_hashes:
                print(f"\n{'='*70}")
                print(f" STRATEGY: {name}")
                print('='*70)
                strategy()
            else:
                break
        
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
        print("\nSuggestions:")
        print("  - Share examples of cracked passwords for pattern analysis")
        print("  - Try reducing word list to top 100-200 most common words")
        print("  - Consider GPU-based cracking (hashcat)")
        print("  - Check if passwords might be from a different word list")
    print("=" * 70)

if __name__ == "__main__":
    main()