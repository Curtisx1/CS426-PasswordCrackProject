import hashlib
import os
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
from itertools import product
import random

PASSWORD_FILE = "passwords.txt"
DICTIONARY_FILE = "dictionary.txt"
CACHE_FILE = "cracked_cache.txt"

# ==========================
# PATTERN-LEARNING PARAMETERS
# ==========================

LEARN_FROM_CRACKED = True      # Analyze cracked passwords for patterns
USE_WORD_FREQUENCY = True      # Track which words appear most
PRIORITIZE_PATTERNS = True     # Try common patterns first

# Word list sizes
WORDS_FOR_2_COMBO = 3000
WORDS_FOR_3_COMBO = 1000
WORDS_FOR_4_COMBO = 500

# Sampling
RANDOM_SAMPLE_SIZE = 100000000  

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

def analyze_cracked_passwords(cracked: Dict[str, str], all_words: Set[str]) -> Dict:
    """
    Analyze cracked passwords to find patterns.
    Returns insights about word usage, lengths, etc.
    """
    print("\n" + "=" * 70)
    print(" PATTERN ANALYSIS OF CRACKED PASSWORDS")
    print("=" * 70)
    
    analysis = {
        'word_frequency': Counter(),
        'word_count_distribution': Counter(),
        'length_distribution': Counter(),
        'common_words': [],
        'avg_word_length': [],
        'patterns': []
    }
    
    all_words_set = set(all_words)
    
    for pw in cracked.values():
        # Try to break password into dictionary words
        words_found = []
        remaining = pw
        
        # Greedy approach: find longest matching words
        while remaining:
            found = False
            # Try from longest to shortest
            for length in range(min(len(remaining), 20), 0, -1):
                prefix = remaining[:length]
                if prefix in all_words_set:
                    words_found.append(prefix)
                    remaining = remaining[length:]
                    found = True
                    break
            if not found:
                # Check if it's a digit
                if remaining[0].isdigit():
                    # Skip digits
                    digit_str = ""
                    while remaining and remaining[0].isdigit():
                        digit_str += remaining[0]
                        remaining = remaining[1:]
                else:
                    # Can't parse, skip char
                    remaining = remaining[1:]
        
        if words_found:
            analysis['word_count_distribution'][len(words_found)] += 1
            for word in words_found:
                analysis['word_frequency'][word] += 1
                analysis['avg_word_length'].append(len(word))
        
        analysis['length_distribution'][len(pw)] += 1
    
    # Print analysis
    print(f"\nTotal cracked passwords analyzed: {len(cracked)}")
    
    if analysis['word_count_distribution']:
        print("\nWord count distribution:")
        for count in sorted(analysis['word_count_distribution'].keys()):
            freq = analysis['word_count_distribution'][count]
            print(f"  {count} words: {freq} passwords")
    
    if analysis['word_frequency']:
        print("\nTop 20 most common words in cracked passwords:")
        for word, count in analysis['word_frequency'].most_common(20):
            print(f"  '{word}': {count} times")
        
        analysis['common_words'] = [w for w, c in analysis['word_frequency'].most_common(100)]
    
    if analysis['avg_word_length']:
        avg = sum(analysis['avg_word_length']) / len(analysis['avg_word_length'])
        print(f"\nAverage word length: {avg:.1f} characters")
    
    print("\nPassword length distribution:")
    for length in sorted(analysis['length_distribution'].keys()):
        freq = analysis['length_distribution'][length]
        print(f"  {length} chars: {freq} passwords")
    
    print("=" * 70 + "\n")
    
    return analysis

# ==========================
# PATTERN-AWARE CRACKER
# ==========================

