import hashlib
import os

PASSWORD_FILE = "passwords.txt"
DICTIONARY_FILE = "dictionary.txt"
CACHE_FILE = "cracked_cache.txt"

# ==========================
# TUNABLE PARAMETERS
# ==========================

# How far to go with suffixes:
# For project spec "up to 10 numbers", you could set this to 10, but
# be aware that 10^10 is huge. Start smaller and gradually increase.
MAX_SUFFIX_DIGITS_SINGLE = 0    # word + up to 4 digits (0000-9999)
MAX_SUFFIX_DIGITS_MULTI = 1       # (w1+w2)+up to 2 digits

# For multi-word combos, only use a subset of "likely" words (e.g., shortest).
NUM_SHORT_WORDS_FOR_MULTI = 1000   # take the 400 shortest words for multi-word attacks

# Limit how many words in multi-word combos we attempt.
# Project says "up to 4 words"; in practice, 2 or 3 is where it stays feasible.
MAX_MULTI_WORDS = 4               # change to 3 if you want, but be careful.

# Numeric patterns to try (pure digits)
TRY_4_DIGIT = False
TRY_6_DIGIT = False
TRY_YYYYMMDD = False   # try 2000-2025, 01-12, 01-31 (not strict calendar)

# ==========================
# UTILITIES
# ==========================

