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
        self.lut_qsig = self.Q_sig
        self.phase_offset = phase_offset
        
        # Python related
        self.phase_inc = (2 * np.pi * self.frequency) / self.fs
        self.phase = phase_offset
        
        # xcore related
        lut_bits = 12 # 16 KB :( 
        self.lut_size = (1 << lut_bits) #TODO should be enough forn 100Hz or below?
        self.reg_size = (1 << 32)
        self.lut_shr = (32 - lut_bits) 

        # Precompute LUT
        self.get_lut(self.lut_size)
        
        # Cast params to float32 
        dt = utils.float32
        fs_f32 = dt(fs)
        frequency_f32 = dt(frequency)
        phase_offset_f32 = dt(phase_offset)

        # Precompute phase inc and offset
        UINT32_MAX = dt(0xFFFFFFFF)
        TWO_PI = dt(2.0 * np.pi)
        denom_phase = UINT32_MAX / TWO_PI          # float32
        denom_inc = UINT32_MAX / fs_f32            # float32
        tmp_phase = np.float32(phase_offset_f32 * denom_phase)
        tmp_inc = np.float32(frequency_f32 * denom_inc)
        self.phase_xcore = np.uint32(tmp_phase)
        self.phase_inc_xcore = np.uint32(tmp_inc)
        self.amplitude_q27 = np.int32(np.float32(amplitude) * ((1 << Q_SIG) - 1))
        
        # Assertions
        assert(self.frequency < fs / 2)
        assert(self.amplitude <= 1.0)    #TODO discuss
        assert(self.frequency <= 100)    #TODO discuss

    def get_lut(self, lut_size):
        self.sine_lut = np.zeros(lut_size, dtype=np.int32)
        two_pi = np.float64(2.0 * np.pi)
        inv_lut_size = np.float64(1.0 / lut_size)
        for i in range(lut_size):
            angle = two_pi * i * inv_lut_size
            angle = np.sin(angle)
            self.sine_lut[i] = utils.float_to_fixed(angle, self.lut_qsig)
    
    def save_lut(self, lut_size, filename="lfo_sine_lut.txt"):
        # Precompute LUT
        self.get_lut(lut_size)
        # write it to a file
        np.savetxt(filename, self.sine_lut, fmt="%d,")

    def process(self, sample: float, channel: int = 0):
        sample = 0.0  # unused
        y = self.amplitude * np.sin(self.phase)
        self.phase += self.phase_inc
        if self.phase >= 2 * np.pi:
            self.phase -= 2 * np.pi
        return float(y)

    def process_xcore(self, sample: float = 0.0, channel: int = 0):
        lut_idx = np.uint32(self.phase_xcore >> self.lut_shr)
        frac = np.uint32(self.phase_xcore & ((1 << self.lut_shr) - 1))
        frac_q27 = np.int64(np.int64(frac) << (27 - self.lut_shr))
        y0 = np.int64(self.sine_lut[lut_idx])
        y1 = np.int64(self.sine_lut[(lut_idx + 1) & (self.lut_size - 1)])
        interp_q27 = y0 + ((y1 - y0) * frac_q27 >> 27)
        product = interp_q27 * np.int64(self.amplitude_q27)
        out_q27 = np.int32(product >> 27)
        with np.errstate(over='ignore'):
            self.phase_xcore = np.uint32(self.phase_xcore + self.phase_inc_xcore)
        return utils.fixed_to_float(out_q27, 27)

    def process_samples(self, num_samples: int):
        out = np.zeros(num_samples, dtype=float)
        for n in range(num_samples):
            out[n] = self.process(0.0)
        return out
    
    def process_xcore_samples(self, num_samples: int):
        out = np.zeros(num_samples, dtype=float)
        for n in range(num_samples):
            out[n] = self.process_xcore(0.0)
        return out



def lfo_write_params(params_file, in_file, fs, frequency, amplitude, ph_offset, samples):
  with open(params_file, "w") as f:
    f.write(f"{fs},{frequency},{amplitude},{ph_offset},{samples}\n")

  with open(in_file, "w") as f:
    f.write("empty on purpose for now\n")  

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from pathlib import Path

    # Parameters
    fs = 48000
    f = 0.9987
    duration = 4
    phase_offset = 0.2
    num_samples = int(fs * duration)
    amplitude = 1.0
    time = np.arange(num_samples) / fs
    lfo = low_freq_osc(fs, 1, frequency=f, amplitude=amplitude, phase_offset=phase_offset)
    py_samples = lfo.process_samples(num_samples)
    pyxc = lfo.process_xcore_samples(num_samples)

    mse = np.mean((py_samples - pyxc)**2)
    print(f"MSE between python and xcore python: {mse}")

    # create dirs and write params
    bin_dir = Path(__file__).parent / "bin"
    test_dir = bin_dir / f"low_freq_osc_{f}"
    bin_path = bin_dir / "low_freq_osc_test.xe"
    file_in = test_dir / "sig_in.bin"
    file_out = test_dir / "sig_out.bin"
    file_params = test_dir / "params.txt"
    test_dir.mkdir(parents=True, exist_ok=True)
    lfo_write_params(
        file_params, file_in, 
        fs=fs, frequency=f, amplitude=amplitude, 
        ph_offset=phase_offset, samples=num_samples
    )


    # plot it
    plt.plot(time, py_samples, label="python" ,alpha=0.7)
    plt.plot(time, pyxc, label="xcore python", linestyle='--', alpha=0.7)
    plt.legend()
    plt.show()

    # save LUT
    lfo.save_lut(lfo.lut_size, filename="lfo_sine_lut_q27.h")
