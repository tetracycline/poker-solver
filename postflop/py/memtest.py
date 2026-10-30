import json,subprocess,sys
from job import make_job, DRV
base=make_job('BTN_BB','gto','Ks7d2c','/tmp/x.json'); base.update(turn_raise='a', river_raise='a')
tests={
 'mid': {},
 'nodonk_flop': dict(flop_oop=''),
 'nodonk_all': dict(flop_oop='', turn_donk='', river_donk=''),
 'v1': dict(flop_oop='', turn_donk='', river_donk='', river_ip='50%,100%', river_oop='50%,100%'),
 'v2': dict(flop_oop='', turn_donk='', river_donk='', turn_ip='66%', turn_oop='66%', river_ip='50%,100%', river_oop='50%,100%'),
 'v3': dict(flop_oop='', turn_donk='', river_donk='', turn_ip='66%', turn_oop='66%', river_ip='75%', river_oop='75%'),
 'v4': dict(flop_oop='', turn_donk='', river_donk='', river_ip='75%,a', river_oop='75%,a'),
 'v5': dict(flop_oop='', turn_donk='', river_donk='', flop_raise='a', river_ip='75%,a', river_oop='75%,a'),
}
for k,v in tests.items():
    j=dict(base); j.update(v); json.dump(j,open('/tmp/j.json','w'))
    p=subprocess.run([DRV,'/tmp/j.json'],capture_output=True,text=True,env={'MEMONLY':'1'}); print(k,p.stderr.strip()[-200:])
