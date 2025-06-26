import pygame

class SoundEffects:
    def __init__(self):
        # Ensure pygame mixer is initialized
        pygame.mixer.init()
        
        # Load or create sound effects
        self.move_sound = self._create_move_sound()
        self.block_fall_sound = self._create_block_fall_sound()
        self.contrast_shift_sound = self._create_contrast_shift_sound()
        self.victory_sound = self._create_victory_sound()
        
        # Set default volumes
        self.volume = 1.0
        self.is_muted = False
        self.set_volume(self.volume)

    def _create_move_sound(self):
        """Creates a pleasing blip sound for movement"""
        sound = pygame.mixer.Sound(self._generate_sine_wave(frequency=440, duration=0.05))
        return sound

    def _create_block_fall_sound(self):
        """Creates a tiny gentle blip for falling blocks"""
        sound = pygame.mixer.Sound(self._generate_sine_wave(frequency=880, duration=0.02))
        return sound

    def _create_contrast_shift_sound(self):
        """Creates a pleasing sound for contrast shift"""
        sound = pygame.mixer.Sound(self._generate_sine_wave(frequency=[440, 660], duration=0.1))
        return sound

    def _create_victory_sound(self):
        """Creates a short victory sound"""
        sound = pygame.mixer.Sound(self._generate_sine_wave(frequency=[440, 550, 660], duration=0.15))
        return sound

    def _generate_sine_wave(self, frequency, duration, amplitude=0.5):
        """
        Generate a simple sine wave sound
        frequency: can be a single number or list of frequencies for a chord
        duration: length of sound in seconds
        amplitude: volume of the sound (0.0 to 1.0)
        """
        import numpy as np
        
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        if isinstance(frequency, (int, float)):
            frequency = [frequency]
        
        # Generate the waveform (sum of frequencies)
        waveform = np.zeros_like(t)
        for freq in frequency:
            waveform += amplitude * np.sin(2 * np.pi * freq * t)
        
        # Normalize
        waveform = waveform / len(frequency)
        
        # Apply a simple envelope to avoid clicks
        envelope = np.ones_like(t)
        attack = int(0.005 * sample_rate)
        release = int(0.005 * sample_rate)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)
        waveform = waveform * envelope
        
        # Convert to 16-bit integer samples
        waveform = np.int16(waveform * 32767)
        return waveform.tobytes()

    def set_volume(self, volume):
        """Set volume for all sound effects"""
        self.volume = max(0.0, min(1.0, volume))
        actual_volume = 0.0 if self.is_muted else self.volume
        
        self.move_sound.set_volume(actual_volume)
        self.block_fall_sound.set_volume(actual_volume * 0.3)
        self.contrast_shift_sound.set_volume(actual_volume)
        self.victory_sound.set_volume(actual_volume)

    def set_muted(self, muted):
        """Set muted state for all sound effects"""
        self.is_muted = muted
        self.set_volume(self.volume)

    def play_move(self):
        """Play the movement sound"""
        if not self.is_muted:
            self.move_sound.play()

    def play_block_fall(self):
        """Play the block fall sound"""
        if not self.is_muted:
            self.block_fall_sound.play()

    def play_contrast_shift(self):
        """Play the contrast shift sound"""
        if not self.is_muted:
            self.contrast_shift_sound.play()

    def play_victory(self):
        """Play the victory sound"""
        if not self.is_muted:
            self.victory_sound.play() 
