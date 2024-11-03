-- Meta data.
function getClientInfo()
  return {
    name = "JapaneseNotes",
    category = "PolySinger",
    author = "Silas Antonisen",
    versionNumber = 0,
    minEditorVersion = 0
  }
end

-- Function for reading all lines from a text file and return a table (list) of strings.
function lines_from(file)
  local fh = io.open(file, "r")
  if not fh then
    SV:showMessageBox("Error", "Cannot open file: " .. file)
    SV:finish()
    return {}
  end

  local lines = {}
  for line in fh:lines() do
    lines[#lines + 1] = line
  end
  fh:close()
  return lines
end

-- Function specifically for parsing the phoneme alignment file, splitting it into phonemes and timings.
function parse_phoneme_file(phoneme_file)
  local text, timings = {}, {}
  for _, line in ipairs(lines_from(phoneme_file)) do
    local index = 0
    -- split lines at whitespace.
    for y in string.gmatch(line, "%S+") do
      index = index + 1
      if index == 1 then
        table.insert(text, y)
      elseif index == 2 then
        table.insert(timings, tonumber(y))
      end
    end
  end
  return text, timings
end

-- Function for grouping phonemes into words. Calculate the onset and duration of each word.
function group_phonemes_into_words(text, timings)
  -- Tables for storing each phoneme, onset and duration belonging to a word.
  local phones, onsets, durs = {}, {}, {}
  -- Tables for storing the words with all their data.
  local words, words_onsets, words_durs = {}, {}, {}
  local count = 0

  for t, phoneme in ipairs(text) do
    -- Start a word when ">" in encountered.
    if phoneme == ">" then
      count = count + 1

    -- If a word is started, save phoneme, onset and duration.
    elseif count == 1 then
      table.insert(phones, phoneme)
      table.insert(onsets, timings[t])
      table.insert(durs, timings[t + 1] and (timings[t + 1] - timings[t]) or 0)
    end

    -- When second ">" is encountered, store all data belonging to the word, and start a new word.
    if count == 2 then
      table.insert(words, phones)
      table.insert(words_onsets, onsets)
      table.insert(words_durs, durs)
      phones, onsets, durs = {}, {}, {}
      count = 1
    end
  end

  return words, words_onsets, words_durs
end

-- Function for parsing syllable file.
function parse_syllables_file(syllables_file)
  -- Table containing tables theat each contain a word, its syllables, and phonemes belonging to the syllables.
  local syllables = {}
  for _, line in ipairs(lines_from(syllables_file)) do
    -- Table for containing syllables belonging to that word.
    local word_syllables, index = {}, 0
    -- Split lines at commas. These are the individual syllables.
    for token in string.gmatch(line, '([^,]+)') do
      index = index + 1
      -- Index 1 is the word.
      if index == 1 then
        table.insert(word_syllables, {token})
      -- Following indices are the syllables in the word.
      else
        -- Table for storing each phoneme in a syllable
        local syllable = {}
        -- Phonemes in the syllables are sepparated by whitespace.
        for x in string.gmatch(token, "%S+") do
          table.insert(syllable, x)
        end
        table.insert(word_syllables, syllable)
      end
    end
    table.insert(syllables, word_syllables)
  end
  return syllables
end

-- Function for aligning the onsets and durations with syllables.
function match_syllables_with_phonemes(syllables, words, words_onsets, words_durs)
  -- loop over the content of syllables table, which contains words with their respecitve syllables and associated phonemes.
  for line, syllable_data in ipairs(syllables) do
    -- define the phonemes with their onsets and durations, belonging to the current word.
    local word_phones, word_onsets, word_durations = words[line], words_onsets[line], words_durs[line]
    local phone_index = 1

      -- Loop through all syllables in the given word. The loop starts at two, because entry 1 is the word itself.
    for syllable = 2, #syllable_data do
      -- define the phonemes in the current syllable. Onset and duration of the syllable is initally set to nil/0.
      local syllable_phones, onset, duration = syllable_data[syllable], nil, 0
      -- Loop through phonemes in the syllable.
      for phoneme in ipairs(syllable_phones) do
        -- Check if current phoneme in the word belongs to the current syllable.
        if word_phones[phone_index] == syllable_phones[phoneme] then
          -- If so, syllable onset is set by the first phoneme, and following phonemes add to the syllable durration.
          onset = onset or word_onsets[phone_index]
          duration = duration + word_durations[phone_index]
          -- Move to next phoneme in the word.
          phone_index = phone_index + 1
        else
          SV:showMessageBox("Error", "Phoneme mismatch in line " .. line)
          SV:finish()
          return
        end
      end
      table.insert(syllable_data[syllable], onset)
      table.insert(syllable_data[syllable], duration)
    end
  end
  -- Return modified syllables table.
  return syllables
end

-- Function for adjusting duration of syllables. This is to fill out small gaps between syllables and ensure a better flow in synthesis.
function adjust_syllable_durations(syllables)
  -- Loop over modified syllables table. It contains words and their syllables. The syllables each have a set of phonemes, an onset and a durration.
  for _, syllable_data in ipairs(syllables) do
    -- at each table, start at index 2, because index 1 is the word itself.
    for e = 2, #syllable_data do
      -- If there are more than two syllables, add a "+" to the table. In Synthesizer V the "+" is used for splitting syllables over notes.
      if e > 2 then
        table.insert(syllable_data[1], "+")
      end
      -- Check if there is another syllables after the current syllable in the word of interest.
      if syllable_data[e + 1] then
        local current_syllable = syllable_data[e]
        local next_syllable = syllable_data[e + 1]
        -- If so, Adjusts the duration of the current syllable to be the difference between the onset time of the next syllable and the onset time of the current syllable.
        current_syllable[#current_syllable] = next_syllable[#next_syllable - 1] - current_syllable[#current_syllable - 1]
      end
    end
  end
end

-- Function for parsing csv files.
function parse_csv(file)
  local data = {}
  for _, line in ipairs(lines_from(file)) do
    -- Seperate by commas.
    for value in string.gmatch(line, '([^,]+)') do
      table.insert(data, value)
    end
  end
  return data
end

-- Function for parsing the generated pitch file.
function parse_pitch_file(pitch_csv)
  -- Table for storing the pairs of time and f0.
  local pitch = {}
  -- Loop through lines in the pitch.csv file.
  for _, line in ipairs(lines_from(pitch_csv)) do
    local time, f0 = nil, nil
    local index = 0
    -- Split by commas.
    for value in string.gmatch(line, '([^,]+)') do
      index = index + 1
      -- Index 1 is time.
      if index == 1 then
        time = tonumber(value)
      -- Index 4 is f0
      elseif index == 4 then
        f0 = tonumber(value)
      end
    end
    if time and f0 then
      -- Add time as key and f0 as value.
      pitch[time] = f0
    end
  end
  return pitch
end

-- Function for creating a note group in Synthesizer V.
function next(groupName)
  if groupName == "" then
    SV:finish()
    return
  end

  local project = SV:getProject()
  local newGroup, newGroupReference = SV:create("NoteGroup"), SV:create("NoteGroupReference")
  newGroup:setName(groupName)
  project:addNoteGroup(newGroup, 1)
  newGroupReference:setTarget(newGroup)
  project:getTrack(1):addGroupReference(newGroupReference)

  -- Read phonemes and their alignments.
  local text, timings = parse_phoneme_file("PolySinger/lyrics-aligner/outputs/cmu/phoneme_onsets/recording.txt")
  -- Group phonemes into words.
  local words, words_onsets, words_durs = group_phonemes_into_words(text, timings)
  -- Read the syllables for all words.
  local syllables = parse_syllables_file("PolySinger/files/syllables.csv")
  -- Align syllables with the phonemes to obtain syllable level onset and duration alignments
  syllables = match_syllables_with_phonemes(syllables, words, words_onsets, words_durs)
  -- Adjust durations of syllables for to fill out gaps and ensure better flow.
  adjust_syllable_durations(syllables)

  -- Start creating notes using the syllables table.
  onNextFrame(syllables)
end

-- Function for filling notes into the note group.
function onNextFrame(syllables)
  local project, newGroup = SV:getProject(), SV:getProject():getNoteGroup(1)
  local timeAxis, AutomatePitch = project:getTimeAxis(), newGroup:getParameter("PitchDelta")

  -- Read the Japanese lyrics.
  local jp_lyrics = parse_csv("PolySinger/files/jp_lyrics.csv")
  -- Counter for keeping track mora index.
  local lyric_count = 0

  -- -- Loop over syllables table. It contains words and their syllables. The syllables each have a set of phonemes, an onset and a durration.
  for _, syllable_data in ipairs(syllables) do
    -- Loop through each syllable in the word. Start at Index 2 because index 1 is the word itself.
    for s = 2, #syllable_data do
      lyric_count = lyric_count + 1
      -- Extract onset and duration of syllable.
      local onset_sec, duration_sec = syllable_data[s][#syllable_data[s] - 1], syllable_data[s][#syllable_data[s]]
      -- Create a note.
      local note = SV:create("Note")
      -- Add onset and duration to the note
      note:setTimeRange(timeAxis:getBlickFromSeconds(onset_sec), timeAxis:getBlickFromSeconds(duration_sec))
      -- Set a standard pitch at 60 (C4).
      note:setPitch(60)
      -- Disable automatic pitch adjustment.
      note:setPitchAutoMode(0)
      -- Set note lyrics to be the current mora.
      note:setLyrics(jp_lyrics[lyric_count])
      -- Add note to note group.
      newGroup:addNote(note)

      -- If the previous note's end time doesn't align with the current note's onset, and the gap is less than 0.2 seconds, the previous note's duration is adjusted to fill the gap.
      if newGroup:getNumNotes() > 1 then
        local index, prevNote = note:getIndexInParent(), newGroup:getNote(note:getIndexInParent() - 1)
        if prevNote:getEnd() ~= note:getOnset() and note:getOnset() - prevNote:getEnd() < timeAxis:getBlickFromSeconds(0.2) then
          prevNote:setDuration(note:getOnset() - prevNote:getOnset())
        end
      end
    end
  end

  -- Automate the pitch of notes over time as a deviation from 60.
  for time, f0 in pairs(parse_pitch_file("PolySinger/files/recording_f0.csv")) do
    local blick = timeAxis:getBlickFromSeconds(time)
    -- the deviation is multiplied by 100 for normalization. 1200 cents is added to shift up an octave, but this might not be neccesarry in your case.
    local value = ((f0 - 60) * 100) + 1200
    AutomatePitch:add(blick, value)
  end

  SV:showMessageBoxAsync("Note Group Created!", "Done!", function() SV:finish() end)
end

-- Main function that initializes a note group.
function main()
  SV:showInputBoxAsync("Create Group", "Please tell me the group name", "Insert Here", next)
end