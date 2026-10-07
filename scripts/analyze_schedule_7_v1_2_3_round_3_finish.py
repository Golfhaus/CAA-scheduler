"""Joint and buffered alternatives for the third unpublished utilization round."""
from analyze_schedule_7_v1_2_3_round_3 import *
OUT='config/proposals/schedule_7_v1_2_3_round_3_joint.json'

def trial(s,name,plans,changes=()):
    c=overlay(s,plans,changes);v,t=validate(s,c)
    result={'name':name,'plans':plans,'retimings':list(changes),'validation':v}
    if good(v):
        result['demand']=demand(s,t,{l['id'] for l in c['insertLegs']})
        result['reviewAudit']=audit(s,t)
        options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
        changed=[]
        for change in changes:
            old=s.legs[change['legId']];new=next(l for l in t['legs'] if l['id']==old['id'])
            before={tuple(r['legs']) for r in s.screen.connections[old['id']]}
            after={tuple(r['legs']) for r in records[old['id']]}
            changed.append({'flight':old['flight'],'route':old['route'],'origin':old['origin'],'destination':old['destination'],
                'oldDeparture':old['departure'],'oldArrival':old['arrival'],'newDeparture':new['departure'],'newArrival':new['arrival'],
                'oldTotalOpportunity':sum(s.screen.loads[old['id']].values()),'newTotalOpportunity':sum(loads[old['id']].values()),
                'oldConnectingOpportunity':sum(v for k,v in s.screen.loads[old['id']].items() if k!='local'),
                'newConnectingOpportunity':sum(v for k,v in loads[old['id']].items() if k!='local'),
                'lostOldConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before)})
        result['retimingDemandAudit']=changed
    print('TRIAL',name,v['operatingErrors'],v['gates'],('lost '+str(len(result['reviewAudit']['marketsLosingAllConnections'])) if 'reviewAudit' in result else ''),flush=True)
    return result,c,t

def main():
    s=HoldSearch(read_json(ROOT/BASE));r={'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'status':'proposed; unpublished','trials':[]}
    old=read_json(ROOT/OUT) if (ROOT/OUT).exists() and '--fresh' not in sys.argv else {}
    assert not old or old['baseSha256']==r['baseSha256']
    def legs(route,a,b,out,back,fleet):return {'route':route,'legs':[s.leg(a,b,out,fleet),s.leg(b,a,back,fleet)]}
    def add(name,plans,changes=()):
        previous=next((x for x in old.get('trials',[]) if x['name']==name),None)
        x=previous or trial(s,name,plans,changes)[0];r['trials'].append(x);write_json(ROOT/OUT,r);return x
    day=legs(163,'DSM','DAY',270,467,'CRJ200')
    dal=legs(509,'SAT','DAL',300,411,'CRJ900')
    mci=legs(526,'DAL','MCI',306,433,'CRJ900')
    add('526 unchanged originator, best morning MCI turn',[mci])
    add('526 buffered MCI turn, first flight +12 minutes',[legs(526,'DAL','MCI',298,435,'CRJ900')],retime(s,526,[12,0,0,0]))
    add('526 later MCI turn, first flight +10 minutes',[legs(526,'DAL','MCI',316,443,'CRJ900')],retime(s,526,[10,0,0,0]))
    add('163 buffered short MCI turn, preserve original 09:05 flight',[legs(163,'DSM','MCI',335,430,'CRJ200')])
    add('163 DAY turn with rounded originator',[day])
    add('509 buffered local DAL turn',[dal])
    # An early MCI turn then the original SAT chain: explicitly test the cascade.
    add('509 early MCI return, first two old flights +57/+3 minutes',
        [legs(509,'SAT','MCI',270,426,'CRJ900')],retime(s,509,[57,3,0,0,0]))
    add('Three turns, preserve all existing clocks',[mci,day,dal])
    add('Three turns with 526 first flight +10 minutes',
        [legs(526,'DAL','MCI',316,443,'CRJ900'),day,dal],retime(s,526,[10,0,0,0]))
    add('Three turns with 526 buffered +12-minute variant',
        [legs(526,'DAL','MCI',298,435,'CRJ900'),day,dal],retime(s,526,[12,0,0,0]))
    add('Shorter DSM–MCI alternative in the joint package',
        [mci,legs(163,'DSM','MCI',335,430,'CRJ200'),dal])
    screen=read_json(ROOT/REPORT)
    wide=next(x for x in screen['screens'] if x['name']=='163 consolidate idle time at JAX; three-leg advance')['selected'][0]
    add('Broader JAX–PIE rebuild with the recommended other turns',
        [legs(526,'DAL','MCI',298,435,'CRJ900'),dal]+wide['plans'],
        retime(s,526,[12,0,0,0])+wide['retimings'])
    add('Buffered DAL–MSY alternative with broader JAX–PIE and SAT–DAL',
        [legs(526,'DAL','MSY',292,426,'CRJ900'),dal]+wide['plans'],wide['retimings'])
    selected=add('Recommended: buffered 526 MCI and 509 DAL; retain 163',
        [legs(526,'DAL','MCI',298,435,'CRJ900'),dal],retime(s,526,[12,0,0,0]))
    assert good(selected['validation'])
    c=overlay(s,selected['plans'],selected['retimings'])
    c['id']='schedule-7-v1.2.3-round-3-proposal'
    c['schedule'].update(id='schedule_7_v1_2_3_round_3_proposed',version='1.2.3',label='Schedule 7 v1.2.3 round 3 proposed; unpublished')
    c['approval']={'status':'proposed; not yet approved for implementation','userInstruction':'Perform the same action for routes 526, 163, and 509; retaining current flying is acceptable where useful extensions do not develop.','publication':'Reserved to user decision','scope':'Morning DAL–MCI on 526; Flight 1206 +12 minutes; SAT–DAL on 509; retain 163. Full accepted rounds 1/2, including 305, form the base.'}
    v,t=validate(s,c);assert good(v)
    write_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_3.json',c)
    write_json(ROOT/'builds/schedule_7_v1_2_3_round_3/canonical_schedule.json',t)
    optional=next(x for x in r['trials'] if x['name']=='Three turns with 526 buffered +12-minute variant')
    oc=overlay(s,optional['plans'],optional['retimings'])
    oc['id']='schedule-7-v1.2.3-round-3-with-optional-dsm-day'
    oc['approval']={'status':'optional; not selected','publication':'Reserved to user decision','scope':'Recommended 526/509 additions plus the legal but weaker DSM–DAY morning turn on 163.'}
    write_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_3_optional_day.json',oc)
    r['recommended']=selected
    r['recommendedFlightCount']=len(t['legs'])
    # Evaluate the hub-count-limited evening option without hiding the failure.
    evening=next(x for x in screen['screens'] if x['name'].startswith('163 JAN evening extension'))
    blocked=evening['rejected'][0]
    bc=overlay(s,[blocked['plan']]);bv,bt=validate(s,bc)
    r['janBhmConditional']={'plan':blocked['plan'],'validation':bv,
        'demand':demand(s,bt,{l['id'] for l in bc['insertLegs']}),
        'condition':'Additional BHM hub connection exceeds JAN two-hub envelope. Standing hub-count exceptions exist, but this option is not selected or overridden.'}
    write_json(ROOT/OUT,r)
    print('SAVED: recommended four-flight round; 163 retained; unpublished',flush=True)

if __name__=='__main__':main()
