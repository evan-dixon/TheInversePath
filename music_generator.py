import pygame
import random
import time
import math
import numpy as np
from threading import Thread, Event, Lock

def _is_mixer_available():
    """Check if the mixer is available and initialized"""
    try:
        return pygame.mixer.get_init() is not None
    except:
        return False

class MusicGenerator:
    def __init__(self):
        pygame.mixer.init(frequency=44100, channels=2)
        pygame.mixer.set_num_channels(32)  # Increased number of channels
        
        # Define genres and their characteristics
        self.genres = {
            'electronic': {
                'tempo_range': (120, 128), 
                'drum_styles': ['house', 'tech_house'],
                'structures': [
                    ['intro', 'verse', 'buildup', 'drop', 'breakdown', 'drop', 'outro'],
                    ['intro', 'verse', 'drop', 'verse', 'drop', 'breakdown', 'drop', 'outro']
                ],
                'note_weights': [
                    (1.0, 0.6),    # quarter notes
                    (2.0, 0.3),    # half notes
                    (4.0, 0.1)     # whole notes
                ],
                'step_preference': 0.9,
                'drum_volume': 1.0,
                'melody_volume': 0.6,
                'max_interval': 2,
                'repetition_chance': 0.4,
                'rest_chance': 0.2
            },
            'chill': {
                'tempo_range': (85, 100),
                'drum_styles': ['basic', 'jazz', 'shuffle'],
                'structures': [
                    ['intro', 'verse', 'chorus', 'verse', 'chorus', 'bridge', 'chorus', 'outro'],
                    ['intro', 'verse', 'verse', 'chorus', 'bridge', 'chorus', 'outro']
                ],
                'note_weights': [
                    (1.0, 0.7),   # quarter notes
                    (2.0, 0.2),   # half notes
                    (4.0, 0.1)    # whole notes
                ],
                'step_preference': 0.9,
                'repetition_chance': 0.3,
                'rest_chance': 0.25
            },
            'funk': {
                'tempo_range': (100, 120),
                'drum_styles': ['funk', 'latin'],
                'structures': [
                    ['intro', 'groove', 'verse', 'groove', 'bridge', 'groove', 'outro'],
                    ['intro', 'groove', 'verse', 'bridge', 'groove', 'verse', 'groove', 'outro']
                ],
                'note_weights': [
                    (0.5, 0.3),   # 8th notes
                    (1.0, 0.6),   # quarter notes
                    (2.0, 0.1)    # half notes
                ],
                'step_preference': 0.8,
                'repetition_chance': 0.35,
                'rest_chance': 0.15
            },
            'ambient': {
                'tempo_range': (70, 90),
                'drum_styles': ['ambient_minimal'],
                'structures': [
                    ['intro', 'flow', 'build', 'flow', 'peak', 'flow', 'outro'],
                    ['intro', 'flow', 'flow', 'build', 'peak', 'flow', 'outro']
                ],
                'note_weights': [
                    (2.0, 0.6),   # half notes
                    (4.0, 0.4)    # whole notes
                ],
                'step_preference': 0.95,
                'drum_volume': 0.2,
                'melody_volume': 0.6,
                'max_interval': 2,
                'repetition_chance': 0.4,
                'rest_chance': 0.3
            }
        }

        # Add harmony rhythm patterns
        self.harmony_patterns = {
            'electronic': [
                [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],  # Four-on-the-floor
                [1,0,0,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],  # Syncopated
                [1,0,1,0, 0,0,1,0, 0,1,0,0, 1,0,0,0]   # Complex
            ],
            'chill': [
                [1,0,0,0, 0,0,1,0, 0,0,0,0, 1,0,0,0],  # Sparse
                [1,0,0,1, 0,0,1,0, 0,1,0,0, 1,0,0,0],  # Jazzy
                [1,0,0,0, 1,0,0,0, 0,0,1,0, 0,0,1,0]   # Flowing
            ],
            'funk': [
                [1,0,1,0, 0,1,0,1, 0,1,0,1, 0,1,0,0],  # Syncopated funk
                [1,0,0,1, 0,1,0,0, 1,0,0,1, 0,1,0,0],  # Groove
                [1,1,0,1, 0,1,1,0, 1,0,1,0, 1,1,0,0]   # Complex funk
            ],
            'ambient': [
                [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],  # Very sparse
                [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],  # Minimal
                [1,0,0,0, 0,0,1,0, 0,0,0,0, 0,0,1,0]   # Floating
            ]
        }

        # Define musical notes (frequencies in Hz)
        self.notes = {
            'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00, 'A3': 220.00, 'B3': 246.94,
            'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
            'C5': 523.25, 'D5': 587.33, 'E5': 659.26, 'F5': 698.46, 'G5': 783.99, 'A5': 880.00, 'B5': 987.77
        }
        
        # Define scale degrees and their roles in chords
        self.scale_degrees = {
            1: ['C4', 'E4', 'G4'],  # I   chord (C major)
            2: ['D4', 'F4', 'A4'],  # ii  chord (D minor)
            3: ['E4', 'G4', 'B4'],  # iii chord (E minor)
            4: ['F4', 'A4', 'C5'],  # IV  chord (F major)
            5: ['G4', 'B4', 'D5'],  # V   chord (G major)
            6: ['A4', 'C5', 'E5'],  # vi  chord (A minor)
            7: ['B4', 'D5', 'F5'],  # vii chord (B diminished)
        }
        
        # Different scales we can use
        self.scales = {
            'major': ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'],
            'minor': ['C4', 'D4', 'Eb4', 'F4', 'G4', 'Ab4', 'B4', 'C5'],
            'pentatonic': ['C4', 'D4', 'E4', 'G4', 'A4', 'C5']
        }
        
        # Chord progressions (as scale degrees)
        self.chord_progressions = [
            # Common progressions
            [1, 4, 5, 1],      # I-IV-V-I (Classic)
            [1, 6, 4, 5],      # I-vi-IV-V (50s progression)
            [2, 5, 1, 6],      # ii-V-I-vi (Jazz)
            [1, 5, 6, 4],      # I-V-vi-IV (Pop)
            
            # Extended progressions
            [1, 4, 1, 5, 6, 4, 5, 1],  # Extended classic
            [1, 5, 6, 3, 4, 1, 4, 5],  # Extended pop
            [2, 5, 1, 1, 2, 5, 1, 6],  # Extended jazz
            [1, 6, 2, 5, 1, 6, 4, 5],  # Circle progression
            
            # Modal progressions
            [6, 5, 4, 5],      # vi-V-IV-V (Minor feel)
            [4, 5, 3, 6],      # IV-V-iii-vi (Dreamy)
            [1, 3, 4, 2],      # I-iii-IV-ii (Modal)
            [1, 7, 6, 4],      # I-vii-vi-IV (Folk)
            
            # Complex progressions
            [1, 4, 7, 3, 6, 2, 5, 1],  # Descending thirds
            [1, 5, 2, 4, 7, 3, 6, 4],  # Mixed modal
            [2, 7, 1, 6, 4, 3, 5, 1],  # Jazz fusion
            [1, 3, 6, 4, 1, 4, 5, 5]   # Pop alternative
        ]
        
        # Drum patterns (1 = hit, 0 = rest) - 16 steps for more detail
        self.drum_patterns = {
            'house': {
                'kick':  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
                'snare': [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
                'hihat': [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0]
            },
            'tech_house': {
                'kick':  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
                'snare': [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,1,0],
                'hihat': [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1]
            },
            'ambient_minimal': {
                'kick':  [1,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
                'snare': [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
                'hihat': [0,0,1,0, 0,0,0,0, 0,0,1,0, 0,0,0,0]
            },
            'basic': {
                'kick':  [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
                'snare': [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
                'hihat': [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0]
            },
            'rock': {
                'kick':  [1,0,0,1, 0,0,1,0, 1,0,0,1, 0,0,1,0],
                'snare': [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
                'hihat': [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1]
            },
            'funk': {
                'kick':  [1,0,0,1, 0,1,0,0, 1,0,0,1, 0,1,0,0],
                'snare': [0,0,1,0, 1,0,0,1, 0,0,1,0, 1,0,0,1],
                'hihat': [1,1,0,1, 0,1,1,0, 1,1,0,1, 0,1,1,0]
            },
            'jazz': {
                'kick':  [1,0,0,0, 0,0,1,0, 0,1,0,0, 0,0,1,0],
                'snare': [0,0,1,0, 1,0,0,0, 0,0,1,0, 1,0,0,1],
                'hihat': [1,0,1,1, 1,0,1,1, 1,0,1,1, 1,0,1,1]
            },
            'latin': {
                'kick':  [1,0,1,0, 0,1,0,0, 1,0,1,0, 0,1,0,0],
                'snare': [0,0,1,0, 1,0,0,1, 0,0,1,0, 1,0,0,1],
                'hihat': [1,1,0,1, 1,0,1,1, 1,1,0,1, 1,0,1,1]
            },
            'electronic': {
                'kick':  [1,0,0,0, 1,0,0,0, 1,1,0,0, 1,0,0,0],
                'snare': [0,0,1,0, 0,1,0,0, 0,0,1,1, 0,1,0,0],
                'hihat': [0,1,1,1, 0,1,1,1, 0,1,1,1, 0,1,1,1]
            },
            'breakbeat': {
                'kick':  [1,0,0,1, 1,0,1,0, 0,1,0,1, 0,0,1,0],
                'snare': [0,0,1,0, 0,1,0,0, 1,0,0,0, 1,1,0,1],
                'hihat': [1,1,0,1, 0,1,1,0, 1,0,1,1, 0,1,0,1]
            },
            'shuffle': {
                'kick':  [1,0,0,0, 0,1,0,0, 1,0,0,0, 0,1,0,0],
                'snare': [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,1],
                'hihat': [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0]
            },
            'intro_build': {
                'kick':  [1,0,0,0, 0,0,0,0, 1,0,0,0, 1,0,0,0],
                'snare': [0,0,0,0, 0,0,0,0, 0,0,0,0, 1,0,0,0],
                'hihat': [0,0,1,0, 0,1,1,0, 1,1,1,0, 1,1,1,1]
            },
            'intro_build_2': {
                'kick':  [1,0,0,0, 1,0,0,0, 1,0,1,0, 1,1,1,0],
                'snare': [0,0,0,0, 1,0,0,0, 0,0,1,0, 1,0,1,1],
                'hihat': [1,0,1,0, 1,1,1,0, 1,1,1,1, 1,1,1,1]
            },
            'outro_wind_down': {
                'kick':  [1,1,1,0, 1,0,1,0, 1,0,0,0, 0,0,0,0],
                'snare': [1,0,1,1, 0,0,1,0, 0,0,0,0, 1,0,0,0],
                'hihat': [1,1,1,1, 1,1,1,0, 1,0,1,0, 0,0,0,0]
            },
            'outro_final': {
                'kick':  [1,0,0,0, 0,0,0,0, 1,0,0,0, 1,0,0,1],
                'snare': [0,0,0,0, 1,0,0,0, 0,0,0,0, 0,0,0,1],
                'hihat': [1,0,1,0, 0,0,1,0, 0,0,0,0, 0,0,0,1]
            }
        }

        # Musical timing - will be set in play_song()
        self.tempo = None
        self.beat_duration = None
        self.steps_per_beat = 4  # 16th notes
        self.step_duration = None
        self.beats_per_bar = 4
        self.bars_per_phrase = 4
        
        # Song structure templates
        self.song_structures = [
            # Simple verse-chorus form
            ['intro', 'verse', 'chorus', 'verse', 'chorus', 'chorus', 'outro'],
            # Verse-chorus with bridge
            ['intro', 'verse', 'chorus', 'verse', 'chorus', 'bridge', 'chorus', 'outro'],
            # Extended form
            ['intro', 'verse', 'verse', 'chorus', 'verse', 'bridge', 'chorus', 'chorus', 'outro']
        ]

        # Section-specific progression templates
        self.section_progressions = {
            'intro': [
                [1, 4, 1, 5],  # Simple intro
                [1, 6, 4, 5],  # Pop intro
                [1, 1, 4, 5]   # Repetitive intro
            ],
            'verse': [
                [1, 6, 4, 5],      # Common verse
                [1, 4, 1, 5],      # Simple verse
                [6, 4, 1, 5],      # Minor start verse
                [1, 3, 4, 4]       # Extended fourth
            ],
            'chorus': [
                [1, 4, 6, 5],      # Strong chorus
                [1, 5, 6, 4],      # Pop chorus
                [4, 1, 5, 5],      # Emphasis on five
                [1, 4, 1, 5]       # Resolution chorus
            ],
            'bridge': [
                [4, 5, 3, 6],      # Tension bridge
                [6, 5, 4, 5],      # Minor bridge
                [2, 5, 1, 6],      # Jazz bridge
                [4, 4, 1, 5]       # Build-up bridge
            ],
            'outro': [
                [1, 4, 1, 1],      # Resolving outro
                [1, 5, 1, 1],      # Strong resolution
                [4, 5, 1, 1]       # Final cadence
            ],
            # Sections for electronic genre
            'buildup': [
                [1, 5, 6, 4],      # Rising tension
                [4, 5, 5, 5],      # Sustained dominant
                [1, 1, 4, 5]       # Simple build
            ],
            'drop': [
                [1, 5, 1, 5],      # Strong alternation
                [1, 4, 1, 5],      # Classic progression
                [5, 1, 5, 1]       # Heavy emphasis
            ],
            'breakdown': [
                [6, 4, 1, 5],      # Minor to major
                [1, 6, 4, 5],      # Emotional progression
                [4, 1, 5, 6]       # Complex resolution
            ],
            # Sections for funk genre
            'groove': [
                [1, 4, 5, 4],      # Funk progression
                [1, 3, 4, 5],      # Soul progression
                [2, 5, 1, 4]       # Jazz-funk progression
            ],
            # Sections for ambient genre
            'flow': [
                [1, 6, 4, 5],      # Floating progression
                [4, 1, 6, 5],      # Dreamy progression
                [1, 4, 6, 3]       # Ethereal progression
            ],
            'build': [
                [1, 3, 6, 4],      # Gentle build
                [2, 5, 1, 4],      # Rising tension
                [4, 5, 6, 5]       # Suspended build
            ],
            'peak': [
                [1, 5, 6, 4],      # Climactic progression
                [4, 1, 5, 1],      # Strong resolution
                [1, 4, 5, 5]       # Sustained peak
            ]
        }

        # Section-specific drum patterns
        self.section_drums = {
            'intro': ['intro_build', 'intro_build_2'],
            'verse': ['basic', 'rock', 'funk'],
            'chorus': ['rock', 'electronic', 'breakbeat'],
            'bridge': ['jazz', 'latin', 'funk'],
            'outro': ['outro_wind_down', 'outro_final']
        }

        self.sample_rate = 44100

        # Create note ordering for melodic movement
        self.note_order = {note: idx for idx, note in enumerate([
            'C3', 'D3', 'E3', 'F3', 'G3', 'A3', 'B3',
            'C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4',
            'C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5'
        ])}

        # Pre-generate drum sounds
        self.drum_sounds = {
            'kick': None,
            'snare': None,
            'hihat': None
        }
        
        # Cache for generated tones
        self.tone_cache = {}
        self.max_cache_size = 1000

        self.volume = 0.5
        self.is_muted = False
        # Set initial mixer volume
        pygame.mixer.music.set_volume(self.volume)

    def set_volume(self, volume):
        """Set the volume for music playback"""
        self.volume = max(0.0, min(1.0, volume))
        actual_volume = 0.0 if self.is_muted else self.volume
        
        # Set volume for all active channels
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            if channel.get_busy():
                channel.set_volume(actual_volume)
    
    def set_muted(self, muted):
        """Set muted state for music"""
        self.is_muted = muted
        self.set_volume(self.volume)

    def apply_envelope(self, samples, attack=0.1, decay=0.2, sustain=0.7, release=0.4):
        """Apply ADSR envelope to a sample array"""
        num_samples = len(samples)
        envelope = np.ones(num_samples)
        
        attack_samples = int(attack * num_samples)
        decay_samples = int(decay * num_samples)
        release_samples = int(release * num_samples)
        
        # Attack phase
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay phase
        if decay_samples > 0:
            decay_end = attack_samples + decay_samples
            envelope[attack_samples:decay_end] = np.linspace(1, sustain, decay_samples)
        
        # Sustain phase is handled by the sustain level
        sustain_end = num_samples - release_samples
        envelope[decay_end:sustain_end] = sustain
        
        # Release phase
        if release_samples > 0:
            envelope[sustain_end:] = np.linspace(sustain, 0, release_samples)
        
        return samples * envelope

    def generate_harmonic_content(self, frequency, duration, harmonics):
        """Generate a tone with specific harmonic content"""
        num_samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, num_samples)
        wave = np.zeros(num_samples)
        
        for harmonic, amplitude in harmonics.items():
            wave += amplitude * np.sin(2.0 * np.pi * frequency * harmonic * t)
        
        return wave

    def generate_melody_tone(self, frequency, duration, amplitude=4096, genre='chill'):
        """Generate a tone with genre-appropriate timbre"""
        # Check cache first
        cache_key = f"melody_{frequency}_{duration}_{amplitude}_{genre}"
        if cache_key in self.tone_cache:
            return self.tone_cache[cache_key]
            
        # Apply genre-specific volume scaling
        if genre in self.genres:
            amplitude *= self.genres[genre].get('melody_volume', 1.0)
            
        # Generate if not in cache
        if genre == 'electronic':
            harmonics = {
                1.0: 1.0,    # Fundamental
                2.0: 0.3,    # Reduced harmonics for cleaner sound
                3.0: 0.15,
                4.0: 0.08,
                5.0: 0.04
            }
            attack, decay, sustain, release = 0.15, 0.3, 0.6, 0.3  # Smoother envelope
        elif genre == 'chill':
            harmonics = {
                1.0: 1.0,    # Fundamental
                2.0: 0.35,   # Softer harmonics for chill
                3.0: 0.12,
                4.0: 0.06,
                5.0: 0.03
            }
            attack, decay, sustain, release = 0.2, 0.3, 0.6, 0.4  # Smoother envelope
        elif genre == 'funk':
            harmonics = {
                1.0: 1.0,    # Fundamental
                2.0: 0.4,    # Brighter harmonics for funk
                3.0: 0.25,
                4.0: 0.15,
                5.0: 0.08
            }
            attack, decay, sustain, release = 0.05, 0.2, 0.6, 0.2  # Quick attack for funk
        else:  # ambient
            harmonics = {
                1.0: 1.0,    # Fundamental
                2.0: 0.3,    # Very soft harmonics for ambient
                3.0: 0.08,
                4.0: 0.04,
                5.0: 0.02
            }
            attack, decay, sustain, release = 0.3, 0.4, 0.5, 0.6  # Very smooth envelope
        
        wave = self.generate_harmonic_content(frequency, duration, harmonics)
        wave = self.apply_envelope(wave, attack=attack, decay=decay, sustain=sustain, release=release)
        
        # Add genre-specific effects
        if genre == 'electronic':
            # Add slight distortion for electronic
            wave = np.clip(wave * 1.2, -1, 1)
        elif genre == 'ambient':
            # Add chorus effect for ambient
            chorus_wave = self.generate_harmonic_content(frequency * 1.002, duration, harmonics)
            chorus_wave = self.apply_envelope(chorus_wave, attack=attack, decay=decay, sustain=sustain, release=release)
            wave = 0.7 * wave + 0.3 * chorus_wave
        
        # Normalize and scale
        amplitude = amplitude * (0.8 if genre == 'ambient' else 0.7)  # Softer for ambient
        wave = wave * (amplitude / np.max(np.abs(wave)))
        
        samples = wave.astype(np.int16)
        stereo = np.column_stack((samples, samples))
        sound = pygame.sndarray.make_sound(stereo)
        
        # Cache the result
        if len(self.tone_cache) < self.max_cache_size:
            self.tone_cache[cache_key] = sound
            
        return sound

    def generate_harmony_tone(self, frequency, duration, amplitude=4096):
        """Generate a harmony tone with the given frequency and duration"""
        if not _is_mixer_available():
            return None
            
        try:
            # Check cache first
            cache_key = f"harmony_{frequency}_{duration}_{amplitude}"
            if cache_key in self.tone_cache:
                return self.tone_cache[cache_key]
            
            # Generate if not in cache
            harmonics = {
                1.0: 1.0,    # Fundamental
                2.0: 0.3,    # Octave
                3.0: 0.05,   # Perfect fifth + octave
                4.0: 0.02    # Second octave
            }
            
            wave = self.generate_harmonic_content(frequency, duration, harmonics)
            wave = self.apply_envelope(wave, attack=0.25, decay=0.4, sustain=0.4, release=0.5)
            
            # Add very subtle chorus effect
            chorus_wave = self.generate_harmonic_content(frequency * 1.002, duration, harmonics)
            chorus_wave = self.apply_envelope(chorus_wave, attack=0.25, decay=0.4, sustain=0.4, release=0.5)
            wave = 0.8 * wave + 0.2 * chorus_wave
            
            # Reduce overall amplitude for harmony
            amplitude = amplitude * 0.5
            wave = wave * (amplitude / np.max(np.abs(wave)))
            
            samples = wave.astype(np.int16)
            stereo = np.column_stack((samples, samples))
            sound = pygame.sndarray.make_sound(stereo)
            
            # Cache the result
            if len(self.tone_cache) < self.max_cache_size:
                self.tone_cache[cache_key] = sound
            
            return sound
        except:
            return None

    def generate_drum_sound(self, type='kick', volume_scale=1.0):
        """Generate different types of drum sounds with more realistic timbres and volume control"""
        duration = 0.1 if type != 'hihat' else 0.05
        num_samples = int(duration * self.sample_rate)
        buffer = []
        
        if type == 'kick':
            # Start with higher frequency for attack
            freq = 150
            t = np.linspace(0, duration, num_samples)
            wave = np.zeros(num_samples)
            
            # Frequency sweep
            for i in range(num_samples):
                freq = max(40, freq * 0.9)
                wave[i] = math.sin(2.0 * math.pi * freq * t[i])
            
            # Add some distortion and compression for punch
            wave = np.clip(wave * 2.0, -1, 1)
            wave = np.sign(wave) * np.power(np.abs(wave), 0.8)  # Soft compression
            
            # Apply envelope
            wave = self.apply_envelope(wave, attack=0.01, decay=0.1, sustain=0.3, release=0.2)
            buffer = wave * (8192 * volume_scale)  # Apply volume scaling
            
        elif type == 'snare':
            # Mix sine wave and noise
            t = np.linspace(0, duration, num_samples)
            
            # Main body (sine wave at 200Hz)
            sine = np.sin(2.0 * np.pi * 200 * t)
            
            # Noise component with more high-end
            noise = np.random.uniform(-1, 1, num_samples)
            noise_hp = np.sin(2.0 * np.pi * 1000 * t) * noise  # High-pass filtered noise
            
            # Mix and shape with more noise
            wave = 0.4 * sine + 0.6 * noise_hp
            wave = self.apply_envelope(wave, attack=0.01, decay=0.1, sustain=0.2, release=0.1)
            buffer = wave * (7168 * volume_scale)  # Apply volume scaling
            
        else:  # hihat
            # High-frequency noise with resonant filter simulation
            noise = np.random.uniform(-1, 1, num_samples)
            
            # Apply band-pass filter effect (simplified)
            t = np.linspace(0, duration, num_samples)
            resonance = np.sin(2.0 * np.pi * 3000 * t)  # Higher frequency
            wave = noise * resonance
            
            # Add some high-frequency sizzle
            sizzle = np.sin(2.0 * np.pi * 5000 * t) * np.random.uniform(-0.5, 0.5, num_samples)
            wave = 0.7 * wave + 0.3 * sizzle
            
            # Sharp attack, quick decay
            wave = self.apply_envelope(wave, attack=0.01, decay=0.05, sustain=0.1, release=0.05)
            buffer = wave * (6144 * volume_scale)  # Apply volume scaling

        samples = np.array(buffer).astype(np.int16)
        stereo = np.column_stack((samples, samples))
        return pygame.sndarray.make_sound(stereo)

    def get_chord_notes(self, root_note, chord_type='major'):
        """Get the notes for a chord based on root note with different voicings"""
        root_freq = self.notes[root_note]
        
        # Get the note name without octave
        note_name = root_note[:-1]
        octave = int(root_note[-1])
        
        # Get all possible notes for this chord
        if chord_type == 'major':
            chord_notes = [
                f"{note_name}{octave}",  # Root
                f"{chr(((ord(note_name[0]) - ord('A') + 2) % 7) + ord('A'))}{octave}",  # Third
                f"{chr(((ord(note_name[0]) - ord('A') + 4) % 7) + ord('A'))}{octave}"   # Fifth
            ]
        else:  # minor
            chord_notes = [
                f"{note_name}{octave}",  # Root
                f"{chr(((ord(note_name[0]) - ord('A') + 2) % 7) + ord('A'))}{octave}",  # Minor Third
                f"{chr(((ord(note_name[0]) - ord('A') + 4) % 7) + ord('A'))}{octave}"   # Fifth
            ]
        
        # Add notes in different octaves
        extended_notes = []
        for note in chord_notes:
            note_name = note[:-1]
            note_octave = int(note[-1])
            extended_notes.append(f"{note_name}{note_octave - 1}")  # Add lower octave
            extended_notes.append(note)  # Add original note
            extended_notes.append(f"{note_name}{note_octave + 1}")  # Add higher octave
        
        # Filter out notes that aren't in our frequency dictionary
        valid_notes = [note for note in extended_notes if note in self.notes]
        
        # Create different voicing options
        voicings = [
            # Root position
            [self.notes[valid_notes[0]], self.notes[valid_notes[1]], self.notes[valid_notes[2]]],
            
            # First inversion (third on bottom)
            [self.notes[valid_notes[1]], self.notes[valid_notes[2]], self.notes[valid_notes[3]]],
            
            # Second inversion (fifth on bottom)
            [self.notes[valid_notes[2]], self.notes[valid_notes[3]], self.notes[valid_notes[4]]],
            
            # Spread voicing (wider intervals)
            [self.notes[valid_notes[0]], self.notes[valid_notes[3]], self.notes[valid_notes[5]]],
            
            # Close voicing (tighter intervals)
            [self.notes[valid_notes[1]], self.notes[valid_notes[2]], self.notes[valid_notes[3]]],
            
            # Drop 2 voicing (middle note dropped an octave)
            [self.notes[valid_notes[1]], self.notes[valid_notes[0]], self.notes[valid_notes[4]]]
        ]
        
        # Choose a random voicing, weighted towards more consonant options
        weights = [0.25, 0.2, 0.2, 0.15, 0.1, 0.1]  # Root position slightly preferred
        return random.choices(voicings, weights=weights)[0]

    def get_consonant_notes(self, chord_degree):
        """Get a list of notes that sound consonant with the given chord"""
        chord_notes = self.scale_degrees[chord_degree]
        
        # Add passing tones and neighboring tones that work well
        consonant_notes = []
        
        # Add all chord tones first (they get priority)
        consonant_notes.extend(chord_notes)
        
        # Add scale degrees that work well with this chord
        if chord_degree == 1:  # I chord
            consonant_notes.extend(['G4', 'E4', 'C5', 'D4'])
        elif chord_degree == 4:  # IV chord
            consonant_notes.extend(['F4', 'A4', 'C5', 'G4'])
        elif chord_degree == 5:  # V chord
            consonant_notes.extend(['G4', 'B4', 'D5', 'F4'])
        elif chord_degree == 6:  # vi chord
            consonant_notes.extend(['A4', 'C5', 'E4', 'B4'])
        else:  # For other chords, use triad notes plus neighboring scale tones
            base_note = chord_notes[0]
            scale_idx = self.scales['major'].index(base_note)
            if scale_idx > 0:
                consonant_notes.append(self.scales['major'][scale_idx - 1])
            if scale_idx < len(self.scales['major']) - 1:
                consonant_notes.append(self.scales['major'][scale_idx + 1])
        
        # Sort notes by pitch for easier stepwise motion
        consonant_notes.sort(key=lambda x: self.note_order.get(x, 0))
        
        return consonant_notes

    def generate_melody(self, progression, note_length_weights=None, step_preference=0.5):
        """Generate a melody that fits our time signature and chord progression"""
        if note_length_weights is None:
            note_length_weights = [
                (1.0, 0.6),   # quarter notes
                (2.0, 0.3),   # half notes
                (4.0, 0.1)    # whole notes
            ]
        
        melody = []
        total_beats = self.beats_per_bar * self.bars_per_phrase
        current_beat = 0
        
        # Calculate which chord is playing at each beat
        beats_per_chord = total_beats / len(progression)
        
        # Get genre-specific settings
        genre_info = self.genres.get(self.current_genre, {})
        max_interval = genre_info.get('max_interval', 2)
        repetition_chance = genre_info.get('repetition_chance', 0.3)
        rest_chance = genre_info.get('rest_chance', 0.2)
        
        # Start with a chord tone from the first chord
        first_chord = progression[0]
        consonant_notes = self.get_consonant_notes(first_chord)
        middle_idx = len(consonant_notes) // 2
        first_note = consonant_notes[middle_idx]
        melody.append((first_note, 1.0))
        current_beat += 1
        
        last_note = first_note
        last_note_idx = consonant_notes.index(last_note)
        repeated_notes_count = 0
        phrase_length = 0
        
        while current_beat < total_beats:
            # Add rests between phrases for breathing room
            if phrase_length >= 4 and random.random() < rest_chance:
                rest_length = 1.0
                melody.append((None, rest_length))
                current_beat += rest_length
                phrase_length = 0
                continue
            
            # Figure out which chord we're currently on
            chord_index = int(current_beat / beats_per_chord)
            if chord_index >= len(progression):
                chord_index = len(progression) - 1
            current_chord = progression[chord_index]
            
            # Get consonant notes for this chord
            consonant_notes = self.get_consonant_notes(current_chord)
            current_idx = consonant_notes.index(last_note) if last_note in consonant_notes else -1
            
            # Possibly repeat the last note (increased chance for singability)
            if random.random() < repetition_chance and repeated_notes_count < 2:
                note = last_note
                repeated_notes_count += 1
            else:
                # Choose next note with strong preference for stepwise motion
                possible_indices = []
                weights = []
                
                for i in range(len(consonant_notes)):
                    interval = i - current_idx
                    
                    # Skip if interval is too large
                    if abs(interval) > max_interval:
                        continue
                    
                    # Calculate weight based on several factors
                    weight = 1.0
                    
                    # Very strong preference for stepwise motion
                    if abs(interval) == 1:
                        weight *= 3.0
                    elif interval == 0:
                        weight *= 1.5
                    else:
                        weight *= 0.5
                    
                    # Prefer chord tones on strong beats
                    note = consonant_notes[i]
                    if current_beat % 2 == 0 and note in self.scale_degrees[current_chord]:
                        weight *= 2.0
                    
                    possible_indices.append(i)
                    weights.append(weight)
                
                if possible_indices:
                    chosen_idx = random.choices(possible_indices, weights=weights)[0]
                    note = consonant_notes[chosen_idx]
                    repeated_notes_count = 0
                else:
                    note = last_note
            
            # Choose note length based on position in phrase
            if current_beat % 4 == 0:
                # Prefer longer notes on strong beats
                length, _ = random.choices([(1.0, 0.7), (2.0, 0.3)], weights=[0.7, 0.3])[0]
            else:
                length, _ = random.choices(note_length_weights, weights=[w for _, w in note_length_weights])[0]
            
            # Adjust length if we're near the end of the phrase
            if current_beat + length > total_beats:
                length = total_beats - current_beat
            
            melody.append((note, length * self.beat_duration))
            current_beat += length
            phrase_length += length
            last_note = note
        
        return melody

    def generate_song_structure(self):
        """Generate a complete song structure with different sections"""
        genre_info = self.genres[self.current_genre]
        structure = random.choice(genre_info['structures'])
        
        # Generate and store melodies for each section type
        section_melodies = {}
        section_progressions = {}
        section_drums = {}
        
        # First pass: Generate melodies and progressions for each unique section type
        for section_type in set(structure):
            base_progression = random.choice(self.section_progressions[section_type])
            section_progressions[section_type] = base_progression
            
            # Generate melody with genre-appropriate parameters
            melody = self.generate_melody(
                base_progression,
                note_length_weights=genre_info['note_weights'],
                step_preference=genre_info['step_preference']
            )
            
            section_melodies[section_type] = melody
            
            # Choose drum pattern appropriate for genre and section
            if section_type in ['intro', 'outro']:
                # Keep special intro/outro patterns
                section_drums[section_type] = self.section_drums[section_type]
            else:
                # Use genre-appropriate drum styles
                section_drums[section_type] = [random.choice(genre_info['drum_styles'])]
        
        song_parts = []
        section_counts = {}
        
        for section in structure:
            section_counts[section] = section_counts.get(section, 0) + 1
            count = section_counts[section]
            
            if section in ['intro', 'outro']:
                pattern_index = min(count - 1, len(section_drums[section]) - 1)
                drum_style = section_drums[section][pattern_index]
            else:
                drum_style = section_drums[section][0]
            
            drum_pattern = self.drum_patterns[drum_style]
            
            song_parts.append({
                'section': section,
                'progression': section_progressions[section],
                'melody': section_melodies[section],
                'drums': drum_pattern
            })
        
        return song_parts

    def play_sound(self, sound):
        """Play a sound if the mixer is available"""
        if sound and _is_mixer_available():
            try:
                channel = pygame.mixer.find_channel(True)
                if channel:
                    channel.set_volume(0.0 if self.is_muted else self.volume)
                    channel.play(sound)
                    return sound
            except:
                pass
        return None

    def play_song(self):
        """Play a complete song with different sections"""
        try:
            # Choose random genre
            self.current_genre = random.choice(list(self.genres.keys()))
            genre_info = self.genres[self.current_genre]
            
            # Set genre-appropriate tempo
            self.tempo = random.randint(*genre_info['tempo_range'])
            self.beat_duration = 60.0 / self.tempo
            self.step_duration = self.beat_duration / self.steps_per_beat
            
            print(f"\nStarting new {self.current_genre} song at {self.tempo} BPM...")
            
            # Pre-generate drum sounds with genre-appropriate volume
            drum_volume = genre_info.get('drum_volume', 1.0)
            self.drum_sounds = {
                'kick': self.generate_drum_sound('kick', volume_scale=drum_volume),
                'snare': self.generate_drum_sound('snare', volume_scale=drum_volume),
                'hihat': self.generate_drum_sound('hihat', volume_scale=drum_volume)
            }
            
            song_parts = self.generate_song_structure()
            
            # Pre-generate all sounds for the entire song
            all_melody_sounds = {}
            for part in song_parts:
                melody_sounds = []
                melody_timings = []
                current_time = 0
                
                for note, duration in part['melody']:
                    if note is not None:
                        freq = self.notes[note]
                        tone = self.generate_melody_tone(freq, duration, genre=self.current_genre)  # Will be cached
                        melody_sounds.append((tone, duration))
                        melody_timings.append(current_time)
                    else:
                        melody_sounds.append((None, duration))
                        melody_timings.append(current_time)
                    current_time += duration
                    
                all_melody_sounds[id(part)] = (melody_sounds, melody_timings)

            # Pre-generate harmony sounds for each possible chord
            harmony_sounds = {}
            for chord_degree in range(1, 8):
                root_note = self.scales['major'][chord_degree - 1]
                chord_notes = self.get_chord_notes(root_note)
                for freq in chord_notes:
                    self.generate_harmony_tone(freq, self.beat_duration * 2)  # Cache the sound

            # Timing constants
            steps_per_bar = 16
            total_steps = steps_per_bar * self.bars_per_phrase
            step_duration = self.beat_duration / 4
            section_duration = total_steps * step_duration

            # Sound management
            active_sounds = []
            current_section_sounds = set()
            
            def cleanup_finished_sounds():
                """Remove finished sounds from active_sounds list"""
                if not _is_mixer_available():
                    return
            
                for sound in active_sounds[:]:
                    try:
                        if not pygame.mixer.find_channel(True):
                            sound.stop()
                            if sound in active_sounds:
                                active_sounds.remove(sound)
                            if sound in current_section_sounds:
                                current_section_sounds.remove(sound)
                    except:
                        # If we can't access the mixer, just clear the lists
                        active_sounds.clear()
                        current_section_sounds.clear()
                        break

            def stop_all_section_sounds():
                """Stop all sounds from the current section"""
                for sound in current_section_sounds.copy():
                    try:
                        sound.stop()
                        if sound in active_sounds:
                            active_sounds.remove(sound)
                        current_section_sounds.remove(sound)
                    except:
                        pass
                current_section_sounds.clear()
            
            def play_sound(sound):
                """Helper function to play and track sounds"""
                if sound is not None:
                    sound = self.play_sound(sound)
                    if sound:
                        active_sounds.append(sound)
                        current_section_sounds.add(sound)

            # Synchronization events and shared state
            start_event = Event()
            stop_event = Event()
            current_step = 0
            current_part_index = 0
            current_part = None
            current_elapsed = 0.0
            
            # Locks for shared state
            state_lock = Lock()
            
            def update_playback_state():
                """Main timing and state update loop"""
                nonlocal current_step, current_part_index, current_part, current_elapsed
                
                start_time = time.time()
                section_start_time = start_time
                
                while not stop_event.is_set() and current_part_index < len(song_parts):
                    current_time = time.time()
                    elapsed_in_section = current_time - section_start_time
                    
                    if elapsed_in_section >= section_duration:
                        stop_all_section_sounds()
                        current_part_index += 1
                        if current_part_index < len(song_parts):
                            print(f"\nPlaying {song_parts[current_part_index]['section']}...")
                            section_start_time = current_time
                            with state_lock:
                                current_part = song_parts[current_part_index]
                                current_step = 0
                                current_elapsed = 0.0
                        else:
                            print("\nSong finished!")
                            stop_event.set()
                            break
                        continue
                    
                    # Update shared state
                    with state_lock:
                        current_step = int(elapsed_in_section / step_duration)
                        current_part = song_parts[current_part_index]
                        current_elapsed = elapsed_in_section
                    
                    # Calculate timing for next step
                    next_step_time = section_start_time + (current_step * step_duration)
                    wait_time = next_step_time - current_time
                    if wait_time > 0:
                        time.sleep(wait_time)
                    
                    cleanup_finished_sounds()

            def play_melody_part():
                """Handle melody playback"""
                start_event.wait()
                last_step = -1
                
                while not stop_event.is_set():
                    with state_lock:
                        if current_part is None:
                            time.sleep(0.01)
                            continue
                            
                        step = current_step
                        part = current_part
                        elapsed = current_elapsed
                        
                        if step == last_step:
                            time.sleep(0.001)
                            continue
                        
                        last_step = step
                        
                        melody_sounds, melody_timings = all_melody_sounds[id(part)]
                        for sound, timing in zip(melody_sounds, melody_timings):
                            if abs(timing - elapsed) < step_duration / 2:
                                if sound[0] is not None:
                                    play_sound(sound[0])
                    time.sleep(0.001)

            def play_chord_part():
                """Handle chord playback with rhythmic variation"""
                start_event.wait()
                last_chord_step = -1
                last_voicing = None
                current_pattern = None
                pattern_duration = 0
                
                while not stop_event.is_set():
                    with state_lock:
                        if current_part is None:
                            time.sleep(0.01)
                            continue
                            
                        step = current_step
                        part = current_part
                        
                        # Change pattern every 4 bars
                        if step % 64 == 0:
                            try:
                                current_pattern = random.choice(self.harmony_patterns[self.current_genre])
                            except:
                                continue
                        
                        # Get current step in pattern
                        pattern_step = step % 16
                        
                        if step // 8 == last_chord_step:
                            time.sleep(0.001)
                            continue
                        
                        try:
                            if pattern_step == 0 or current_pattern[pattern_step]:
                                progression = part['progression']
                                chord_index = (step // 8) % len(progression)
                                chord_degree = progression[chord_index]
                                root_note = self.scales['major'][chord_degree - 1]
                                
                                # Choose chord voicing, avoiding the same voicing twice in a row
                                while True:
                                    chord_notes = self.get_chord_notes(root_note)
                                    if chord_notes != last_voicing:
                                        break
                                last_voicing = chord_notes
                                
                                # Play chord notes with genre-appropriate timing
                                for freq in chord_notes:
                                    # Shorter duration for funk/electronic, longer for ambient
                                    if self.current_genre in ['funk', 'electronic']:
                                        duration = self.beat_duration
                                    else:
                                        duration = self.beat_duration * 2
                                    tone = self.generate_harmony_tone(freq, duration, amplitude=1536)
                                    if tone is not None:  # Only play if tone generation succeeded
                                        play_sound(tone)
                                
                                last_chord_step = step // 8
                        except:
                            # Handle any errors during chord generation/playback
                            pass
                    time.sleep(0.001)

            def play_drum_part():
                """Handle drum playback"""
                start_event.wait()
                last_step = -1
                
                while not stop_event.is_set():
                    with state_lock:
                        if current_part is None:
                            time.sleep(0.01)
                            continue
                            
                        step = current_step
                        part = current_part
                        
                        if step == last_step:
                            time.sleep(0.001)
                            continue
                        
                        last_step = step
                        step_in_bar = step % steps_per_bar
                        
                        try:
                            for drum_type, pattern in part['drums'].items():
                                if pattern[step_in_bar]:
                                    if drum_type in self.drum_sounds:
                                        play_sound(self.drum_sounds[drum_type])
                        except (KeyError, AttributeError):
                            # Drum sounds might have been cleared during shutdown
                            pass
                    time.sleep(0.001)

            # Create and start threads
            threads = [
                Thread(target=update_playback_state),
                Thread(target=play_melody_part),
                Thread(target=play_chord_part),
                Thread(target=play_drum_part)
            ]

            for thread in threads:
                thread.daemon = True
                thread.start()

            print("\nStarting song...")
            start_event.set()

            # Wait for song to complete or stop event
            while not stop_event.is_set():
                time.sleep(0.1)
            
            # Cleanup
            stop_all_section_sounds()
            time.sleep(0.5)  # Allow time for cleanup
            
            # Clear pygame sound channels
            pygame.mixer.stop()
            
            # Set the volume before playing
            pygame.mixer.music.set_volume(0.0 if self.is_muted else self.volume)
            
        except Exception as e:
            print(f"Error in music playback: {e}")
            # Ensure cleanup happens even if there's an error
            pygame.mixer.stop()

    def stop_all_sounds(self):
        """Stop all sounds and cleanup resources"""
        try:
            # Set stop event first to prevent new sounds from being generated
            if hasattr(self, 'stop_event'):
                self.stop_event.set()
            
            # Small delay to let threads notice the stop event
            time.sleep(0.1)
            
            # Stop all channels
            if _is_mixer_available():
                pygame.mixer.stop()
            
            # Clear any cached sounds
            if hasattr(self, 'drum_sounds'):
                self.drum_sounds.clear()  # Use clear() instead of reassigning
            
            # Stop all section sounds if the function exists
            if hasattr(self, 'stop_all_section_sounds'):
                self.stop_all_section_sounds()
                
        except:
            pass  # Ignore any errors during cleanup

    def __del__(self):
        """Cleanup when the object is deleted"""
        self.stop_all_sounds()

if __name__ == "__main__":
    music_gen = MusicGenerator()
    music_gen.play_song()
