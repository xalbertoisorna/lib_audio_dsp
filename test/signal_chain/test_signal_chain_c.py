# Copyright 2024-2025 XMOS LIMITED.
# This Software is subject to the terms of the XMOS Public Licence: Version 1.
import numpy as np
import soundfile as sf
from pathlib import Path
import shutil
import subprocess
import audio_dsp.dsp.signal_chain as sc
from audio_dsp.dsp.generic import Q_SIG
import audio_dsp.dsp.signal_gen as gen
import audio_dsp.dsp.low_freq_osc as lfo

import pytest
from test.test_utils import xdist_safe_bin_write, float_to_qxx, qxx_to_float, q_convert_flt

cwd = Path(__file__).parent.absolute()
bin_dir = Path(__file__).parent / "bin"
gen_dir = Path(__file__).parent / "autogen"

fs = 48000


def get_sig(len=0.05):
  sig_fl = []
  sig_fl.append(gen.sin(fs, len, 997, 0.7))
  sig_fl.append(gen.sin(fs, len, 100, 0.7))
  sig_fl = np.stack(sig_fl, axis=0)
  sig_fl = q_convert_flt(sig_fl, 23, Q_SIG)

  sig_int = float_to_qxx(sig_fl)

  name = "sig_48k"
  sig_path = bin_dir /  str(name + ".bin")

  xdist_safe_bin_write(sig_int[0], sig_path)

  # wav file does not need to be locked as it is only used for debugging outside pytest
  wav_path = gen_dir / str(name + ".wav")
  sf.write(wav_path, sig_fl[0], int(fs), "PCM_24")

  name = "sig1_48k"
  sig_path = bin_dir /  str(name + ".bin")
  xdist_safe_bin_write(sig_int[1], sig_path)

  # wav file does not need to be locked as it is only used for debugging outside pytest
  wav_path = gen_dir / str(name + ".wav")
  sf.write(wav_path, sig_fl[1], int(fs), "PCM_24")

  return sig_fl


def get_c_wav(dir_name, comp_name, verbose=False, sim = True):
  app = "xsim" if sim else "xrun --io"
  run_cmd = app + " " + str(bin_dir / f"{comp_name}_test.xe")
  stdout = subprocess.check_output(run_cmd, cwd = dir_name, shell = True)
  if verbose: print("run msg:\n", stdout.decode())

  sig_bin = dir_name / "sig_out.bin"
  assert sig_bin.is_file(), f"Could not find output bin {sig_bin}"
  sig_int = np.fromfile(sig_bin, dtype=np.int32)

  sig_fl = qxx_to_float(sig_int)
  sf.write(gen_dir / "sig_c.wav", sig_fl, fs, "PCM_24")
  return sig_fl

def get_c_wav2(dir_name, run_cmd, verbose=False):
  stdout = subprocess.check_output(run_cmd)
  if verbose: print("run msg:\n", stdout.decode())

  sig_bin = dir_name / "sig_out.bin"
  assert sig_bin.is_file(), f"Could not find output bin {sig_bin}"
  sig_int = np.fromfile(sig_bin, dtype=np.int32)

  sig_fl = qxx_to_float(sig_int)
  sf.write(gen_dir / "sig_c.wav", sig_fl, fs, "PCM_24")
  return sig_fl

def write_gain(test_dir, gain):
  all_filt_info = np.empty(0, dtype=np.int32)
  all_filt_info = np.append(all_filt_info, np.array(gain, dtype=np.int32))
  all_filt_info.tofile(test_dir / "gain.bin")


def single_channels_test(filt, test_dir, fname, sig_fl):
  out_py = np.zeros(sig_fl.shape[1])

  for n in range(sig_fl.shape[1]):
    out_py[n] = filt.process_channels_xcore(sig_fl[:, n])[0]
  
  sf.write(gen_dir / "sig_py_int.wav", out_py, fs, "PCM_24")

  out_c = get_c_wav(test_dir, fname)
  shutil.rmtree(test_dir)

  np.testing.assert_allclose(out_c, out_py, rtol=0, atol=0)


