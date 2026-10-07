"""Validate and preserve jointly usable evening recommendations and options."""
from analyze_schedule_7_v1_2_3_round_4_finish import *
OUT='config/proposals/schedule_7_v1_2_3_round_4_package.json'

def main():
    s=HoldSearch(read_json(ROOT/BASE))
    enum=s.screen.enumerate;last={}
    def cached(legs):
        key=tuple((l['id'],l['departureMinute'],l['arrivalMinute']) for l in legs)
        if last.get('key')!=key:last.clear();last.update(key=key,options=enum(legs))
        return last['options']
    s.screen.enumerate=cached
    r={'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'status':'proposed; new extensions not implemented','trials':[]}
    old=read_json(ROOT/OUT) if (ROOT/OUT).exists() and '--fresh' not in sys.argv else {}
    assert not old or old['baseSha256']==r['baseSha256']
    def loop(route,a,b,out,back,fleet):return {'route':route,'city':b,'legs':[s.leg(a,b,out,fleet),s.leg(b,a,back,fleet)]}
    def add(name,plans,changes=()):
        x=next((z for z in old.get('trials',[]) if z['name']==name),None)
        x=x or trial(s,name,plans,changes)[0]
        r['trials'].append(x);write_json(ROOT/OUT,r);return x
    phf=loop(114,'ROA','PHF',1170,1305,'CRJ200')
    day=loop(169,'FWA','DAY',1225,1315,'CRJ200')
    mci=loop(350,'ELP','MCI',1107,1353,'CRJ700')
    add('114 PHF with four-minute advances to improve ROA ground margin',[phf],retime(s,114,[0,0,0,0,-4,-4]))
    offset=s.leg('FWA','PHF',0,'CRJ200')['arrivalMinute']
    add('169 late PHF alternative',[loop(169,'FWA','PHF',1292-offset,1332,'CRJ200')])
    out=s.leg('FWA','BHM',1260,'CRJ200')
    add('169 latest permissible FWA departure to BHM',[loop(169,'FWA','BHM',1260,out['arrivalMinute']+50,'CRJ200')])
    selected=add('Recommended 114 PHF and 169 DAY; retain 340, 327, 350',[phf,day])
    optional=add('Recommended 114/169 plus optional 350 late MCI',[phf,day,mci])
    for x,path,tag in [(selected,'config/proposals/schedule_7_v1_2_3_round_4.json','recommended'),(optional,'config/proposals/schedule_7_v1_2_3_round_4_optional_mci.json','optional 350 MCI')]:
        assert good(x['validation']),x['validation']
        c=overlay(s,x['plans'],x['retimings']);c['operatingOverrides']=x['operatingOverrides']
        c['id']='schedule-7-v1.2.3-round-4-'+tag.replace(' ','-')
        c['schedule'].update(id='schedule_7_v1_2_3_round_4_'+tag.replace(' ','_'),label='Schedule 7 v1.2.3 evening extensions '+tag+'; unpublished')
        c['approval']={'status':'proposed; not yet approved for implementation','publication':'Reserved to user decision','userInstruction':'Look into extending routes 340, 350, 114, 169, and 327 past their current early terminating points.','scope':tag+'; existing 340 and 327 DAY extensions retained; no existing clocks changed.'}
        v,t=raw_validate(s,c);assert good(v)
        write_json(ROOT/path,c)
        x['flightCount']=len(t['legs']);x['addedBlockMinutes']=sum(s.screen.utc(l)[2] for p in x['plans'] for l in p['legs'])
        x['scheduleId']=c['schedule']['id']
        x['overnightTransitions']=[a for a in __import__('caa_scheduler.operating_validation',fromlist=['validate_overnight_turns']).validate_overnight_turns(t)['metrics']['transitions'] if a['fromRoute'] in {114,169,350}]
    r['recommended']=selected;r['optional350']=optional
    write_json(ROOT/OUT,r)
    print('SAVED jointly validated proposed packages; unpublished',flush=True)

if __name__=='__main__':main()
