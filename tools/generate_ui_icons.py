from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'icons'
OUT.mkdir(parents=True, exist_ok=True)
S = 384
BG = (0,0,0,0)
FG = '#DCE8F3'
MUTED = '#9DB1C5'
BLUE = '#58AFFF'
GREEN = '#56E39F'
RED = '#FF4C5B'
YELLOW = '#FFD15A'


def canvas():
    im = Image.new('RGBA', (S,S), BG)
    return im, ImageDraw.Draw(im)

def line(d, pts, fill=FG, width=26):
    d.line(pts, fill=fill, width=width, joint='curve')
    # round caps
    r=width//2
    for x,y in (pts[0], pts[-1]):
        d.ellipse((x-r,y-r,x+r,y+r), fill=fill)

def box(d, xy, fill=None, outline=FG, width=22, radius=38):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def save(name, draw_fn):
    im,d = canvas(); draw_fn(d)
    im.resize((96,96), Image.Resampling.LANCZOS).save(OUT/f'{name}.png')

# navigation / section icons
save('record', lambda d: d.ellipse((105,105,279,279), fill=RED))

def takes(d):
    box(d,(82,125,302,290),outline=FG,width=22,radius=22)
    line(d,[(91,150),(292,105)],width=22)
    for x in (118,180,242): line(d,[(x,121),(x+30,150)],width=14)
    line(d,[(125,205),(260,205)],width=16); line(d,[(125,245),(230,245)],width=16)
save('takes',takes)

def notes(d):
    box(d,(96,68,288,316),outline=FG,width=22,radius=24)
    line(d,[(137,143),(249,143)],width=14); line(d,[(137,191),(249,191)],width=14); line(d,[(137,239),(220,239)],width=14)
    d.polygon([(234,68),(288,68),(288,122)],fill=MUTED)
save('notes',notes)

def remote(d):
    # wifi arcs
    d.arc((62,70,322,330),210,330,fill=FG,width=24)
    d.arc((105,118,279,292),210,330,fill=FG,width=24)
    d.arc((148,168,236,256),210,330,fill=FG,width=24)
    d.ellipse((178,278,206,306),fill=GREEN)
save('remote',remote)

def gear(d):
    d.ellipse((115,115,269,269),outline=FG,width=22)
    d.ellipse((167,167,217,217),outline=FG,width=20)
    for a in range(0,360,45):
        import math
        r1,r2=108,148; cx=cy=192
        x1=cx+math.cos(math.radians(a))*r1; y1=cy+math.sin(math.radians(a))*r1
        x2=cx+math.cos(math.radians(a))*r2; y2=cy+math.sin(math.radians(a))*r2
        line(d,[(x1,y1),(x2,y2)],width=24)
save('system',gear)

def helpi(d):
    d.ellipse((78,78,306,306),outline=FG,width=22)
    d.arc((135,112,251,235),190,354,fill=FG,width=22)
    line(d,[(192,224),(192,245)],width=20)
    d.ellipse((179,271,205,297),fill=FG)
save('help',helpi)

