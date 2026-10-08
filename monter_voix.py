"""Monte une vidéo texte + voix off.
Usage : python3 monter_voix.py audio.m4a ecrans.json nom_sortie
ecrans.json : {"nom": [[fond, texte, accent, taille, duree, ["ligne", ...]], ...]} (durées recalculées)
La lecture doit marquer une vraie pause entre chaque écran."""
import sys, json, subprocess, wave, numpy as np, pathlib, re
from scipy.signal import stft, istft
from scipy.ndimage import uniform_filter
here = pathlib.Path(__file__).parent
audio, ej, out = sys.argv[1], sys.argv[2], sys.argv[3]
V = json.load(open(ej, encoding="utf-8")); name = list(V)[0]; sc = V[name]; n = len(sc)
subprocess.run(["ffmpeg","-loglevel","error","-y","-i",audio,"-ac","1","-ar","48000","raw.wav"],check=True)
w=wave.open("raw.wav");sr=w.getframerate();x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(float)/32768
dur=len(x)/sr
# 1) segments de parole
def segments(min_sil):
    r=subprocess.run(["ffmpeg","-i","raw.wav","-af",f"silencedetect=noise=-35dB:d={min_sil}","-f","null","-"],capture_output=True,text=True).stderr
    st=[float(v) for v in re.findall(r"silence_start: ([\d.]+)",r)]; en=[float(v) for v in re.findall(r"silence_end: ([\d.]+)",r)]
    sil=list(zip(st,en+[dur]*(len(st)-len(en))))
    sp=[];cur=0.0
    for a,b in sil:
        if a-cur>0.25: sp.append((cur,a))
        cur=b
    if dur-cur>0.25: sp.append((cur,dur))
    return sp
sp=None
for ms in [1.2,1.0,0.85,0.7,0.6,0.5,0.45,0.4]:
    s=segments(ms)
    if len(s)>=n: sp=s; break
if sp is None: sys.exit(f"Pas assez de pauses : {len(s)} phrases trouvées pour {n} écrans")
# regrouper si trop de segments : fusionner les pauses les plus courtes
while len(sp)>n:
    gaps=[sp[i+1][0]-sp[i][1] for i in range(len(sp)-1)]; i=int(np.argmin(gaps))
    sp[i]=(sp[i][0],sp[i+1][1]); del sp[i+1]
print("phrases :",[(round(a,2),round(b,2)) for a,b in sp])
# 2) nettoyage du souffle (profil = silences)
f,t,Z=stft(x,sr,nperseg=2048,noverlap=1536);mag=np.abs(Z)
nmask=np.ones_like(t,bool)
for a,b in sp: nmask&=~((t>a-0.15)&(t<b+0.15))
nm=mag[:,nmask].mean(1,keepdims=True); ns=mag[:,nmask].std(1,keepdims=True)
g=(mag>nm+3*ns).astype(float); g=uniform_filter(g,size=(3,5)); g=np.where(g>0.35,1.0,g/0.35*0.5)
m2=np.maximum(mag-1.5*nm,0)*(0.01+0.99*g)
_,y=istft(m2*np.exp(1j*np.angle(Z)),sr,nperseg=2048,noverlap=1536);y=y[:len(x)]
wo=wave.open("clean.wav","wb");wo.setnchannels(1);wo.setsampwidth(2);wo.setframerate(sr);wo.writeframes((np.clip(y,-1,1)*32767).astype(np.int16).tobytes());wo.close()
# 3) durées des écrans : 0,8 s avant la 1re phrase, chaque écran apparaît 0,35 s avant sa phrase
off=sp[0][0]-0.8
starts=[0.0]+[sp[i][0]-off-0.35 for i in range(1,n)]
end=sp[-1][1]-off+2.2
for i in range(n): sc[i][4]=round((starts[i+1] if i+1<n else end)-starts[i],2)
json.dump({name+"_img":sc},open("tmp_v.json","w"),ensure_ascii=False)
subprocess.run(["python3",str(here/"mk.py"),"tmp_v.json"],check=True)
total=end+0.6
subprocess.run(["ffmpeg","-loglevel","error","-y","-ss",str(max(off,0)),"-i","clean.wav","-af",
  f"adelay={int(max(-off,0)*1000)}|{int(max(-off,0)*1000)},highpass=f=80,acompressor=threshold=-22dB:ratio=2:attack=10:release=150,loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={total}",
  "-ar","48000","-ac","2","voix_tmp.wav"],check=True)
subprocess.run(["ffmpeg","-loglevel","error","-y","-i",str(here/(name+"_img.mp4")),"-i","voix_tmp.wav","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",out],check=True)
print("OK",out,round(total,1),"s")
