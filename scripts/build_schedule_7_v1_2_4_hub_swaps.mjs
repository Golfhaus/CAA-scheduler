import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

// Run a copy from a conversation-specific temporary directory linked to the
// primary runtime's node_modules. First argument is the repository root.
const root = process.argv[2];
if (!root) throw new Error('Repository root is required');
const review = JSON.parse(await fs.readFile(path.join(root, 'config/proposals/schedule_7_v1_2_4_hub_swaps_review.json'), 'utf8'));
const base = JSON.parse(await fs.readFile(path.join(root, review.baseCanonical), 'utf8'));
const all = [...review.pairs, ...(review.coordinatedCandidates ?? [])];
const validated = all.filter(q => q.overlay);
const dir = path.join(root, 'outputs/schedule_7_v1_2_4_hub_swaps');
const wb = Workbook.create();
for (const name of ['Terminators','Pairs','Flights','Line Plans']) wb.worksheets.add(name);
const columns = n => { let s=''; while(n) { n--; s=String.fromCharCode(65+n%26)+s; n=Math.floor(n/26); } return s; };
const minute = n => n == null ? 'n.a.' : (n % 1440) / 1440;
const fmt = n => `${String(Math.floor((n%1440)/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}${n>=1440?' +1':''}`;
const zone = hub => hub === 'MCI' ? 'CT' : 'ET';
const bankText = q => (q.proposedBanks ?? []).map(b => `${b.hub} ${fmt(b.startMinute)}–${b.endMinute===1440?'24:00':fmt(b.endMinute)}`).join('; ');
const groupText = o => Object.entries(o ?? {}).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${k} ${v.toFixed(1)}`).join(', ');
const routes = new Map();
for (const l of base.legs) { if(!routes.has(l.route)) routes.set(l.route,[]); routes.get(l.route).push(l); }
for (const ls of routes.values()) ls.sort((a,b)=>a.sequenceWithinRoute-b.sequenceWithinRoute);
const inventory = new Map(review.allHubTerminators.map(x=>[x.route,x]));
const flightRows = [], planRows = [], references = new Map();
for (const q of validated) {
  const cycles = q.lineProof.cycles;
  const next = new Map();
  for (const c of cycles) c.forEach((r,i)=>next.set(r,c[(i+1)%c.length]));
  const changed = new Map(q.routes.map((r,i)=>[r,q.selectedTiming.legs[i]]));
  for (const [i,f] of q.demand.flights.entries()) {
    const old = inventory.get(q.routes[i]);
    const peer = next.get(old.route);
    const originator = routes.get(peer)[0];
    const evidence = q.section26Evidence.pairs.find(x=>x.legId===f.id);
    references.set(`${q.id}:${i}`, flightRows.length + 9);
    flightRows.push([q.id,old.route,f.fleet,f.flight,f.origin,f.destination,minute(f.departureMinute),zone(f.origin),
      minute(f.arrivalMinute),Math.floor(f.arrivalMinute/1440),zone(f.destination),minute(old.finishMinute),
      f.departureMinute-old.finishMinute,peer,minute(originator.departureMinute),q.selectedTiming.rons[i],
      evidence.frequencyBefore,evidence.frequencyAfter,evidence.minimumCyclicGapMinutes,f.local,f.connecting,null,
      f.inboundFeeders.length,f.outboundConnections.length,groupText(f.originGroups),groupText(f.destinationGroups),
      f.route,f.line,f.day,f.topMarkets.map(x=>`${x.origin}–${x.destination} ${x.opportunity.toFixed(1)}`).join(', '),
      f.inboundFeeders.map(x=>`${x.flight} ${x.origin}`).join(', '),f.outboundConnections.map(x=>`${x.flight} ${x.destination}`).join(', ')]);
  }
  for (const x of q.routeReassignments) {
    const c = cycles.find(c=>c.includes(x.sourceRoute)), i = c.indexOf(x.sourceRoute), successor = next.get(x.sourceRoute);
    const last = changed.get(x.sourceRoute) ?? routes.get(x.sourceRoute).at(-1);
    const first = routes.get(successor)[0];
    // Same-station handoff: local clocks suffice. Unwrap original post-midnight
    // endpoints exactly as the line proof did, using the complete route sequence.
    let finish = last.arrivalMinute;
    if (!changed.has(x.sourceRoute)) {
      let offset=0, previous=-Infinity;
      for(const l of routes.get(x.sourceRoute)) { if(l.departureMinute+offset<previous) offset+=1440; previous=l.arrivalMinute+offset; }
      finish=previous;
    }
    const ron = 1440+first.departureMinute-finish;
    if(ron<40) throw new Error(`Invalid overnight ${q.id} ${x.sourceRoute}`);
    planRows.push([q.id,q.fleet,x.sourceRoute,x.expectedLine,x.expectedDay,x.targetRoute,x.line,x.day,
      c.length,successor,last.destination,ron,q.maintenance[x.line].maximumConsecutiveNonTargetRons,
      q.maintenance[x.line].targetRons.map(t=>`${t.city} day ${t.day}`).join(', ')]);
  }
}
const termRows = review.eligible.map(x=>{
  const z=x.review, opts=[...z.validatedIndividualOptions,...z.validatedCoordinatedOptions];
  const status=z.validatedCoordinatedOptions.length?'Conditional coordinated plan':z.validatedIndividualOptions.length?'Conditional individual options':z.timingPairs?'No line cover proved':'No reciprocal timing';
  return [x.route,x.fleet,x.line,x.day,x.legs.at(-1).flight,x.legs.at(-1).origin,x.terminator,minute(x.finishMinute),
    x.nextOriginator.route,minute(x.nextOriginator.departureMinute),status,opts.join(', ')||'n.a.',z.screenedPairs,z.timingPairs];
});
const pairRows = all.map(q=>{
  const proof=q.lineProof, timing=q.selectedTiming, d=q.directions;
  const rejected=d?.map(x=>`${x.origin}–${x.destination}: ${Object.keys(x.rejectCounts).join(', ')||'timing available'}`).join('; ')||'';
  return [q.id,q.peerPairs?'Coordinated':'Individual',q.fleet,q.routes.join('/'),q.hubs.join('/'),timing?'Timing available':'No reciprocal timing',
    (q.strictTimingsEachWay?.every(n=>n>0) ?? false)?'Yes':'No',proof?.status==='proved'?'Proved':proof?'Not proved':'n.a.',
    q.overlay?'Conditional pass':'Not evaluated',proof?.poolLines?.join('/')||'n.a.',proof?.cycleLengths?.join('/')||'n.a.',
    q.connectionAudit?.marketsWithFasterBestItinerary??'n.a.',null,null,
    d?.[0]?.existingFrequency??'n.a.',d?.[1]?.existingFrequency??'n.a.',timing?Math.min(...timing.rons):'n.a.',
    bankText(q)||'n.a.', timing?timing.legs.map(l=>`${l.origin}–${l.destination} ${fmt(l.departureMinute)}–${fmt(l.arrivalMinute)}`).join('; '):'n.a.',
    timing?.missingBanks.map(x=>`${x.hub} ${x.operation} ${x.clock}`).join('; ')||'n.a.',rejected,
    q.peerPairs?'AD only: 44 two-pair combinations':'Paired lines plus up to two additional same-fleet lines'];
});

function sheet(name,title,note,headers,rows,widths,previewEnd='I') {
  const sh=wb.worksheets.getItem(name), end=columns(headers.length), bottom=rows.length+8;
  sh.showGridLines=false;
  sh.getRange(`A1:${end}${bottom}`).format={font:{name:'Arial',size:10},verticalAlignment:'center',rowHeight:42,wrapText:false};
  sh.getRange(`A1:${end}1`).format.rowHeight=12;
  sh.mergeCells(`A2:${previewEnd}2`); sh.getRange('A2').values=[[title]];
  sh.getRange(`A2:${previewEnd}2`).format={font:{name:'Arial',size:14,bold:true,color:'#17324D'},rowHeight:28};
  sh.mergeCells(`A3:${previewEnd}4`); sh.getRange('A3').values=[[note]];
  sh.getRange(`A3:${previewEnd}4`).format={wrapText:true,font:{name:'Arial',size:10,color:'#475569'}};
  sh.getRange(`A7:${end}7`).format.rowHeight=12;
  sh.getRange(`A8:${end}8`).values=[headers];
  sh.getRange(`A9:${end}${bottom}`).values=rows;
  const table=sh.tables.add(`A8:${end}${bottom}`,true,`${name.replaceAll(' ','')}Data`);
  table.showFilterButton=true;
  sh.getRange(`A8:${end}8`).format={fill:'#17324D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:44};
  rows.forEach((r,i)=>{if(i%2===1)sh.getRange(`A${i+9}:${end}${i+9}`).format.fill='#F1F5F9';});
  widths.forEach((w,i)=>sh.getRange(`${columns(i+1)}8:${columns(i+1)}${bottom}`).format.columnWidth=w);
  sh.freezePanes.freezeRows(8);sh.freezePanes.freezeColumns(2);
  return sh;
}
const terminators=sheet('Terminators','Hub terminators, 19:30–22:15',
  'Accepted v1.2.4 draft. All options require added banks and compliant line rebuilding. Current banks permit no reciprocal exchange. Times are local. MCI is CT; other hubs are ET.',
  ['Route','Fleet','Line','Day','Terminator flight #','From','Hub','Arrival','Current next route','Next departure','Review result','Validated options','Pairs screened','Timing pairs'],
  termRows,[9,12,8,7,13,9,9,11,13,12,35,43,12,11]);
terminators.getRange('K9:L37').format.wrapText=true;
terminators.getRange('H9:H37').setNumberFormat('hh:mm');terminators.getRange('J9:J37').setNumberFormat('hh:mm');
terminators.mergeCells('A5:B5');terminators.getRange('A5').values=[['Terminators']];terminators.getRange('C5').formulas=[['=COUNTA(A9:A37)']];
terminators.mergeCells('D5:F5');terminators.getRange('D5').values=[['Pairs screened']];terminators.getRange('G5').formulas=[[`=COUNTIFS('Pairs'!B9:B106,"Individual")`]];
terminators.mergeCells('H5:J5');terminators.getRange('H5').values=[['Current-bank pairs']];terminators.getRange('K5').formulas=[[`=COUNTIFS('Pairs'!B9:B106,"Individual",'Pairs'!G9:G106,"Yes")`]];
terminators.getRange('A5:L6').format.rowHeight=22;

const pairs=sheet('Pairs','Reciprocal pair screening',
  '97 individual pairs and one coordinated plan. Conditional passes include proposed bank additions. Unproved line covers are not global impossibility. Alternatives overlap and cannot be combined without joint validation.',
  ['Option','Scope','Fleet','Routes','Hubs','Timing','Fits current banks','Line cover','Full validation','Line pool','New lengths (days)','Faster markets',
   'Direction 1 opportunity','Direction 2 opportunity','Existing frequency 1','Existing frequency 2','Shortest RON (min)',
   'Proposed bank windows','Added flights (local)','Missing bank touches','Timing rejection evidence','Line search scope'],
  pairRows,[27,14,12,15,15,25,14,15,21,18,18,13,16,16,15,15,15,58,70,70,72,50]);
pairs.getRange('R9:V106').format.wrapText=true;
pairs.getRange('M9:N106').setNumberFormat('0.0');
pairs.getRange('A5').values=[['Individual passes']];pairs.getRange('B5').formulas=[['=COUNTIFS(B9:B106,"Individual",I9:I106,"Conditional pass")']];
pairs.getRange('D5').values=[['Joint plans passing']];pairs.getRange('E5').formulas=[['=COUNTIFS(B9:B106,"Coordinated",I9:I106,"Conditional pass")']];
pairs.getRange('A5:I6').format.rowHeight=22;

const flights=sheet('Flights','Added flights in validated scenarios',
  'Opportunity separates local O-D and connecting demand. It is seat-uncapped and is not predicted passengers or incremental traffic. +1 is the next calendar day. Proposed flight numbers repeat between mutually exclusive scenarios.',
  ['Option','Original route','Fleet','Proposed flight #','Origin','Destination','Departure','Dep zone','Arrival','Arrival +days','Arr zone',
   'Current term arrival','Turn (min)','Next original route','Next departure','RON (min)','Existing frequency','New frequency','Min pair gap (min)',
   'Local opportunity','Connecting opportunity','Total opportunity','Feeder flights','Onward flights','Origin groups','Destination groups',
   'Proposed route','New line','New day','Top connecting markets','Feeder flight # and origin','Onward flight # and destination'],
  flightRows,[27,12,12,14,10,12,12,9,12,12,9,13,11,13,12,11,13,12,13,14,16,15,12,12,65,50,13,10,9,100,100,75]);
const fb=flightRows.length+8;
for(const c of ['G','I','L','O'])flights.getRange(`${c}9:${c}${fb}`).setNumberFormat('hh:mm');
flights.getRange(`T9:V${fb}`).setNumberFormat('0.0');flights.getRange(`Y9:AF${fb}`).format.wrapText=true;
flights.getRange(`V9:V${fb}`).formulas=flightRows.map((r,i)=>[`=SUM(T${i+9}:U${i+9})`]);
flights.getRange('A5').values=[['Scenario flights']];flights.getRange('B5').formulas=[[`=COUNTA(D9:D${fb})`]];
flights.getRange('D5:I6').merge();flights.getRange('D5').values=[['Do not sum opportunity across alternative scenarios.']];
flights.getRange('A5:I6').format.rowHeight=22;
for(const [i,q] of all.entries())for(const j of [0,1]){
  const r=references.get(`${q.id}:${j}`);
  pairs.getRange(`${j===0?'M':'N'}${i+9}`).formulas=[[r?`='Flights'!V${r}`:'="n.a."']];
}

const plans=sheet('Line Plans','Complete line reconstruction',
  'Original route days remain intact. The table maps every day in each altered pool to its proposed route, line and day, and shows its next original route. All reconstructed lines contain 9–12 days.',
  ['Option','Fleet','Original route','Original line','Original day','Proposed route','New line','New day','Line length','Next original route','RON city',
   'RON (min)','Max non-MX RON run','Maintenance RONs'],planRows,[27,12,13,12,12,13,10,10,11,15,11,12,17,70],'I');
plans.getRange(`N9:N${planRows.length+8}`).format.wrapText=true;
plans.mergeCells('A5:I6');plans.getRange('A5').values=[[`Source: CAA schedule 7 v1.2.4 accepted draft, pinned O-D and CAA Build Instructions v2.0 §§2.6, 2.8. https://github.com/Golfhaus/CAA-scheduler/tree/codex/v1.2.4-utilization. Snapshot SHA-256: ${review.baseSha256}`]];
plans.getRange('A5:I6').format={rowHeight:28,wrapText:true,font:{name:'Arial',size:9,color:'#475569'}};

