import json, sys, shutil, subprocess, pathlib
from playwright.sync_api import sync_playwright
here = pathlib.Path(__file__).parent
FPS = 24
D, B, C = "#17111B", "#F3E7D8", "#FBF3E8"   # sombre, beige, crème
ROSE, LILAS, TERRA, CIEL = "#EE9CAB", "#B9A3D9", "#E07A55", "#A9CCE8"
# Usage : python3 make_videos.py videos.json
# videos.json = {"nom_du_fichier": [[fond, couleur_texte, couleur_accent, taille, duree_s, ["ligne 1", "*mot en italique coloré*"]], ...], ...}
V = json.load(open(sys.argv[1], encoding="utf-8"))
HTML = r'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:G;src:url('file:///mnt/skills/examples/canvas-design/canvas-fonts/BricolageGrotesque-Bold.ttf')}
@font-face{font-family:S;src:url('file:///mnt/skills/examples/canvas-design/canvas-fonts/InstrumentSerif-Italic.ttf')}
@font-face{font-family:R;src:url('file:///mnt/skills/examples/canvas-design/canvas-fonts/BricolageGrotesque-Regular.ttf')}
*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
#stage{position:relative;width:1080px;height:1920px;overflow:hidden}
#glow{position:absolute;width:1500px;height:1500px;border-radius:50%;filter:blur(120px);opacity:.28}
#box{position:absolute;left:80px;right:150px;top:260px;bottom:620px;display:flex;flex-direction:column;justify-content:center;font-family:G;line-height:1.0;letter-spacing:-3px}
.w{display:inline-block;margin-right:.22em}.s{font-family:S;letter-spacing:-1px;font-size:1.3em;line-height:.95}
#h{position:absolute;left:80px;bottom:470px;font-family:R;font-size:44px;opacity:.75}
#grain{position:absolute;inset:0;opacity:.18;mix-blend-mode:multiply;pointer-events:none}
</style></head><body><div id="stage"><div id="glow"></div><div id="box"></div><div id="h">@jerecommence.encore</div>
<svg id="grain" width="1080" height="1920"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .9 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg></div>
<script>
const SC=__SCENES__;const $=id=>document.getElementById(id);const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));const oc=x=>1-Math.pow(1-clamp(x),3);
let starts=[],acc=0;for(const s of SC){starts.push(acc);acc+=s[4]}window.DUR=acc+0.6;let cur=-1,ws=[];
function build(i){const s=SC[i];$('stage').style.background=s[0];$('box').style.color=s[1];$('box').style.fontSize=s[3]+'px';$('h').style.color=s[1];$('glow').style.background=s[2];
 let it=false;$('box').innerHTML=s[5].map(l=>'<div style="white-space:nowrap">'+l.split(' ').map(x=>{if(x.startsWith('*'))it=true;const c=it;if(x.endsWith('*'))it=false;return `<span class="w ${c?'s':''}" style="${c?'color:'+s[2]:''}">${x.replace(/\*/g,'')}</span>`}).join('')+'</div>').join('');
 const mw=Math.max(...[...$('box').children].map(d=>{const r=document.createRange();r.selectNodeContents(d);return r.getBoundingClientRect().width}));if(mw>850)$('box').style.fontSize=Math.floor(s[3]*850/mw)+'px';ws=[...document.querySelectorAll('.w')]}
window.render=function(t){let i=0;for(let k=0;k<SC.length;k++)if(t>=starts[k])i=k;if(i!==cur){build(i);cur=i}
 const l=t-starts[i],d=SC[i][4],last=i===SC.length-1;
 ws.forEach((w,k)=>{const e=oc((l-0.08-k*0.11)/0.4);const out=last?1:1-clamp((l-(d-0.22))/0.2);w.style.opacity=e*out;w.style.transform=`translateY(${(1-e)*36}px)`;w.style.filter=`blur(${(1-e)*8}px)`});
 $('box').style.transform=`scale(${1+0.035*clamp(l/d)})`;$('box').style.transformOrigin='0% 50%';
 $('glow').style.left=(-300+Math.sin(t*0.5)*260)+'px';$('glow').style.top=(700+Math.cos(t*0.4)*320)+'px';
 $('h').style.opacity=last?0.75*clamp((l-1.2)*2):0};render(0);</script></body></html>'''
names = list(V)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1080,"height":1920})
    for n in names:
        f = here / f"{n}.html"; f.write_text(HTML.replace("__SCENES__", json.dumps(V[n], ensure_ascii=False)))
        pg.goto(f"file://{f}"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
        fr = here / "frames"; shutil.rmtree(fr, ignore_errors=True); fr.mkdir()
        N = int(pg.evaluate("window.DUR") * FPS)
        for i in range(N):
            pg.evaluate(f"render({i/FPS})"); pg.screenshot(path=str(fr/f"{i:05d}.jpg"), type="jpeg", quality=90)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(fr/"%05d.jpg"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","19","-movflags","+faststart",str(here/f"{n}.mp4")],check=True)
        shutil.rmtree(fr); f.unlink(); print(n, N/FPS, "s")
    b.close()