@pytest.fixture(scope="module")
def in_signal():
  bin_dir.mkdir(exist_ok=True, parents=True)
  gen_dir.mkdir(exist_ok=True, parents=True)
  return get_sig()


@pytest.mark.parametrize("gain_dB", [-10, 0, 24])
def test_gains_c(in_signal, gain_dB):
  filt = sc.fixed_gain(fs, 1, gain_dB)
  test_dir = bin_dir / f"fixed_gain_{gain_dB}"
  test_dir.mkdir(exist_ok = True, parents = True)
  write_gain(test_dir, filt.gain_int)

  out_py = np.zeros(in_signal.shape[1])
  
  for n in range(in_signal.shape[1]):
    out_py[n] = filt.process_xcore(in_signal[0][n])

  sf.write(gen_dir / "sig_py_int.wav", out_py, fs, "PCM_24")

  out_c = get_c_wav(test_dir, "fixed_gain")
  shutil.rmtree(test_dir)

  np.testing.assert_allclose(out_c, out_py, rtol=0, atol=0)


def test_subtractor_c(in_signal):
  filt = sc.subtractor(fs)
  test_dir = bin_dir / "subtractor"
  test_dir.mkdir(exist_ok = True, parents = True)

  single_channels_test(filt, test_dir, "subtractor", in_signal)


def test_adder_c(in_signal):
  filt = sc.adder(fs, 2)
  test_dir = bin_dir / "adder"
  test_dir.mkdir(exist_ok = True, parents = True)

  single_channels_test(filt, test_dir, "adder", in_signal)


@pytest.mark.parametrize("gain_dB", [-12, -6, 0])
def test_mixer_c(in_signal, gain_dB):
  filt = sc.mixer(fs, 2, gain_dB)
  test_dir = bin_dir / f"mixer_{gain_dB}"
  test_dir.mkdir(exist_ok = True, parents = True)
  write_gain(test_dir, filt.gain_int)

  single_channels_test(filt, test_dir, "mixer", in_signal)


@pytest.mark.parametrize("gains_dB", [[0, -6, 6], [-10, 3, 0]])
@pytest.mark.parametrize("slew", [1, 10])
@pytest.mark.parametrize("mute_test", [True, False])
def test_volume_control_c(in_signal, gains_dB, slew, mute_test):
  filt = sc.volume_control(fs, 1, gains_dB[0], slew)
  test_dir = bin_dir / f"volume_control_{gains_dB[0]}_{gains_dB[1]}_{gains_dB[2]}_{slew}_{mute_test}"
  test_dir.mkdir(exist_ok = True, parents = True)
  
  test_info = [0] * 5
  test_info[0] = mute_test
  test_info[1] = filt.slew_shift
  test_info[2] = filt.target_gain_int

  out_py = np.zeros(in_signal.shape[1])
  intervals = [0] * 4
  intervals[1] = in_signal.shape[1] // 3
  intervals[2] = intervals[1] * 2
  intervals[3] = in_signal.shape[1]
  
  for n in range(intervals[0], intervals[1]):
    out_py[n] = filt.process_xcore(in_signal[0][n])

  filt.set_gain(gains_dB[1])
  if mute_test: filt.mute()
  test_info[3] = filt.target_gain_int

  for n in range(intervals[1], intervals[2]):
    out_py[n] = filt.process_xcore(in_signal[0][n])

  filt.set_gain(gains_dB[2])
  if mute_test: filt.unmute()
  test_info[4] = filt.target_gain_int
  
  for n in range(intervals[2], intervals[3]):
    out_py[n] = filt.process_xcore(in_signal[0][n])

  sf.write(gen_dir / "sig_py_int.wav", out_py, fs, "PCM_24")

  test_info = np.array(test_info, dtype=np.int32)
  test_info.tofile(test_dir / "gain.bin")

  out_c = get_c_wav(test_dir, "volume_control")
  shutil.rmtree(test_dir)

  np.testing.assert_allclose(out_c, out_py, rtol=0, atol=0)