def sha1_hex(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def load_hashes(password_file):
    """
    Reads passwords.txt, returns:
      id_to_hash: {user_id (str) -> hash_hex}
      hash_to_ids: {hash_hex -> [user_id,...]}
    """
    id_to_hash = {}
    hash_to_ids = {}

    with open(password_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            user_id, hash_hex = parts
            hash_hex = hash_hex.lower()
            id_to_hash[user_id] = hash_hex
            hash_to_ids.setdefault(hash_hex, []).append(user_id)

    return id_to_hash, hash_to_ids


def load_dictionary(dict_file):
    words = []
    with open(dict_file, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                words.append(w.lower())
    return words


def load_cache(cache_file):
    """
    CACHE FORMAT: one entry per line:
       <sha1_hash> <plaintext>
    e.g.,
       7c4a8d09ca3762af61e59520943dc26494f8941b 123456
    """
    cache = {}
    if not os.path.exists(cache_file):
        return cache

    with open(cache_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue
            h, pw = parts
            cache[h.lower()] = pw
    return cache


def save_cache(cache_file, cache_dict):
    """Write the cache dictionary {hash -> pw} to file."""
    with open(cache_file, "w", encoding="utf-8") as f:
        for h, pw in cache_dict.items():
            f.write(f"{h} {pw}\n")


def test_candidate(candidate, hash_to_ids, found, total_hashes):
    """Hash candidate and record if it matches. Return True if we just completed all."""
    h = sha1_hex(candidate)
    if h in hash_to_ids and h not in found:
        found[h] = candidate
        for uid in hash_to_ids[h]:
            print(f"[+] Found password for user {uid}: {candidate}")
        if len(found) == total_hashes:
            print("[*] All passwords cracked for this run, stopping early.")
            return True
    return False


# ==========================
# ATTACK PHASES
# ==========================

def numeric_attack(hash_to_ids, found, total_hashes):
    print("[*] Numeric attack...")

    # 4-digit
    if TRY_4_DIGIT:
        print("    Trying 4-digit numbers (0000-9999)...")
        for n in range(10_000):
            candidate = f"{n:04d}"
            if test_candidate(candidate, hash_to_ids, found, total_hashes):
                return

    # 6-digit
    if TRY_6_DIGIT:
        print("    Trying 6-digit numbers (000000-999999)...")
        for n in range(1_000_000):
            candidate = f"{n:06d}"
            if test_candidate(candidate, hash_to_ids, found, total_hashes):
                return

    # simple yyyymmdd
    if TRY_YYYYMMDD:
        print("    Trying simple date-like yyyymmdd (2000-2025)...")
        for year in range(2000, 2026):
            for month in range(1, 13):
                for day in range(1, 32):
                    candidate = f"{year:04d}{month:02d}{day:02d}"
                    if test_candidate(candidate, hash_to_ids, found, total_hashes):
                        return


def word_attack_single(words, hash_to_ids, found, total_hashes):
    """
    1-word and 1-word+digits (up to MAX_SUFFIX_DIGITS_SINGLE).
    """
    print("[*] Single-word / word+digits attack...")

    # plain words
    print("    Trying plain dictionary words...")
    for w in words:
        if test_candidate(w, hash_to_ids, found, total_hashes):
            return

    # word + up to MAX_SUFFIX_DIGITS_SINGLE digits
    print(f"    Trying word + up to {MAX_SUFFIX_DIGITS_SINGLE} digits...")
    for w in words:
        for num_digits in range(1, MAX_SUFFIX_DIGITS_SINGLE + 1):
            limit = 10 ** num_digits  # e.g., 10, 100, 1000, ...
            for n in range(limit):
                suffix = f"{n:0{num_digits}d}"  # zero-padded
                candidate = w + suffix
                if test_candidate(candidate, hash_to_ids, found, total_hashes):
                    return


def multi_word_attack(words, hash_to_ids, found, total_hashes):
    """
    Multi-word (up to MAX_MULTI_WORDS) + optional digits (up to MAX_SUFFIX_DIGITS_MULTI).
    Uses only the shortest NUM_SHORT_WORDS_FOR_MULTI words to keep runtime sane.
    """
    if MAX_MULTI_WORDS < 2:
        return

    print("[*] Multi-word attack (up to "
          f"{MAX_MULTI_WORDS} words, {MAX_SUFFIX_DIGITS_MULTI} digit suffix)...")

    # choose shortest words to combine
    sorted_by_len = sorted(words, key=len)
    base_words = sorted_by_len[:NUM_SHORT_WORDS_FOR_MULTI]
    print(f"    Using {len(base_words)} shortest words for multi-word combos.")

    # recursive generator for combos of length 2..MAX_MULTI_WORDS
    def dfs(prefix_words, depth):
        base = "".join(prefix_words)

        # test base (no digits)
        if test_candidate(base, hash_to_ids, found, total_hashes):
            return True

        # test with digits
        if MAX_SUFFIX_DIGITS_MULTI > 0:
            for num_digits in range(1, MAX_SUFFIX_DIGITS_MULTI + 1):
                limit = 10 ** num_digits
                for n in range(limit):
                    suffix = f"{n:0{num_digits}d}"
                    candidate = base + suffix
                    if test_candidate(candidate, hash_to_ids, found, total_hashes):
                        return True

        # extend with another word if we haven't hit max depth
        if depth < MAX_MULTI_WORDS:
            for w in base_words:
                prefix_words.append(w)
                if dfs(prefix_words, depth + 1):
                    return True
                prefix_words.pop()
        return False

    # start with each word as root for depth >= 2
    for w in base_words:
        # prefix has at least 2 words, so seed it with [w1, w2] in the first call
        for w2 in base_words:
            if dfs([w, w2], 2):
                return


# ==========================
# MAIN
# ==========================

def main():
    id_to_hash, hash_to_ids = load_hashes(PASSWORD_FILE)
    words = load_dictionary(DICTIONARY_FILE)
    total_hashes = len(id_to_hash)

    print(f"Loaded {total_hashes} hashed passwords.")
    print(f"Loaded {len(words)} dictionary words.")

    # Load cache
    cache = load_cache(CACHE_FILE)
    print(f"Loaded {len(cache)} cached cracked hashes from {CACHE_FILE}.")

    # found = { hash -> plaintext } for THIS run
    found = {}

    # Pre-fill from cache
    print("[*] Checking cache for already-known passwords...")
    for uid, h in id_to_hash.items():
        if h in cache:
            found[h] = cache[h]
            print(f"[CACHE] User {uid}: {cache[h]}")

    if len(found) == total_hashes:
        print("[*] All users resolved from cache; no cracking needed.")
    else:
        # Phase 1: numeric
        numeric_attack(hash_to_ids, found, total_hashes)

        if len(found) < total_hashes:
            # Phase 2: single-word + digits
            word_attack_single(words, hash_to_ids, found, total_hashes)

        if len(found) < total_hashes:
            # Phase 3: multi-word + digits (restricted to shortest words)
            multi_word_attack(words, hash_to_ids, found, total_hashes)

    # Merge found into cache (add any new ones)
    updated_cache = dict(cache)
    updated_cache.update(found)
    save_cache(CACHE_FILE, updated_cache)
    print(f"[*] Cache updated with {len(found) - len(cache)} new entries "
          f"(total cached: {len(updated_cache)}).")

    # Final summary
    print("\n=== Final Cracking summary ===")
    for uid, h in id_to_hash.items():
        if h in found:
            print(f"User {uid}: {found[h]}")
        else:
            print(f"User {uid}: <NOT CRACKED>")


if __name__ == "__main__":
    main()
