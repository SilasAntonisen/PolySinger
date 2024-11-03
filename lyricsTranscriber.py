import subprocess
import csv
import wave
import pyaudio
from pathlib import Path
from transformers import pipeline
import nltk
from nltk.corpus import cmudict
import string

# Download CMU dictionary if not already downloaded.
nltk.download('cmudict', quiet=True)

# Function for recording a vocal performance.
def record_audio(output_path):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    frames = []
    print("Recording... Press Ctrl+C to stop.")
    try:
        while True:
            frames.append(stream.read(1024))
    except KeyboardInterrupt:
        print("Recording stopped.")
    stream.stop_stream()
    stream.close()
    audio.terminate()
    with wave.open(str(output_path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        f.setframerate(16000)
        f.writeframes(b''.join(frames))

# Fucntion for transcribing the lyrics from recorded audio using Whisper. "return_timestamps" must be set True for long form transcription (>30s).
def transcribe_audio(audio_path, transcript_path, model_name="openai/whisper-large-v3"):
    asr_pipeline = pipeline("automatic-speech-recognition", model=model_name, device="cpu", return_timestamps=True)
    transcription = asr_pipeline(str(audio_path), generate_kwargs={"language": "english"})
    with open(str(transcript_path), 'w') as f:
        f.write(transcription["text"])

# Function for categorizing phonemes from a word into syllables.
# Input is a list of phonemes representing the pronunciation of the word (e.g., ['N', 'EH1', 'V', 'ER0'] for "never"). 
# The numbers indicate a vowel and its type of stress.
# Output is a list of syllables containing their respecitve phonemes (e.g., [['N', 'EH'], ['V', 'ER']]).
# Specific rules are set up to concatenate consonants with their best vowel match for natural pronunciation.
def split_syllables(pronunciation):
    syllables = [[]]
    i = 0

    # boolean flag to determine if a vowel has been encountered.
    vowel = False
    length = len(pronunciation)

    # Go through each phoneme of the word.
    while i < length:
        phoneme = pronunciation[i]

        # Append current phoneme to last sublist in syllables list without including the digit in case it is a vowel.
        syllables[-1].append(phoneme[:-1] if phoneme[-1].isdigit() else phoneme)

        # is_vowel becomes true if phoneme contains a digit. Then, update the vowel flag to True if vowel is found.
        is_vowel = phoneme[-1].isdigit()
        vowel |= is_vowel

        # Look into the next two phonemes in the word to determine if they are vowels and determine syllable boundaries.
        lookahead = pronunciation[i+1:i+3]
        next_is_vowel = lookahead[0][-1].isdigit() if len(lookahead) > 0 else False
        next_next_is_vowel = lookahead[1][-1].isdigit() if len(lookahead) > 1 else False

        # If current phoneme is a vowel and if either the first or the second of the following phonemes is a vowel, 
        # start a new syllable sublist. vowel flag is reset to False.
        if is_vowel:
            if (not next_is_vowel and next_next_is_vowel) or next_is_vowel:
                syllables.append([])
                vowel = False

        # If current phoneme is not a vowel, but the vowel flag is True and the first following phoneme is not a vowel, 
        # but the second following phoneme is a vowel, start a new syllable sublist. Vowel flag is reset to False.
        else:
            if vowel and (not next_is_vowel and next_next_is_vowel):
                syllables.append([])
                vowel = False
        i += 1

    # Post processing of syllables in case they start with phoneme Y.
    # If a syllable starts with Y and the previous syllable has more than two phonemes,
    # but the last of those phonemes is not a vowel, then move that last phoneme into the current syllable as first syllable.
    for idx in range(1, len(syllables)):
        if syllables[idx][0] == 'Y' and len(syllables[idx-1]) > 2 and not syllables[idx-1][-1][-1].isdigit():
            syllables[idx].insert(0, syllables[idx-1].pop())
    return syllables

# Fucntion for processing the transcript. The purpose is to split words into syllables, count them and save them.
def process_transcript(transcript_path, syllables_csv_path, syllable_count_path):
    cmu_dict = cmudict.dict()
    total_syllables = 0
    syllable_data = []
    with open(str(transcript_path), 'r') as f:
        text = f.read()

    # Remove all punctuations except for apostrophes, and split the transcript string into separate words.
    punctuation_to_remove = ''.join(c for c in string.punctuation if c not in ("'",))
    translator = str.maketrans(punctuation_to_remove, ' ' * len(punctuation_to_remove))
    words = text.lower().translate(translator).split()

    # Itterate through all words.
    for word in words:
        # Get the pronunciation of the word.
        pronunciations = cmu_dict.get(word)
        if not pronunciations:
            continue

        # cmu_dict returns a list of pronunciations. In this implemetation, we always use the first pronunciation in the list.
        pronunciation = pronunciations[0]

        # Call the "split_syllables" function in order define the syllables of the word using the phonetic pronunciation.
        syllables = split_syllables(pronunciation)

        # Count total amount of syllables in transcript. This number will be saved as syl_count.txt
        total_syllables += len(syllables)
        
        # Create list of syllables in word and append to syllable_data list. This nested list will be saved as syllables.csv file.
        syllable_strings = [' '.join(syl) for syl in syllables]
        syllable_data.append([word] + syllable_strings)
    with open(str(syllables_csv_path), 'w', newline='') as csvfile:
        csv.writer(csvfile).writerows(syllable_data)
    with open(str(syllable_count_path), 'w') as f:
        f.write(str(total_syllables))

# Create directory for saving files
files_dir = Path('./files')
files_dir.mkdir(exist_ok=True)
audio_dir = Path('./audio')
audio_dir.mkdir(exist_ok=True)
lyrics_dir = Path('./lyrics')
lyrics_dir.mkdir(exist_ok=True)

# Paths for saving files
record_save_path = audio_dir / "recording.wav"
transcript_save_path = lyrics_dir / "recording.txt"
syllables_csv_path = files_dir / "syllables.csv"
syllable_count_path = files_dir / "syl_count.txt"

# Perform recording and transcription
record_audio(record_save_path)
transcribe_audio(record_save_path, transcript_save_path)

# Delete previous phoneme alignment file if it exists
align_path = Path("./lyrics-aligner/outputs/cmu/phoneme_onsets/recording.txt")
if align_path.exists():
    align_path.unlink()

# Perform phoneme-level lyrics alignment. It might be neccesarry to play around with vad-threshold to get accurate alignments.
subprocess.run([
    'python', 'align.py', '../audio/', '../lyrics/',
    '--lyrics-format', 'w', '--onsets', 'p', '--dataset-name', 'cmu', '--vad-threshold', '0.2'
], cwd='lyrics-aligner/')

# Perform frame-level vocal-contour extraction. Beware, when using the baseline model, the tail of the audio will occacionaly not be transcribed.
subprocess.run(['omnizart', 'vocal-contour', 'transcribe', 'audio/recording.wav', '--output', 'files/'])

# Process the transcript to count syllables
print("Generating syllables...")
process_transcript(transcript_save_path, syllables_csv_path, syllable_count_path)