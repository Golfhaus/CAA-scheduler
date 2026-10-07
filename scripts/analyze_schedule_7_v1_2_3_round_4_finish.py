"""Evening buffered, hub-count and rebuilt alternatives on the accepted draft."""
from analyze_schedule_7_v1_2_3_round_4 import *
from caa_scheduler.operating_validation import validate_operating_rules
OUT='config/proposals/schedule_7_v1_2_3_round_4_joint.json'
raw_validate=validate

def validate(s,c):
    # Standing user authorization permits justified additional hubs, but never
    # waives gates, spacing, curfews, minimum service or bank alignment.
    t=apply_optimization_overlay(s.base,c)
    op=validate_operating_rules(t)
    new=[]
    for check in op['checks']:
        if check['id']!='tiered_service_minimums':continue
        for f in check['findings']:
            e=f['evidence']
            if f.get('override') or len(e.get('connectedHubs',[]))<=e.get('hubCountCap',999):continue
            if e.get('totalFlights',0)<e.get('minimumFlights',999) or e.get('hubOrFocusFlights',0)<e.get('minimumFlights',999):continue
            new.append({'checkId':check['id'],'findingId':f['id'],
                'reason':'Standing user instruction permits an additional hub when useful to the initiative. Conditional evening extension analysis; publication remains reserved to user.'})
    c.setdefault('operatingOverrides',[]).extend(new)
    return raw_validate(s,c)

def trial(s,name,plans,changes=(),banks=()):
    c=overlay(s,plans,changes,banks);v,t=validate(s,c)
    x={'name':name,'plans':plans,'retimings':list(changes),'banks':list(banks),'operatingOverrides':c['operatingOverrides'],'validation':v}
    if good(v):
        x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,t)
        options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
        x['changedFlightConnections']=[]
        for change in changes:
            l=s.legs[change['legId']]
            before={tuple(r['legs']) for r in s.screen.connections[l['id']]}
            after={tuple(r['legs']) for r in records[l['id']]}
            x['changedFlightConnections'].append({'flight':l['flight'],'oldTotalOpportunity':sum(s.screen.loads[l['id']].values()),'newTotalOpportunity':sum(loads[l['id']].values()),'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before)})
    print('TRIAL',name,v['operatingErrors'],v['gates'],[(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x.get('demand',{}).get('flights',[])],flush=True)
    return x,c,t

def main():
    s=HoldSearch(read_json(ROOT/BASE));screen=read_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_4_screen.json')
    # Demand, availability and retimed-flight audits use the same complete
    # candidate. Reuse that enumeration once; retain only the last network.
    enumerate_network=s.screen.enumerate
    last={}
    def cached_enumerate(legs):
        key=tuple((l['id'],l['origin'],l['destination'],l['departureMinute'],l['arrivalMinute']) for l in legs)
        if last.get('key')!=key:
            last.clear();last.update(key=key,options=enumerate_network(legs))
        return last['options']
    s.screen.enumerate=cached_enumerate
    r={'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'status':'proposals only; unpublished','trials':[],'rebuiltScreens':[]}
    old=read_json(ROOT/OUT) if (ROOT/OUT).exists() and '--fresh' not in sys.argv else {}
    assert not old or old['baseSha256']==r['baseSha256']
    def add(name,plans,changes=(),banks=()):
        x=next((z for z in old.get('trials',[]) if z['name']==name),None)
        x=x or trial(s,name,plans,changes,banks)[0]
        r['trials'].append(x);write_json(ROOT/OUT,r);return x
    def loop(route,a,b,out,back,fleet):return {'route':route,'city':b,'legs':[s.leg(a,b,out,fleet),s.leg(b,a,back,fleet)]}
    # Evaluate high-ranked opportunities previously blocked only by hub-count,
    # and other physical failures without waiving those constraints.
    for item in screen['screens']:
        seen=set()
        for rejected in item.get('rejected',[]):
            p=rejected['plan']
            if p['city'] in seen or p['city'] not in s.screen.hubs:continue
            seen.add(p['city']);add(f"{item['route']} {p['city']} additional-hub/physical sensitivity",[p])
    add('350 buffered late MCI turn',[loop(350,'ELP','MCI',1107,1353,'CRJ700')])
    add('114 buffered late JAX turn',[loop(114,'ROA','JAX',1175,1319,'CRJ200')])
    add('169 buffered DAY mini-bank turn',[loop(169,'FWA','DAY',1225,1315,'CRJ200')])
    # Earlier arrivals at a terminal hub can require advancing two or more old
    # flights; quantify all connection damage, rather than assuming an advance
    # preserves the old itinerary availability.
    previous.validate=validate
    for name,route,city,fleet,start,end,changes,banks in [
        ('114 advance last AVL/JAX flights 30 minutes',114,'ROA','CRJ200',1139,1500,retime(s,114,[0,0,0,0,-30,-30]),[]),
        ('169 rebuild into two earlier banks',169,'FWA','CRJ200',1005,1500,retime(s,169,[-11,-135,-195,-195,-195,-165]),[]),
    ]:
        x=next((z for z in old.get('rebuiltScreens',[]) if z['name']==name),None)
        x=x or previous.shortlist(s,name,route,city,fleet,start,end,sorted(s.screen.hubs),changes=changes,limit=3)
        r['rebuiltScreens'].append(x);write_json(ROOT/OUT,r)
        for selected in x['selected'][:2]:add(name+' '+selected['plans'][0]['city'],selected['plans'],changes,banks)
    # ELP's two close daytime MCI departures leave no ordinary earlier bank.
    # This explicit alternative adds a 40-minute mini-bank and advances the
    # second existing turn, preserving every original market/fleet assignment.
    add('350 earlier second turn plus new MCI mini-bank',
        [loop(350,'ELP','MCI',1003,1239,'CRJ700')],retime(s,350,[0,0,-79,-98]),
        [{'id':'MCI-M14','hub':'MCI','startMinute':845,'endMinute':885}])
    write_json(ROOT/OUT,r)
    print('SAVED evening alternatives; new flying remains proposed',flush=True)

if __name__=='__main__':main()