def waveform(d):
    xs=[86,120,154,188,222,256,290]; hs=[62,116,184,240,184,116,62]
    for x,h in zip(xs,hs): line(d,[(x,192-h//2),(x,192+h//2)],fill=BLUE,width=20)
save('tracks',waveform)

def slate(d):
    box(d,(78,132,306,296),outline=FG,width=22,radius=20)
    line(d,[(86,156),(296,100)],width=22)
    for x in (110,175,240): line(d,[(x,135),(x+34,160)],width=13)
    line(d,[(125,210),(257,210)],width=14); line(d,[(125,252),(230,252)],width=14)
save('slate',slate)

def mic(d):
    box(d,(142,72,242,222),outline=FG,width=22,radius=48)
    d.arc((105,142,279,290),0,180,fill=FG,width=22)
    line(d,[(192,290),(192,326)],width=20); line(d,[(145,326),(239,326)],width=20)
save('input',mic)

def audio(d):
    d.polygon([(86,160),(138,160),(208,102),(208,282),(138,224),(86,224)],fill=FG)
    d.arc((190,120,320,264),300,60,fill=BLUE,width=22); d.arc((172,88,350,298),300,60,fill=BLUE,width=20)
save('audio',audio)

def disk(d):
    box(d,(82,102,302,282),outline=FG,width=22,radius=22)
    line(d,[(105,230),(279,230)],width=16)
    d.ellipse((245,246,269,270),fill=GREEN)
save('disk',disk)

def idle(d):
    d.ellipse((108,108,276,276),outline=FG,width=22); d.ellipse((174,174,210,210),fill=GREEN)
save('idle',idle)

def folder(d):
    d.polygon([(72,140),(145,140),(168,112),(310,112),(326,272),(72,272)],fill=None,outline=FG)
    line(d,[(74,157),(318,157)],width=18)
save('folder',folder)

def external(d):
    box(d,(78,116,270,306),outline=FG,width=20,radius=20)
    line(d,[(190,82),(306,82),(306,198)],fill=BLUE,width=22)
    line(d,[(306,82),(176,212)],fill=BLUE,width=22)
save('open',external)

def refresh(d):
    d.arc((76,76,308,308),32,214,fill=FG,width=22); d.arc((76,76,308,308),212,394,fill=FG,width=22)
    d.polygon([(270,66),(326,90),(280,130)],fill=FG); d.polygon([(114,318),(58,294),(104,254)],fill=FG)
save('refresh',refresh)
save('reset',refresh)

def stop(d): box(d,(126,126,258,258),fill=FG,outline=FG,width=1,radius=12)
save('stop',stop)
def play(d): d.polygon([(132,92),(292,192),(132,292)],fill=FG)
save('play',play)
def nexti(d):
    d.polygon([(78,100),(200,192),(78,284)],fill=FG); d.polygon([(180,100),(302,192),(180,284)],fill=FG)
save('next',nexti)
def star(d):
    import math
    pts=[]
    for i in range(10):
        a=math.radians(-90+i*36); r=118 if i%2==0 else 50
        pts.append((192+math.cos(a)*r,192+math.sin(a)*r))
    d.polygon(pts,fill=YELLOW)
save('circle',star)

def qr(d):
    def marker(x,y):
        d.rectangle((x,y,x+88,y+88),outline=FG,width=16); d.rectangle((x+27,y+27,x+61,y+61),fill=FG)
    marker(62,62); marker(234,62); marker(62,234)
    for x,y in [(214,214),(258,214),(302,214),(214,258),(302,258),(258,302),(302,302)]: d.rectangle((x,y,x+26,y+26),fill=BLUE)
save('qr',qr)

def report(d):
    box(d,(100,62,284,322),outline=FG,width=20,radius=20)
    line(d,[(138,135),(246,135)],width=13); line(d,[(138,181),(246,181)],width=13); line(d,[(138,227),(230,227)],width=13)
    d.rectangle((138,265,160,287),fill=GREEN); line(d,[(176,276),(244,276)],width=12)
save('report',report)

def diagnostics(d):
    line(d,[(54,210),(105,210),(130,145),(162,275),(199,108),(232,244),(260,188),(330,188)],fill=BLUE,width=18)
save('diagnostics',diagnostics)

def browser(d):
    box(d,(70,90,314,294),outline=FG,width=20,radius=20); line(d,[(72,140),(312,140)],width=16)
    for x,c in [(100,RED),(132,YELLOW),(164,GREEN)]: d.ellipse((x-8,108,x+8,124),fill=c)
save('browser',browser)

def speaker(d):
    d.polygon([(78,166),(132,166),(214,104),(214,280),(132,218),(78,218)],fill=FG)
    d.arc((204,126,308,258),300,60,fill=BLUE,width=20)
save('monitor',speaker)

def chevron(d):
    line(d,[(120,152),(192,224),(264,152)],width=24)
save('dropdown',chevron)

def reveal(d):
    d.ellipse((58,118,326,266),outline=FG,width=20); d.ellipse((155,155,229,229),fill=BLUE)
save('reveal',reveal)


def plusi(d):
    line(d,[(192,96),(192,288)],fill=BLUE,width=22)
    line(d,[(96,192),(288,192)],fill=BLUE,width=22)
save('plus',plusi)

print(f'generated {len(list(OUT.glob("*.png")))} icons in {OUT}')
