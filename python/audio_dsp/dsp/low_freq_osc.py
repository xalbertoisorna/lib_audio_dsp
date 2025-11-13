import numpy as np
from audio_dsp.dsp import utils as utils
from audio_dsp.dsp.generic import dsp_block, Q_SIG

class low_freq_osc(dsp_block):
    def __init__(
            self, 
            fs: float,            # in Hz 
            n_chans : int,        # number of channels
            frequency: float,     # in Hz
            amplitude: float,     # amplitude
            phase_offset: float,  # starting phase in rad
        ):
        
        self.fs = fs
        self.frequency = frequency
        self.amplitude = amplitude
        self.Q_sig = Q_SIG
        
        # Python related
        self.phase_inc = (2 * np.pi * self.frequency) / self.fs
        self.phase = phase_offset
        
        # xcore related
        lut_bits = 12 # 16 KB :( 
        self.lut_size = (1 << lut_bits) #TODO should be enough forn 100Hz or below?
        self.reg_size = (1 << 32)
        self.lut_shr = (32 - lut_bits) 

        # Precompute LUT
        self.sine_amp_lut = np.zeros(self.lut_size, dtype=np.float32)

        TWO_PI = np.float32(2.0 * np.pi)
        inv_lut_size = np.float32(1.0 / self.lut_size)
        for i in range(self.lut_size):
            angle = TWO_PI * np.float32(i) * inv_lut_size
            angle = np.float32(angle)
            self.sine_amp_lut[i] = np.float32(self.amplitude * np.sin(angle, dtype=np.float32))
        
        # Precompute phase inc and offset
        uint32_max = np.iinfo(np.uint32).max
        tmp_phase = np.float64((phase_offset * uint32_max) / TWO_PI)
        tmp_inc = np.float64((frequency * uint32_max) / fs)
        self.phase_xcore = np.uint32(tmp_phase)
        self.phase_inc_xcore = np.uint32(tmp_inc)
        
        assert(self.frequency < fs / 2)
        assert(self.amplitude <= 1.0)   #TODO discuss
        assert(self.frequency <= 100)    #TODO discuss

    def process(self, sample: float, channel: int = 0):
        sample = 0.0  # unused
        y = self.amplitude * np.sin(self.phase)
        self.phase += self.phase_inc
        if self.phase >= 2 * np.pi:
            self.phase -= 2 * np.pi
        return float(y)

    def process_xcore(self, sample: float = 0.0, channel: int = 0):
        lut_idx = self.phase_xcore >> self.lut_shr
        with np.errstate(over='ignore'):
            self.phase_xcore += self.phase_inc_xcore
        return self.sine_amp_lut[lut_idx]

    def process_samples(self, num_samples: int):
        out = np.zeros(num_samples, dtype=float)
        for n in range(num_samples):
            out[n] = self.process(0.0)
        return out
    
    def process_xcore_samples(self, num_samples: int):
        out = np.zeros(num_samples, dtype=np.float32)
        for n in range(num_samples):
            out[n] = self.process_xcore(0.0)
        return out


if __name__ == "__main__":
    # Parameters
    fs = 32000
    f = 1
    duration = 1
    phase_offset = 0.2
    num_samples = int(fs * duration)
    amplitude = 1.0
    time = np.arange(num_samples) / fs
    lfo = low_freq_osc(
        fs=fs, frequency=f, amplitude=amplitude, phase_offset=phase_offset
    )
