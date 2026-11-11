# Sentence start times of a voice WAV: silence split + whisper tiny.en (sherpa-onnx). python3 voice_times.py VOICE.wav (model dir: stt/sherpa-onnx-whisper-tiny.en)
import sys, subprocess, re, numpy as np, sherpa_onnx, scipy.io.wavfile as wf, scipy.signal as sg
wav=sys.argv[1]; M='stt/sherpa-onnx-whisper-tiny.en/'
out=subprocess.run(['ffmpeg','-i',wav,'-af','silencedetect=n=-35dB:d=0.3','-f','null','-'],capture_output=True,text=True).stderr
ss=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)]; se=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]
sr,a=wf.read(wav); a=a.astype('float32')/32768
if a.ndim>1:a=a.mean(1)
a16=sg.resample_poly(a,16000,sr).astype('float32')
starts=[0.0]+se; ends=ss+[len(a)/sr]
import glob
enc=glob.glob(M+'*encoder*int8*')[0]; dec=glob.glob(M+'*decoder*int8*')[0]; tok=glob.glob(M+'*tokens*')[0]
rec=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=enc,decoder=dec,tokens=tok)
for s,e in zip(starts,ends):
    if e-s<0.15: continue
    st=rec.create_stream(); st.accept_waveform(16000,a16[int(s*16000):int(e*16000)]); rec.decode_stream(st)
    print(f"{s:6.2f}-{e:6.2f} {st.result.text.strip()}")
