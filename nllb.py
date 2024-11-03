from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import numpy as np
import pykakasi
import csv
import random
import nagisa

# Initialize kakasi for converting Kanji to Hiragana.
kakasi = pykakasi.kakasi()

# Load tokenizer for English to Japanese translation.
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M", src_lang="eng_Latn")

# Load the pre-trained translation model.
#model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M").to("cpu")

# Load fine-tuned translation model.
model = AutoModelForSeq2SeqLM.from_pretrained("model/").to("cpu")

# Load the English transcription from file.
with open('lyrics/recording.txt', 'r') as f:
    src = f.readlines()

# Load the syllable count from file.
with open('files/syl_count.txt', 'r') as f:
    syl_count = int(f.read())

# Generate Japanese sequences with the model.
inputs = tokenizer(src, return_tensors="pt")
outputs = model.generate(
    **inputs,
    forced_bos_token_id=tokenizer.convert_tokens_to_ids("jpn_Jpan"),
    num_beams=45,                # Number of beams for beam search.
    num_return_sequences=45,     # Number of sequences to return.
    do_sample=True,
    top_p=0.90,
    top_k=200,
    penalty_alpha=0.6,
    early_stopping=True,
    return_dict_in_generate=True,  # Necessary for computing sequence scores.
    output_scores=True
)

# Compute transition scores for the generated sequences.
transition_scores = model.compute_transition_scores(
    outputs.sequences, 
    outputs.scores, 
    outputs.beam_indices, 
    normalize_logits=True
)

# Extract generated sequences, skipping the initial tokens.
input_length = 1 if model.config.is_encoder_decoder else inputs.input_ids.shape[1]
generated_sequences = outputs.sequences[:, input_length:]

# Decode sequences and skip special tokens.
decoded_sequences = tokenizer.batch_decode(
    generated_sequences, 
    skip_special_tokens=True
)

# Function that concatenates half-size characters with the preceding character, as they are used to alter pronunciations.
def concat(text):
    special_chars = {"っ", "ゃ", "ゅ", "ょ", "ー"}
    new_text = []
    for ch in text:
        if ch in special_chars and new_text:
            new_text[-1] += ch
        else:
            new_text.append(ch)
    return new_text

# Function that checks if the text contains any numerical digits.
# Sequences with digits are not considered valid because they can have too much impact on mora count.
def contains_digit(text):    
    return any(char.isdigit() for char in text)

# Function for removing unwanted characters from text.
def clean_text(text):
    unwanted_chars = {' ', '?', ',', '.', '」'}
    return ''.join(ch for ch in text if ch not in unwanted_chars)

# Function that computes the length of a word, excluding the half-size characters.
def compute_word_length(word):
    special_chars = {"っ", "ゃ", "ゅ", "ょ", "ー"}
    return sum(1 for char in word if char not in special_chars)

# Pad, start-of-sentence, end-of-sentence, and language tokens to exclude.
special_tokens = {0, 1, 2, 256079, 248059}
# Variable for keeping track of the best generated sequence.
saved_sequence = None

# Iterate over all sequences to find the best one.
# The best sequence is defined by having the mora count closest to the original English syllable count.
for i, score in enumerate(transition_scores):
    # Japanese text string of the sequence.
    jp_text = decoded_sequences[i]
    # List of token IDs in the sequence, excluding special tokens.
    tokens = [t for t in generated_sequences[i] if t not in special_tokens]
    # List of decoded tokens in the sequence.
    jp_list = [tokenizer.decode(t) for t in tokens]

    # Convert Japanese text exclusively to Hiragana.
    converted = kakasi.convert(jp_text)
    # Overall probability of the sequence, obtained by multiplying the probabilities of each token.
    prob = np.exp(score.numpy()).prod()
    # Make a list of all Hiragana characters in the sequence and concatenate the half-size characters with their relative previous character.
    hira_text = ''.join(item['hira'] for item in converted if item['hira'] not in {' ', '?', ',', '.'})
    hira_text = concat(hira_text)
    # Get the mora count for the sequence.
    hira_len = len(hira_text)

    # Check if sequence meets criteria:
    # - The Hiragana text length must be greater than or equal to the original syllable count.
    # - The text should not contain any digits.
    # - Prefer sequences with the smallest hira_len to match the syllable count as closely as possible.
    # Stores the sequence that best fits the criteria into saved_sequence.
    if hira_len >= syl_count and not contains_digit(''.join(hira_text)):
        if not saved_sequence or hira_len < saved_sequence['hira_len']:
            saved_sequence = {
                'prob': prob,
                'hira_text': hira_text,
                'hira_len': hira_len,
                'jp_text': jp_text,
                'jp_list': jp_list
            }

# Ensure a suitable sequence was found.
if not saved_sequence:
    raise ValueError("No suitable sequence found.")

# Clean the saved sequence by removing unwanted characters.
jp_text = clean_text(saved_sequence['jp_text'])

# Split sequence into words using nagisa for word segmentation.
# If a word is exclusively "は", use the pronunciation of "わ".
words = nagisa.tagging(jp_text)
word_list = []
for word in words.words:
    # Convert each word to Hiragana and concatenate all parts.
    hira_word = ''.join(item['hira'] for item in kakasi.convert(word) if item['hira'] not in {' ', '?', ',', '.'})
    hira_word = "わ" if hira_word == "は" else hira_word
    word_list.append(hira_word)

print("List of words: ", word_list)

# Compute word lengths excluding special characters.
word_len_list = [compute_word_length(word) for word in word_list]

print("saved_sequence:", saved_sequence['jp_text'])

# Measure the difference in saved_sequence mora count and original syllable count.
diff = saved_sequence['hira_len'] - syl_count
print("diff:", diff)

hira_text = saved_sequence['hira_text']

# If mora count is larger, concatenate random adjacent entries until the difference is zero.
# For future improvement, this concatenation could be based on note lengths.
while diff > 0:
    index = random.randint(0, len(hira_text) - 2)
    if len(hira_text[index]) < 2:
        hira_text[index] += hira_text.pop(index + 1)
        diff -= 1

print("Hira text: ", hira_text)

# Write the Hiragana characters to a CSV file.
with open('files/jp_lyrics.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(hira_text)

# Write the word lengths to a CSV file.
with open('files/jp_word_len_list.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(word_len_list)