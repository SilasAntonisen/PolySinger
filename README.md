# PolySinger: Singing-Voice to Singing-Voice Translation from English to Japanese
[![arXiv](https://img.shields.io/badge/arXiv-2407.14399-b31b1b.svg)](https://arxiv.org/abs/2407.14399)
[![Project Page](https://img.shields.io/badge/Project%20Page-Access%20Here-green.svg)](https://antonisen.dev/polysinger/)
[![Synthesizer V Studio Pro](https://img.shields.io/badge/Synthesizer%20V%20Studio%20Pro-Required-red.svg)](https://dreamtonics.com/synthesizerv/)
![Platform](https://img.shields.io/badge/Platform-Ubuntu-orange.svg)
![Python Version](https://img.shields.io/badge/python-3.8-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GitHub Issues](https://img.shields.io/github/issues/SilasAntonisen/PolySinger)

This is the implementation for the paper ["PolySinger: Singing-Voice to Singing-Voice Translation from English to Japanese"](https://arxiv.org/abs/2407.14399) by Silas Antonisen and Iván López-Espejo. The concept is similar to speech-to-speech translation, but for singing! In short, the idea is to sing a song, translate the lyrics, and resynthesize the song with a synthetic voice in the translated language using your original melody. The project page with audio examples can be found [here](https://antonisen.dev/polysinger/).

## Prerequisites
Currently, this implementation requires a license for [Synthesizer V Studio Pro](https://dreamtonics.com/synthesizerv/).

**Note**: *For easier accessibility and no requirement for monetary investment, we plan to create solutions using open-source singing voice synthesis software as well. An implementation for [ENUNU](https://github.com/oatsu-gh/ENUNU) is currently in development.*

This implementation has exclusively been tested on **Ubuntu 22.04.4 LTS** using a **conda based Python 3.8 environment** and **Synthesizer V Studio Pro Ubuntu Version 1.10.0b1**.

## Installation
The specific versions used in testing are indicated for all packages to ensure reproducibility.
1. **Install Synthesizer V Studio Pro 1.10.0b1**

2. **Clone this repository into the Synthesizer V folder** 
    ```
    cd svstudio-pro-linux64/Synthesizer-V-Studio-Pro/

    git clone https://github.com/SilasAntonisen/PolySinger.git
    
    cd PolySinger/
    ```
3. **Move the lua script into the Synthesizer V scripts folder** 
    ```
    mv JapaneseNotes.lua ../scripts/
    ```
4. **Create a conda environment**
    ```
    conda create -n PolySinger python=3.8
    ```
5. **Activate the environment**
    ```
    conda activate PolySinger
    ```
6. **Install PyTorch and Transformers**
    ```
    conda install pytorch==1.13.1 torchaudio==0.13.1 pytorch-cuda=11.7 -c pytorch -c nvidia
    
    pip install transformers==4.45.1
    ```
7. **Install dependencies for recording audio**
    ```
    pip install pyaudio==0.2.14
    ```
8. **Clone schufo-lyrics-aligner into this repository**
    ```
    git clone https://github.com/schufo/lyrics-aligner.git
    ```
    
9. **Copy CMU word2phoneme file into lyrics-aligner/files/ folder**
    ```
    wget -P lyrics-aligner/files/ https://github.com/hataori-p/lyrics-alignment/raw/main/lyrics-aligner/cmu_word2phonemes.pickle
    ```
    
10. **Install the requirements for lyrics-aligner**
    ```
    pip install pyqt5==5.15.11
    
    pip install ffmpeg==1.4
    
    pip install pysoundfile==0.9.0.post1
    
    pip install argparse==1.4.0
    ```
11. **Install Omnizart and its checkpoints**
    ```
    sudo apt-get install libsndfile1-dev=1.0.31-2ubuntu0.1 fluidsynth=2.2.5-1 ffmpeg=7:4.4.2-0ubuntu0.22.04.1
    
    pip install Cython==3.0.11
    
    pip install omnizart==0.5.0
    
    omnizart download-checkpoints
    ```

12. **Install dependencies for syllable concatenation**
    ```
    pip install nltk==3.9.1
    ```
13. **Install dependencies for Japanese pronunciation and word segmentation**
    ```
    pip install pykakasi==2.3.0
    
    pip install nagisa==0.2.11
    ```
14. **Retrieve the fine-tuned model**

    Manually copy the [model](https://drive.google.com/drive/folders/1pwR2pVY1YlK1ncBn5ZYUEo5aD1dCkCrP?usp=sharing) folder into this repository. This is our fine-tuned NLLB (No Language Left Behind) model

    **or**
    ```
    pip install gdown

    gdown --folder https://drive.google.com/drive/folders/1OxgFNw4taIShd1sfuVyRSOYNesW9iRdY
    ```

## Usage
Now the environment is set up. To run this implementation, follow these steps:

1. **Run** `lyricsTranscriber.py` **from within this repository** to record a vocal performance, transcribe the lyrics, align the phonetics, transcribe the vocal-contour, and define the syllables sung
    ```
    python lyricsTranscriber.py
    ```
    **Note**: *Remember to choose your preferred microphone inside your system settings.*

    **Note**: *When using the baseline vocal-contour model in Omnizart, the tail of the audio will occasionally not be transcribed. This can be mitigated by extending the tail with a hum or similar sound that will not be transcribed as lyrics.*

3. **Run** `nllb.py` **from within this repository** to translate the lyrics to Japanese and define the pronunciation of the Japanese lyrics
    ```
    python nllb.py
    ```
    **Note**: *You can choose whether you want to use the baseline or fine-tuned model in the script. Depending on your pc memory and audio length, you might need to change the num_beams parameter as well.*

4. **Run** `JapaneseNotes.lua` **in Synthesizer V Studio Pro** to create notes and automation
    - Launch Synthesizer V Studio Pro.
    - Click the **Scripts** dropdown menu and select `PolySinger -> JapaneseNotes` to generate the notes.
    - Select a synthetic voice for the current track in the voice menu (Mai is included when purchasing a Synthesizer V Studio Pro license but must be installed separately) and press play!

## Citation
If you use any of our code or the fine-tuned model, please cite our paper:
```bibtex
@INPROCEEDINGS{PolySinger,
    AUTHOR = {Silas Antonisen and Iván López-Espejo},
    TITLE = {{PolySinger: Singing-Voice to Singing-Voice Translation from English to Japanese}},
    BOOKTITLE = {Proceedings of the 25th International Society for Music Information Retrieval (ISMIR) Conference},
    YEAR = {2024},
    ADDRESS = {San Francisco, CA, USA}
    }
```