@pytest.mark.parametrize("delay_spec", [[1, 0, "samples"],
                                        [0.5, 0.5, "ms"],
                                        [0.02, 0.01, "s"],
                                        [0.5, 0, "ms"]])
def test_delay_c(in_signal, delay_spec):
  filter = sc.delay(fs, 1, *delay_spec)
  test_dir = bin_dir / f"delay_{delay_spec[0]}_{delay_spec[1]}_{delay_spec[2]}"
  test_dir.mkdir(exist_ok = True, parents = True)

  delay_info = np.empty(0, dtype=np.int32)
  delay_info = np.append(delay_info, filter._max_delay)
  delay_info = np.append(delay_info, filter._delay)
  delay_info = np.array(delay_info, dtype=np.int32)
  print(delay_info)
  delay_info.tofile(test_dir / "delay.bin")

  out_py = np.zeros((1, in_signal.shape[1]))
  for n in range(len(in_signal[0])):
    out_py[:, n] = filter.process_channels_xcore(in_signal[0, n:n+1].tolist())

  sf.write(gen_dir / "sig_py_int.wav", out_py[0], fs, "PCM_24")

  out_c = get_c_wav(test_dir, "delay")
  shutil.rmtree(test_dir)
  np.testing.assert_allclose(out_c, out_py[0], rtol=0, atol=0)