class PatternAwareCracker:
    
    def __init__(self, hash_to_ids: Dict[str, List[str]], found: Dict[str, str], 
                 all_words: List[str], analysis: Dict = None):
        self.hash_to_ids = hash_to_ids
        self.found = found
        self.remaining_hashes = set(hash_to_ids.keys()) - set(found.keys())
        self.total_hashes = len(hash_to_ids)
        self.attempts = 0
        self.all_words = all_words
        self.analysis = analysis or {}
        
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

    def pattern_guided_search(self) -> bool:
        """
        Use patterns from cracked passwords to guide search.
        """
        if not self.analysis or not self.analysis.get('common_words'):
            print("[!] No pattern analysis available, skipping pattern-guided search")
            return False
        
        common_words = self.analysis['common_words'][:200]  # Top 200 words
        print(f"\n[PATTERN-GUIDED] Using top {len(common_words)} words from cracked passwords")
        
        # Determine most common word count
        word_counts = self.analysis['word_count_distribution']
        if word_counts:
            most_common_count = word_counts.most_common(1)[0][0]
            print(f"  Most common word count: {most_common_count}")
            
            # Focus on that word count
            if most_common_count == 2:
                return self._try_n_words_targeted(common_words, 2)
            elif most_common_count == 3:
                return self._try_n_words_targeted(common_words, 3)
            elif most_common_count == 4:
                return self._try_n_words_targeted(common_words, 4)
        
        return False

    def _try_n_words_targeted(self, words: List[str], n: int) -> bool:
        """Try n-word combos with targeted word list."""
        total = len(words) ** n
        print(f"  Trying {n}-word combos with {len(words)} words = {total:,} combinations")
        
        if total > 1000000000:  # More than 1B
            print(f"  Still too many! Sampling {RANDOM_SAMPLE_SIZE:,} random combinations...")
            for i in range(RANDOM_SAMPLE_SIZE):
                combo = random.choices(words, k=n)
                if self.test(''.join(combo)):
                    return True
                if (i + 1) % 1000000 == 0:
                    print(f"    Sample progress: {i+1:,}/{RANDOM_SAMPLE_SIZE:,}")
        else:
            checked = 0
            for combo in product(words, repeat=n):
                if self.test(''.join(combo)):
                    return True
                checked += 1
                if checked % 1000000 == 0:
                    print(f"    Progress: {checked:,}/{total:,}")
        
        return False

    def massive_random_sampling(self) -> bool:
        """
        Last resort: massive random sampling across all word lengths.
        """
        print(f"\n[MASSIVE RANDOM SAMPLING]")
        print(f"  Sampling {RANDOM_SAMPLE_SIZE:,} random combinations...")
        print(f"  Using all {len(self.all_words)} words")
        
        # Weight words by frequency if we have it
        if self.analysis and self.analysis.get('word_frequency'):
            word_weights = []
            for w in self.all_words:
                freq = self.analysis['word_frequency'].get(w, 1)
                word_weights.append(freq)
            print("  Using frequency-weighted sampling")
        else:
            word_weights = None
        
        for i in range(RANDOM_SAMPLE_SIZE):
            # Randomly pick 2, 3, or 4 words
            n_words = random.choices([2, 3, 4], weights=[0.3, 0.3, 0.4])[0]
            
            if word_weights:
                combo = random.choices(self.all_words, weights=word_weights, k=n_words)
            else:
                combo = random.choices(self.all_words, k=n_words)
            
            if self.test(''.join(combo)):
                return True
            
            if (i + 1) % 1000000 == 0:
                print(f"    Progress: {i+1:,}/{RANDOM_SAMPLE_SIZE:,}")
        
        return False

def main():
    print("=" * 70)
    print(" PATTERN-LEARNING PASSWORD CRACKER")
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
    print("\n[*] Loading cached passwords...")
    for uid, h in id_to_hash.items():
        if h in cache:
            found[h] = cache[h]
    
    print(f"[+] Found {len(found)} passwords in cache")
    
    # Analyze cracked passwords
    analysis = None
    if LEARN_FROM_CRACKED and found:
        analysis = analyze_cracked_passwords(found, set(words))
    
    if len(found) == len(hash_to_ids):
        print("\n[*] All passwords already cracked!")
    else:
        remaining = len(hash_to_ids) - len(found)
        print(f"\n[*] Need to crack {remaining} more passwords...")
        print(f"[*] Starting pattern-aware attack...\n")
        
        cracker = PatternAwareCracker(hash_to_ids, found, words, analysis)
        
        # Attack sequence
        if cracker.remaining_hashes and analysis:
            print("[*] Phase 1: Pattern-guided search")
            cracker.pattern_guided_search()
        
        if cracker.remaining_hashes:
            print("\n[*] Phase 2: Massive random sampling")
            cracker.massive_random_sampling()
        
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