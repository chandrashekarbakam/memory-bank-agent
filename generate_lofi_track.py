import numpy as np
from scipy.io import wavfile

def generate_lofi_audio(duration_sec=16.0, sample_rate=44100):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    num_samples = len(t)
    
    # 84 BPM upbeat lo-fi groove
    bpm = 84
    beat_sec = 60.0 / bpm
    eighth_sec = beat_sec / 2.0
    
    # 1. Chords (Soft Rhodes E-Piano with 7th chords)
    # Chord progression: Fmaj7 (4s), Em7 (4s), Dm7 (4s), Cmaj7 (4s)
    chords = [
        [174.61, 220.00, 261.63, 329.63], # Fmaj7
        [164.81, 196.00, 246.94, 293.66], # Em7
        [146.83, 174.61, 220.00, 261.63], # Dm7
        [130.81, 164.81, 196.00, 246.94], # Cmaj7
    ]
    
    chord_synth = np.zeros(num_samples)
    chord_len_samples = int(sample_rate * 4.0)
    
    for i, chord in enumerate(chords):
        start_idx = i * chord_len_samples
        end_idx = min((i + 1) * chord_len_samples, num_samples)
        segment_t = np.linspace(0, (end_idx - start_idx)/sample_rate, end_idx - start_idx, endpoint=False)
        
        # Soft envelope for Rhodes piano feel
        env = np.exp(-segment_t * 0.4) * (1.0 - np.exp(-segment_t * 30.0))
        
        chord_wave = np.zeros_like(segment_t)
        for freq in chord:
            # Fundamental + 2nd harmonic (warmth) + slight vibrato
            vibrato = 1.0 + 0.003 * np.sin(2 * np.pi * 5.0 * segment_t)
            harm1 = np.sin(2 * np.pi * freq * vibrato * segment_t)
            harm2 = 0.25 * np.sin(2 * np.pi * freq * 2 * vibrato * segment_t)
            chord_wave += (harm1 + harm2)
            
        chord_synth[start_idx:end_idx] += chord_wave * env * 0.15

    # 2. Drums (Kick, Snare/Rimshot, Hi-hats)
    drum_synth = np.zeros(num_samples)
    
    # Total beats in duration
    total_beats = int(duration_sec / beat_sec)
    for b in range(total_beats):
        beat_start_time = b * beat_sec
        beat_start_idx = int(beat_start_time * sample_rate)
        
        # Kick drum on beat 0 and beat 2.5 of every 4-beat bar
        bar_beat = b % 4
        if bar_beat == 0 or bar_beat == 2:
            k_len = int(sample_rate * 0.25)
            if beat_start_idx + k_len < num_samples:
                kt = np.linspace(0, 0.25, k_len, endpoint=False)
                # Exponential pitch drop 130Hz -> 45Hz
                k_freq = 45.0 + 85.0 * np.exp(-kt * 25.0)
                k_phase = 2 * np.pi * np.cumsum(k_freq) / sample_rate
                k_wave = np.sin(k_phase) * np.exp(-kt * 10.0)
                drum_synth[beat_start_idx:beat_start_idx+k_len] += k_wave * 0.45
                
        # Snare / Rimshot on beat 1 and beat 3 of every 4-beat bar
        if bar_beat == 1 or bar_beat == 3:
            s_len = int(sample_rate * 0.2)
            if beat_start_idx + s_len < num_samples:
                st = np.linspace(0, 0.2, s_len, endpoint=False)
                # Tonal body + noise burst
                s_tone = np.sin(2 * np.pi * 180 * st) * np.exp(-st * 20.0)
                s_noise = np.random.uniform(-1, 1, s_len) * np.exp(-st * 25.0)
                s_wave = 0.4 * s_tone + 0.6 * s_noise
                drum_synth[beat_start_idx:beat_start_idx+s_len] += s_wave * 0.35

    # Hi-hats on every 8th note
    total_eighths = int(duration_sec / eighth_sec)
    for e in range(total_eighths):
        e_start_idx = int(e * eighth_sec * sample_rate)
        h_len = int(sample_rate * 0.05)
        if e_start_idx + h_len < num_samples:
            ht = np.linspace(0, 0.05, h_len, endpoint=False)
            h_noise = np.random.uniform(-1, 1, h_len) * np.exp(-ht * 80.0)
            drum_synth[e_start_idx:e_start_idx+h_len] += h_noise * 0.12

    # 3. Vinyl crackle / warmth texture
    vinyl_noise = np.random.normal(0, 0.008, num_samples)
    crackle_pops = (np.random.uniform(0, 1, num_samples) > 0.9995).astype(float) * np.random.uniform(0.02, 0.05, num_samples)
    vinyl = vinyl_noise + crackle_pops

    # Combine & master
    mix = chord_synth + drum_synth + vinyl
    # Normalize
    max_val = np.max(np.abs(mix))
    if max_val > 0:
        mix = mix / max_val * 0.85
        
    # Convert to 16-bit PCM WAV
    audio_int16 = (mix * 32767).astype(np.int16)
    # Create stereo by slight phase shift
    stereo = np.column_stack((audio_int16, np.roll(audio_int16, 10)))
    
    output_path = "/tmp/lofi_background.wav"
    wavfile.write(output_path, sample_rate, stereo)
    print(f"Generated lo-fi music track: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_lofi_audio()
