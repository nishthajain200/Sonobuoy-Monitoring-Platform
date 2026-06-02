import numpy as np
from scipy.io import wavfile

def read_wav_file(file):
    """
    Read WAV file and return normalized float data, sample rate, and number of channels.
    """
    sample_rate, data = wavfile.read(file)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.float32:
        pass  # already float
    else:
        raise ValueError("Unsupported WAV format")

    if data.ndim == 1:
        channels = 1
        mono = data
    else:
        channels = data.shape[1]
        mono = np.mean(data, axis=1)  # mono mix

    return data, sample_rate, channels