def test_switch_slew_c(in_signal):

  filt = sc.switch_slew(fs, 2)

  test_dir = bin_dir / "switch_slew"
  test_dir.mkdir(exist_ok = True, parents = True)
  fname = "switch_slew"

  out_py = np.zeros(in_signal.shape[1])

  for n in range(in_signal.shape[1]//2):
    out_py[n] = filt.process_channels_xcore(in_signal[:, n])[0]

  filt.move_switch(1)

  for n in range(in_signal.shape[1]//2, in_signal.shape[1]):
    out_py[n] = filt.process_channels_xcore(in_signal[:, n])[0]

  sf.write(gen_dir / "sig_py_int.wav", out_py, fs, "PCM_24")

  out_c = get_c_wav(test_dir, fname)
  shutil.rmtree(test_dir)

  np.testing.assert_allclose(out_c, out_py, rtol=0, atol=0)


@pytest.mark.parametrize("mix", [0, 0.1, 0.5, 0.9, 1.0])
def test_crossfader_c(in_signal, mix):

  # initial mix of zero  
  filt = sc.crossfader(fs, 2, 0)
  test_dir = bin_dir / f"crossfader_{mix}"
  test_dir.mkdir(exist_ok = True, parents = True)
  write_gain(test_dir, filt.gains_int)

  test_info = [0] * 5
  test_info[0] = filt.slew_shift
  test_info[1:3] = filt.target_gains_int

  # set mix to desired mix
  filt.mix = mix
  test_info[3:] = filt.target_gains_int

  test_info = np.array(test_info, dtype=np.int32)
  test_info.tofile(test_dir / "gain.bin")

  single_channels_test(filt, test_dir, "crossfader", in_signal)


@pytest.mark.parametrize("channel_states", [
    [True, False, False, False],  # Only channel 0 active
    [False, True, False, False],  # Only channel 1 active
    [True, True, False, False],   # Channel 0 and 1 active
    [True, True, True, True]      # All channels active
])
def test_router_4to1_c(in_signal, channel_states):
    in_signal = np.tile(in_signal, [2, 1])
    filt = sc.router_4to1(fs, 4)
    test_dir = bin_dir / f"router_4to1_{''.join(['1' if s else '0' for s in channel_states])}"
    test_dir.mkdir(exist_ok=True, parents=True)
    
    # Write channel states to file
    channel_states_int = np.array([int(s) for s in channel_states], dtype=np.int32)
    channel_states_int.tofile(test_dir / "channel_states.bin")
    
    # Set channel states in Python implementation
    filt.set_channel_states(channel_states)
    
    out_py = np.zeros(in_signal.shape[1])
    
    for n in range(in_signal.shape[1]):
        out_py[n] = filt.process_channels_xcore(in_signal[:, n])[0]
    
    sf.write(gen_dir / "sig_py_int.wav", out_py, fs, "PCM_24")
    
    out_c = get_c_wav(test_dir, "router_4to1")
    shutil.rmtree(test_dir)
    
    np.testing.assert_allclose(out_c, out_py, rtol=0, atol=0)


def lfo_write_params(params_file, in_file, fs, frequency, amplitude, ph_offset, samples):
  with open(params_file, "w") as f:
    f.write(f"{fs},{frequency},{amplitude},{ph_offset},{samples}\n")

  with open(in_file, "w") as f:
    f.write("empty on purpose for now\n")  


@pytest.mark.parametrize("frequency", [0.0999, 0.1, 0.997, 1.0, 9.97, 10, 11.24, 20, 44, 100])
@pytest.mark.parametrize("amplitude", [1.0])
def test_low_freq_osc(frequency, amplitude):
  duration = 2.0
  phase_offset = 0.2
  num_samples = int(fs * duration)
  t = np.arange(num_samples) / fs
  
  gen = lfo.low_freq_osc(fs, frequency=frequency, phase_offset=phase_offset, amplitude=amplitude)

  test_dir = bin_dir / f"low_freq_osc_{frequency}"
  test_dir.mkdir(exist_ok = True, parents = True)

  # create dirs and write params
  bin_path = bin_dir / "low_freq_osc_test.xe"
  file_in = test_dir / "sig_in.bin"
  file_out = test_dir / "sig_out.bin"
  file_params = test_dir / "params.txt"

  lfo_write_params(
    file_params, file_in, 
    fs=fs, frequency=frequency, amplitude=amplitude, 
    ph_offset=phase_offset, samples=num_samples
  )

  # python ideal
  ideal = gen.process_samples(num_samples)
  ideal = np.array(ideal, dtype=float)

  # py xcore
  out_py = gen.process_xcore_samples(num_samples)
  out_py = np.array(out_py, dtype=np.float32)

  # c xcore
  run_cmd = [
    "xsim",
    "--args",
    bin_path.relative_to(cwd),
    file_in.relative_to(cwd),
    file_params.relative_to(cwd),
    file_out.relative_to(cwd),
  ]
  out_c = get_c_wav2(test_dir, run_cmd)
  out_c = np.array(out_c, dtype=np.float32)

  # cleanup and compare
  shutil.rmtree(test_dir)

  # tols
  rtol = 0.0
  atol = 1e-7       #TODO reduce to 0
  thdn_tol = -60.0  #TODO reduce

  if frequency >= 20: # LUT steps are more visible at high freq
    atol = 5e-6      #TODO reduce to 0
    thdn_tol = -40.0 #TODO reduce
  
  if frequency >= 80: # Not really recommended to use for now
    atol = 2e-3      #TODO reduce to 0
    rtol = 2e-3      #TODO reduce to 0

  # direct compare 
  np.testing.assert_allclose(out_c, out_py, rtol=rtol, atol=atol) #TODO reduce to 0

  # thdn compare 
  residual = out_c - ideal
  power_signal, power_noise = np.mean(ideal ** 2), np.mean(residual ** 2)
  thdn = np.sqrt(power_noise / power_signal)
  thdn_db = 20 * np.log10(thdn)
  assert thdn_db <= thdn_tol




if __name__ =="__main__":
  bin_dir.mkdir(exist_ok=True, parents=True)
  gen_dir.mkdir(exist_ok=True, parents=True)
  sig_fl = get_sig()
  
  #test_gains_c(sig_fl, -6)
  #test_subtractor_c(sig_fl)
  #test_adder_c(sig_fl)
  #test_mixer_c(sig_fl, -3)
  # test_volume_control_c(sig_fl, [0, -6, 6], 7, False)
  # test_switch_slew_c(sig_fl)
  # test_crossfader_c(sig_fl, 0.1)
  test_low_freq_osc(1.0)
