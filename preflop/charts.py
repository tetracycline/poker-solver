import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
import os
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc']:
    if os.path.exists(f): fm.fontManager.addfont(f); plt.rcParams['font.family']=fm.FontProperties(fname=f).get_name(); break
import os
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')+'/'
G=json.load(open(D+'preflop/gto_rake.json')); E=json.load(open(D+'preflop/exploit_rake.json'))
names=G['names']
COL={'fold':'#2a3a30','open':'#3ecf7a','call':'#3b82d6','3bet':'#e0574f','4bet':'#e0574f','jam':'#9b3ad6'}
ZH={'fold':'棄牌','open':'開池','call':'跟注','3bet':'3-bet','4bet':'4-bet','jam':'全下'}
def comb(n): return 6 if len(n)==2 else (4 if n[2]=='s' else 12)
def freq(acts,strat,reach):
    w=[0]*len(acts)
    for i,n in enumerate(names):
        for a in range(len(acts)): w[a]+=comb(n)*strat[i][a]*reach[i]
    t=sum(w); return [x/t*100 for x in w]
def grid(ax,acts,strat,title,reach):
    mx=max(reach)
    ax.set_xlim(0,13); ax.set_ylim(13,0); ax.axis('off'); ax.set_facecolor('#0f1a14')
    for i,n in enumerate(names):
        r,c=divmod(i,13); x=c
        h=reach[i]/mx
        if h<0.03: h=0
        for a in range(len(acts)):
            wd=strat[i][a]
            if wd>0.001: ax.add_patch(Rectangle((x,r+1-h),wd,h,color=COL[acts[a]],lw=0)); x+=wd
        ax.add_patch(Rectangle((c,r),1,1,fill=False,ec='#0f1a14',lw=.8))
        ax.text(c+.5,r+.55,n,ha='center',va='center',fontsize=6.3,color='#e8f5ec')
    f=freq(acts,strat,reach)
    ax.set_title(title+'\n'+'  '.join(f'{ZH[a]} {v:.1f}%' for a,v in zip(acts,f)),color='#e8f5ec',fontsize=9)
SPOTS=[('UTGrfi','UTG 開池'),('HJrfi','HJ 開池'),('COrfi','CO 開池'),('BTNrfi','BTN 開池'),('SBrfi','SB 開池（對 BB）'),
 ('UTGopen>BB','BB vs UTG 開池'),('HJopen>BB','BB vs HJ 開池'),('COopen>BB','BB vs CO 開池'),('BTNopen>BB','BB vs BTN 開池'),('SBopen>BB','BB vs SB 開池'),
 ('SBopen>BB3b','SB 開池後 vs BB 3-bet'),('BTNopen>SB','SB vs BTN 開池（3-bet or fold）'),('COopen>BTN','BTN vs CO 開池'),('UTGopen>BTN','BTN vs UTG 開池'),
 ('BTNopen>BB3b','BTN 開池後 vs BB 3-bet'),('COopen>BTN3b','CO 開池後 vs BTN 3-bet'),('UTGopen>BB3b','UTG 開池後 vs BB 3-bet'),
 ('BTNopen>BB3b>4b','BB 3-bet 後 vs BTN 4-bet'),('COopen>BTN3b>4b','BTN 3-bet 後 vs CO 4-bet'),('BTNopen>BB3b>4b>jam','BTN 4-bet 後 vs BB 全下')]
out=[]
for k,t in SPOTS:
    nd=G['nodes'][k]; seat=nd['seat']; ex=E['heroes'].get(seat,{}).get('nodes',{}).get(k)
    fig,axs=plt.subplots(1,2,figsize=(10,5.6),facecolor='#0f1a14')
    grid(axs[0],nd['acts'],nd['strat'],t+' — GTO（含抽水）',nd['reach'])
    if ex: grid(axs[1],ex['acts'],ex['strat'],t+' — 剝削 NL2 池',ex.get('reach',nd['reach']))
    else: axs[1].axis('off'); axs[1].text(.5,.5,'（此節點無剝削解）',color='#9fb8a8',ha='center',transform=axs[1].transAxes)
    fn='pf_'+k.replace('>','_')+'.png'; plt.tight_layout(); fig.savefig(D+'report_img/'+fn,dpi=110,facecolor='#0f1a14'); plt.close(fig)
    out.append((k,t,fn,freq(nd['acts'],nd['strat'],nd['reach']),nd['acts'],(freq(ex['acts'],ex['strat'],ex.get('reach',nd['reach'])) if ex else None)))
json.dump(out,open(D+'report_img/index.json','w'),ensure_ascii=False,indent=0)
for o in out: print(o[0], o[4], [round(x,1) for x in o[3]], o[5] and [round(x,1) for x in o[5]])
