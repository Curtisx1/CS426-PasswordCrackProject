import hashlib
import os
import random
from typing import List

PASSWORD_FILE = "passwords.txt"
DICTIONARY_FILE = "dictionary.txt"
CACHE_FILE = "cracked_cache.txt"
CANDIDATE_FILE = "candidates_massive.txt"

# ==========================
# MASSIVE GENERATION PARAMETERS
# ==========================


TARGET_CANDIDATES = 20000000000 

# Distribution of strategies
PURE_4_WORD_PERCENT = 0.70          
DIGIT_VARIATIONS_PERCENT = 0.15     
MIXED_LENGTH_PERCENT = 0.10         
EDGE_CASES_PERCENT = 0.05        

# Word selection
USE_ALL_WORDS = True             
ALSO_TRY_RARE_WORDS = True       

# ==========================
# UTILITIES
# ==========================

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

def format_size(bytes_size):
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def estimate_time(num_candidates, hash_rate=23500000):
    """Estimate hashcat time."""
    seconds = num_candidates / hash_rate
    hours = seconds / 3600
    days = hours / 24
    return days, hours, seconds

# ==========================
# MASSIVE GENERATOR
# ==========================

def generate_massive_candidates(words: List[str], output_file: str, target: int):
    """
    Generate MASSIVE candidate file with multiple strategies.
    This is designed to run for days on your GPU.
    """
    print("\n" + "=" * 70)
    print(" MASSIVE CANDIDATE GENERATION")
    print("=" * 70)
    
    print(f"\nTarget: {target:,} candidates")
    
    # Calculate distribution
    pure_4word = int(target * PURE_4_WORD_PERCENT)
    digit_vars = int(target * DIGIT_VARIATIONS_PERCENT)
    mixed_length = int(target * MIXED_LENGTH_PERCENT)
    edge_cases = int(target * EDGE_CASES_PERCENT)
    
    print(f"\nStrategy Distribution:")
    print(f"  Pure 4-word random:        {pure_4word:>12,} ({PURE_4_WORD_PERCENT*100:.0f}%)")
    print(f"  Digit variations:          {digit_vars:>12,} ({DIGIT_VARIATIONS_PERCENT*100:.0f}%)")
    print(f"  Mixed length patterns:     {mixed_length:>12,} ({MIXED_LENGTH_PERCENT*100:.0f}%)")
    print(f"  Edge cases (5-word, etc):  {edge_cases:>12,} ({EDGE_CASES_PERCENT*100:.0f}%)")
    
    # Estimate file size and time
    avg_length = 20  # Average password length
    file_size_bytes = target * (avg_length + 1)  # +1 for newline
    days, hours, seconds = estimate_time(target)
    
    print(f"\nEstimates:")
    print(f"  File size:        ~{format_size(file_size_bytes)}")
    print(f"  Generation time:  ~{target / 1000000:.0f} minutes")
    print(f"  Hashcat time:     ~{days:.1f} days ({hours:.1f} hours)")
    
    print(f"\nUsing {len(words)} dictionary words")
    
    # Prepare word lists by length
    very_short = [w for w in words if 2 <= len(w) <= 4]
    short = [w for w in words if 4 <= len(w) <= 6]
    medium = [w for w in words if 6 <= len(w) <= 8]
    long_words = [w for w in words if len(w) >= 8]
    
    print(f"\nWord length distribution:")
    print(f"  Very short (2-4 chars): {len(very_short)}")
    print(f"  Short (4-6 chars):      {len(short)}")
    print(f"  Medium (6-8 chars):     {len(medium)}")
    print(f"  Long (8+ chars):        {len(long_words)}")
    
    total_written = 0
    
    print(f"\nStarting generation to: {output_file}")
    print("This will take a while... Progress updates every 50M candidates\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        
        # STRATEGY 1: Pure 4-word random (70% of file)
        print("[1/4] Pure 4-word random combinations...")
        for i in range(pure_4word):
            combo = random.choices(words, k=4)
            f.write(''.join(combo) + '\n')
            total_written += 1
            
            if (i + 1) % 50000000 == 0:
                progress = (i + 1) / pure_4word * 100
                print(f"      {i+1:>12,} / {pure_4word:,} ({progress:.1f}%)")
        
        print(f"      Complete: {pure_4word:,} candidates")
        
        # STRATEGY 2: Digit variations (15% of file)
        print("\n[2/4] Digit variations (prefix, suffix, between words)...")
        for i in range(digit_vars):
            n_words = random.choice([3, 4])
            word_combo = random.choices(words, k=n_words)
            
            # Random digit (0-9999)
            digit = random.randint(0, 9999)
            
            # Random position
            strategy = random.randint(0, 4)
            
            if strategy == 0:
                # Digit prefix
                candidate = f"{digit}{''.join(word_combo)}"
            elif strategy == 1:
                # Digit suffix
                candidate = f"{''.join(word_combo)}{digit}"
            elif strategy == 2 and len(word_combo) >= 2:
                # Digit after first word
                candidate = f"{word_combo[0]}{digit}{''.join(word_combo[1:])}"
            elif strategy == 3 and len(word_combo) >= 3:
                # Digit after second word
                candidate = f"{word_combo[0]}{word_combo[1]}{digit}{''.join(word_combo[2:])}"
            else:
                # Multiple digits between words
                if len(word_combo) >= 2:
                    d1 = random.randint(0, 99)
                    candidate = f"{word_combo[0]}{d1}{''.join(word_combo[1:])}"
                else:
                    candidate = ''.join(word_combo) + str(digit)
            
            f.write(candidate + '\n')
            total_written += 1
            
            if (i + 1) % 50000000 == 0:
                progress = (i + 1) / digit_vars * 100
                print(f"      {i+1:>12,} / {digit_vars:,} ({progress:.1f}%)")
        
        print(f"      Complete: {digit_vars:,} candidates")
        
        # STRATEGY 3: Mixed length patterns (10% of file)
        print("\n[3/4] Mixed length patterns (short+medium+long combos)...")
        
        length_patterns = [
            [very_short, very_short, very_short, very_short],  # 4 very short
            [very_short, very_short, very_short, medium],       # 3 short, 1 medium
            [very_short, very_short, medium, medium],           # 2 short, 2 medium
            [short, short, medium, long_words],                 # varied
            [very_short, medium, medium, long_words],           # mixed
            [long_words, long_words, short, short],             # 2 long, 2 short
            [very_short, very_short, long_words, long_words],   # extremes
            [medium, medium, medium, medium],                   # all medium
        ]
        
        # Filter patterns where all lists have words
        valid_patterns = [p for p in length_patterns if all(len(wlist) > 0 for wlist in p)]
        
        for i in range(mixed_length):
            pattern = random.choice(valid_patterns)
            combo = [random.choice(wlist) for wlist in pattern]
            f.write(''.join(combo) + '\n')
            total_written += 1
            
            if (i + 1) % 50000000 == 0:
                progress = (i + 1) / mixed_length * 100
                print(f"      {i+1:>12,} / {mixed_length:,} ({progress:.1f}%)")
        
        print(f"      Complete: {mixed_length:,} candidates")
        
        # STRATEGY 4: Edge cases (5% of file)
        print("\n[4/4] Edge cases (5-word, all same length, etc)...")
        
        for i in range(edge_cases):
            edge_strategy = random.randint(0, 5)
            
            if edge_strategy == 0:
                # 5 very short words
                if very_short:
                    combo = random.choices(very_short, k=5)
                    f.write(''.join(combo) + '\n')
            elif edge_strategy == 1:
                # 4 words all same length
                target_len = random.choice([3, 4, 5, 6])
                same_len = [w for w in words if len(w) == target_len]
                if len(same_len) >= 4:
                    combo = random.choices(same_len, k=4)
                    f.write(''.join(combo) + '\n')
            elif edge_strategy == 2:
                # 2 very long words
                if len(long_words) >= 2:
                    combo = random.choices(long_words, k=2)
                    f.write(''.join(combo) + '\n')
            elif edge_strategy == 3:
                # 3 words + double digit between each
                combo = random.choices(words, k=3)
                d1 = random.randint(10, 99)
                d2 = random.randint(10, 99)
                f.write(f"{combo[0]}{d1}{combo[1]}{d2}{combo[2]}\n")
            elif edge_strategy == 4:
                # 4 words with no repeats (all different)
                if len(words) >= 4:
                    combo = random.sample(words, k=4)
                    f.write(''.join(combo) + '\n')
            else:
                # 6 very short words
                if very_short:
                    combo = random.choices(very_short, k=6)
                    f.write(''.join(combo) + '\n')
            
            total_written += 1
            
            if (i + 1) % 50000000 == 0:
                progress = (i + 1) / edge_cases * 100
                print(f"      {i+1:>12,} / {edge_cases:,} ({progress:.1f}%)")
        
        print(f"      Complete: {edge_cases:,} candidates")
    
    # Final stats
    actual_size = os.path.getsize(output_file)
    print(f"\n{'='*70}")
    print(" GENERATION COMPLETE")
    print('='*70)
    print(f"Total candidates:  {total_written:,}")
    print(f"File size:         {format_size(actual_size)}")
    print(f"File:              {output_file}")
    
    days, hours, seconds = estimate_time(total_written)
    print(f"\nHashcat estimates (GTX 1080 @ 23.5 GH/s):")
    print(f"  Time:              ~{days:.1f} days ({hours:.1f} hours)")
    print(f"  Speed:             ~23.5 million H/s")

def main():
    print("=" * 70)
    print(" MASSIVE CANDIDATE GENERATOR FOR MULTI-DAY GPU CRACKING")
    print("=" * 70)
    
    # Load dictionary
    print("\n[*] Loading dictionary...")
    words = load_dictionary(DICTIONARY_FILE)
    print(f"[*] Loaded {len(words)} words")
    
    print("\n" + "=" * 70)
    print(" CONFIGURATION")
    print("=" * 70)
    
    print(f"\nCurrent settings:")
    print(f"  Target candidates: {TARGET_CANDIDATES:,}")
    
    days, hours, _ = estimate_time(TARGET_CANDIDATES)
    print(f"  Estimated time:    ~{days:.1f} days ({hours:.1f} hours)")
    
    print(f"\nYou can edit TARGET_CANDIDATES in the script to adjust:")
    print(f"  -  1,000,000,000 (1B)  = ~12 hours")
    print(f"  -  2,000,000,000 (2B)  = ~24 hours")
    print(f"  -  5,000,000,000 (5B)  = ~2.5 days")
    print(f"  - 10,000,000,000 (10B) = ~5 days")
    
    print("\n" + "=" * 70)
    response = input("\nGenerate candidates with current settings? (yes/no) [yes]: ").strip().lower()
    
    if response in ['', 'yes', 'y']:
        print("\n[*] Starting generation...")
        print("[!] This will take 30-60 minutes depending on your system")
        print("[!] You can stop with Ctrl+C and resume later\n")
        
        try:
            generate_massive_candidates(words, CANDIDATE_FILE, TARGET_CANDIDATES)
            
            print("\n" + "=" * 70)
            print(" NEXT STEPS")
            print("=" * 70)
            print("\n1. Run hashcat (this will take 1-2+ days):")
            print(f"   hashcat -m 100 -a 0 -o hashcat_cracked.txt --potfile-disable -w 3 hashes.txt {CANDIDATE_FILE}")
            
            print("\n2. Monitor progress:")
            print("   Hashcat shows real-time progress")
            print("   Press 's' for status while running")
            
            print("\n3. Check for cracks periodically:")
            print("   type hashcat_cracked.txt")
            
            print("\n4. Let it run to completion")
            print("   Your GTX 1080 will process ~23M hashes/second")
            print("   Temperature should stay under 80-85°C")
            
            print("\n5. If still not all cracked after this:")
            print("   - Increase TARGET_CANDIDATES to 5-10 billion")
            print("   - Try hashcat rule-based attacks")
            print("   - Consider the passwords may use non-dictionary words")
            
        except KeyboardInterrupt:
            print("\n\n[!] Generation interrupted!")
            print("[!] Partial file may be usable")
        except Exception as e:
            print(f"\n[!] Error: {e}")
    else:
        print("\nAborted. Edit TARGET_CANDIDATES in the script and run again.")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()