if(termRows.length!==29||pairRows.length!==98||flightRows.length!==38)throw new Error('Incomplete review');
wb.recalculate();
console.log(JSON.stringify({terminatorCount:terminators.getRange('C5').values,screenedPairCount:terminators.getRange('G5').values,currentBankCount:terminators.getRange('K5').values,individualPassCount:pairs.getRange('B5').values,jointPassCount:pairs.getRange('E5').values}));
console.log((await wb.inspect({kind:'region',sheetId:'Flights',range:'T9:V10',maxChars:1500,tableMaxRows:2,tableMaxCols:3})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Final formula error scan'})).ndjson);
for (const sh of ['Terminators','Pairs','Flights','Line Plans']) {
  const png=await wb.render({sheetName:sh,range:sh==='Terminators'?'A1:L14':'A1:I14',scale:1.3});
  await fs.writeFile(`/tmp/caa-hub-swaps-4476e574895b/${sh.replaceAll(' ','_')}.png`,new Uint8Array(await png.arrayBuffer()));
}
await fs.mkdir(dir,{recursive:true});
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(dir,'Hub_Terminator_Swaps.xlsx'));
console.log(JSON.stringify({terminators:termRows.length,screenedPairs:review.pairs.length,conditionalPlans:validated.length,scenarioFlights:flightRows.length,lineDays:planRows.length,output:path.join(dir,'Hub_Terminator_Swaps.xlsx')}));
