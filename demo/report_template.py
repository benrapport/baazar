"""HTML report template for simulation results."""

import json
from pathlib import Path


def generate_html(report: dict, path: Path):
    """Generate widescreen dashboard HTML report with advanced visualizations."""

    mock_badge = ' <span class="mock">MOCK DATA</span>' if report['metadata'].get('is_mock') else ''
    report_json = json.dumps(report)

    # Use a plain template with simple replacements — no f-strings near JS
    html = _HTML_TEMPLATE.replace('__REPORT_JSON__', report_json)
    html = html.replace('__MOCK_BADGE__', mock_badge)
    html = html.replace('__TIMESTAMP__', report['metadata']['timestamp'])
    html = html.replace('__N_MARKETS__', str(report['metadata']['n_markets']))
    html = html.replace('__N_AGENTS__', str(report['metadata']['n_agents']))

    with open(path, "w") as f:
        f.write(html)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bazaar Exchange — Simulation Report</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0f;color:#e0e0e0;padding:12px 16px;font-size:13px}
h1{color:#ffd700;font-size:1.5em;display:inline}
.mock{background:#ff6f00;color:#fff;padding:2px 8px;border-radius:3px;font-size:.65em;vertical-align:middle}
.sub{color:#666;font-size:.8em;margin-left:12px}
.hdr{display:flex;align-items:baseline;gap:8px;margin-bottom:10px}
h2{color:#00bcd4;font-size:.95em;margin:0 0 6px;padding:4px 0;border-bottom:1px solid #222}
.note{color:#555;font-size:.72em;margin:-4px 0 4px}

/* Grid layouts */
.row{display:grid;gap:10px;margin-bottom:10px}
.r2{grid-template-columns:1fr 1fr}
.r3{grid-template-columns:1fr 1fr 1fr}
.r23{grid-template-columns:2fr 3fr}
.r32{grid-template-columns:3fr 2fr}
.box{background:#111118;border:1px solid #1e1e2e;border-radius:6px;padding:10px;overflow:hidden}

/* Stats strip */
.stats{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.st{background:#111118;border:1px solid #1e1e2e;border-radius:5px;padding:6px 12px;text-align:center;flex:1;min-width:90px}
.st .v{font-size:1.3em;font-weight:bold;color:#ffd700}
.st .l{font-size:.6em;color:#666;margin-top:1px}
.st .v.g{color:#4caf50}.st .v.r{color:#f44336}.st .v.b{color:#42a5f5}

/* Flow */
.flow{display:flex;align-items:center;justify-content:center;gap:6px;padding:8px;font-size:.85em}
.fb{background:#13131f;border:1px solid #282838;border-radius:6px;padding:8px 12px;text-align:center}
.fb .l{font-size:.6em;color:#666}.fb .v{font-size:1.1em;font-weight:bold;margin-top:2px}
.fa{color:#444;font-size:1.2em}

/* Bars */
.bar{display:flex;align-items:center;margin:2px 0}
.bl{width:140px;font-size:.7em;color:#888;text-align:right;padding-right:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}
.bf{height:14px;border-radius:2px;min-width:1px}.bv{font-size:.65em;color:#666;padding-left:6px;white-space:nowrap}

/* Tables */
table{width:100%;border-collapse:collapse;font-size:.75em}
th{background:#12121e;color:#666;text-align:left;padding:4px 6px;font-weight:normal;text-transform:uppercase;font-size:.65em;letter-spacing:.5px}
td{padding:3px 6px;border-bottom:1px solid #151520}
tr:hover{background:#151520}
.p{color:#4caf50}.n{color:#f44336}

/* Chips */
.tc{padding:2px 7px;border-radius:10px;font-size:.65em;font-weight:bold;display:inline-block}
.tc-penny{background:#1a1a1a;color:#777;border:1px solid #333}
.tc-budget{background:#0a1f0a;color:#4caf50;border:1px solid #2e7d32}
.tc-stress{background:#1f140a;color:#ff9800;border:1px solid #e65100}
.tc-mid{background:#1f1f0a;color:#ffeb3b;border:1px solid #f9a825}
.tc-premium{background:#1f0a1f;color:#e040fb;border:1px solid #7b1fa2}
.tc-creative{background:#0a1f1f;color:#26c6da;border:1px solid #00838f}

.wb{background:#2e7d32;color:#fff;padding:1px 6px;border-radius:8px;font-size:.7em}
.rb{background:#1a237e;color:#90caf9;padding:1px 6px;border-radius:8px;font-size:.7em}
.sc{padding:1px 5px;border-radius:2px;font-size:.65em;display:inline-block;margin:1px}
.sh{background:#1b5e20;color:#a5d6a7}.sm{background:#3a2e00;color:#ffe082}.sl{background:#3a0000;color:#ef9a9a}

/* Scatter plots */
.scat{position:relative;height:220px;background:#0f0f16;border:1px solid #1e1e2e;border-radius:4px;margin:0}
.scat-canvas{width:100%;height:100%;display:block;background:#0f0f16}
.dot{position:absolute;border-radius:50%;cursor:pointer;transition:all .15s}
.dot:hover{z-index:10;filter:drop-shadow(0 0 4px rgba(255,215,0,.6))}
.ax{position:absolute;color:#555;font-size:.55em;font-weight:normal}
.ax-x{bottom:-14px;white-space:nowrap}
.ax-y{right:100%;text-align:right;padding-right:4px;top:50%;transform:translateY(-50%)}
.pline{position:absolute;background:transparent;border:1px dashed #333}

/* Sparkline */
.spark{display:flex;gap:1px;align-items:flex-end;height:14px}
.sb{flex:1;min-width:2px;border-radius:1px}

/* Market grid */
.mg{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:6px}
.mc{background:#111118;border:1px solid #1e1e2e;border-radius:5px;padding:8px;font-size:.78em}
.mc .pr{color:#aaa;font-style:italic;font-size:.85em;margin:3px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mc .sr{display:flex;gap:3px;flex-wrap:wrap;margin-top:4px}

/* Collapsible */
details>summary{cursor:pointer;color:#00bcd4;font-size:.9em;padding:4px 0}
details>summary:hover{color:#4dd0e1}
</style>
</head>
<body>
<div class="hdr"><h1>BAZAAR EXCHANGE__MOCK_BADGE__</h1><span class="sub">__TIMESTAMP__ — __N_MARKETS__ markets, __N_AGENTS__ agents</span></div>

<div class="stats" id="stats"></div>
<div class="box" style="margin-bottom:10px"><div class="flow" id="flow"></div></div>

<div class="row r3">
  <div class="box"><h2>PARETO FRONTIER</h2><div class="note">Cost vs Quality efficiency</div><div class="scat" id="pareto"></div></div>
  <div class="box"><h2>SCORE VS WIN RATE</h2><div class="note">Quality's conversion to wins</div><div class="scat" id="scatter2"></div></div>
  <div class="box"><h2>REVISION IMPACT</h2><div class="note">Before → after scores</div><div class="scat" id="revplot"></div></div>
</div>

<div class="row r2">
  <div class="box">
    <h2>AGENT PnL LEADERBOARD</h2>
    <div id="pnl" style="margin-bottom:6px"></div>
    <div style="max-height:220px;overflow-y:auto"><table id="atbl"><thead><tr><th>#</th><th>Agent</th><th>Strat</th><th>W</th><th>L</th><th>W%</th><th>Avg</th><th>Trend</th><th>Costs</th><th>PnL</th></tr></thead><tbody></tbody></table></div>
  </div>
  <div>
    <div class="row r2" style="margin-bottom:10px">
      <div class="box"><h2>TIER BREAKDOWN</h2><div id="ttbl" style="max-height:160px;overflow-y:auto"></div></div>
      <div class="box"><h2>SCORE DISTRIBUTION</h2><div id="sdist" style="display:flex;flex-direction:column;gap:6px"></div></div>
    </div>
  </div>
</div>

<div class="row r1">
  <div class="box">
    <details open><summary>MARKET-BY-MARKET RESULTS (__N_MARKETS__ markets)</summary>
    <div class="mg" id="mlist" style="margin-top:6px"></div>
    </details>
  </div>
</div>

<script>
const D=__REPORT_JSON__;
const E=D.economics,S=D.markets.filter(function(m){return m.status==='settled'}),T=D.markets.filter(function(m){return m.status==='timeout'});
const A=Object.entries(D.agent_pnl).map(function(kv){var id=kv[0],a=kv[1];return Object.assign({id:id},a)}).sort(function(a,b){return b.pnl-a.pnl});
const TO=['penny','budget','stress','mid','premium','creative'];
const TC={penny:'#888',budget:'#4caf50',stress:'#ff9800',mid:'#ffeb3b',premium:'#e040fb',creative:'#26c6da'};
const avg=S.length?(S.reduce(function(s,m){return s+m.score},0)/S.length).toFixed(1):'—';

document.getElementById('stats').innerHTML=[
['Markets',D.metadata.n_markets,''],['Settled',S.length,'g'],['Timeouts',T.length,T.length?'r':''],
['Avg Score',avg+'/10',''],['Volume','$'+E.total_buyer_spend.toFixed(2),'g'],
['Agent Costs','$'+E.total_agent_costs.toFixed(2),'r'],['Fees','$'+E.exchange_fees.toFixed(2),'b'],
['Q.Gap','+'+E.avg_quality_gap.toFixed(1),'g'],['Revisions',E.total_revisions+'('+E.successful_revisions+'w)',''],
].map(function(kv){var l=kv[0],v=kv[1],c=kv[2];return '<div class="st"><div class="v '+c+'">'+v+'</div><div class="l">'+l+'</div></div>'}).join('');

const ap=Math.max(0,E.total_agent_revenue-E.total_agent_costs),al=Math.max(0,E.total_agent_costs-E.total_agent_revenue);
document.getElementById('flow').innerHTML='<div class="fb"><div class="l">BUYER</div><div class="v" style="color:#ffd700">$'+E.total_buyer_spend.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">FEE 1.5%</div><div class="v" style="color:#42a5f5">$'+E.exchange_fees.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">WINNERS</div><div class="v" style="color:#4caf50">$'+E.total_agent_revenue.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">API COSTS</div><div class="v" style="color:#f44336">$'+E.total_agent_costs.toFixed(2)+'</div></div><div class="fa">→</div><div class="fb"><div class="l">NET '+(ap>0?'PROFIT':'LOSS')+'</div><div class="v" style="color:'+(ap>0?'#4caf50':'#f44336')+'">$'+Math.abs(ap||al).toFixed(2)+'</div></div>';

function drawScatter(container,xLabel,yLabel,points){
  var w=container.offsetWidth-2,h=220;
  var svg='<svg width="100%" height="'+h+'" viewBox="0 0 '+w+' '+h+'" style="position:absolute;left:0;top:0">';
  var xs=points.map(function(p){return p.x}),ys=points.map(function(p){return p.y});
  var xmin=Math.min.apply(null,xs),xmax=Math.max.apply(null,xs),ymin=Math.min.apply(null,ys),ymax=Math.max.apply(null,ys);
  var px=function(x){return 40+(x-xmin)/(xmax-xmin||1)*0.85*w};
  var py=function(y){return h-40-(y-ymin)/(ymax-ymin||1)*0.8*h};
  svg+='<line x1="40" y1="'+(h-40)+'" x2="'+(w-10)+'" y2="'+(h-40)+'" stroke="#333" stroke-width="1"/>';
  svg+='<line x1="40" y1="10" x2="40" y2="'+(h-40)+'" stroke="#333" stroke-width="1"/>';
  for(var i=0;i<=5;i++){
    var x=40+i/5*0.85*w,lbl=((xmin+i/5*(xmax-xmin))*100|0)/100;
    svg+='<text x="'+x+'" y="'+(h-25)+'" font-size="10" fill="#555" text-anchor="middle">'+lbl+'</text>';
  }
  for(var i=0;i<=5;i++){
    var y=h-40-i/5*0.8*h,lbl=((ymin+i/5*(ymax-ymin))*100|0)/100;
    svg+='<text x="35" y="'+y+'" font-size="10" fill="#555" text-anchor="end" dominant-baseline="middle">'+lbl+'</text>';
  }
  points.forEach(function(p){
    var x=px(p.x),y=py(p.y),r=Math.sqrt(p.size||1)*2+2;
    svg+='<circle cx="'+x+'" cy="'+y+'" r="'+r+'" fill="'+p.color+'" opacity="0.7" stroke="none"/>';
  });
  svg+='</svg>';
  svg+='<div style="position:relative;width:100%;height:'+h+'px;background:#0f0f16;border:1px solid #1e1e2e;border-radius:4px">'+svg;
  svg+='<div class="ax ax-x" style="left:40px;right:10px;text-align:center">'+xLabel+'</div>';
  svg+='<div class="ax ax-y">'+yLabel+'</div></div>';
  container.innerHTML=svg;
}

var paretoAgents=A.filter(function(a){return a.n_markets>0}).map(function(a){
  var costPerMarket=a.n_markets>0?a.costs/a.n_markets:0;
  return{id:a.id,x:costPerMarket,y:a.avg_score,size:a.wins+1,color:TC[a.aesthetic]||'#888',data:a};
});
var paretoLine=[];
paretoAgents.forEach(function(a1){
  var isDominated=paretoAgents.some(function(a2){return a2.x<=a1.x&&a2.y>=a1.y&&(a2.x<a1.x||a2.y>a1.y)});
  if(!isDominated)paretoLine.push(a1);
});
paretoLine.sort(function(a,b){return a.x-b.x});
drawScatter(document.getElementById('pareto'),'Cost/Market',paretoLine.length?'Avg Score':'(no data)',paretoAgents);

var scoreWinRatePoints=A.map(function(a){return{x:a.avg_score,y:(a.win_rate*100|0),size:a.n_markets,color:TC[a.economic_strategy]||'#888'};});
drawScatter(document.getElementById('scatter2'),'Avg Score (1-10)','Win Rate (%)',scoreWinRatePoints);

var revisions=[];D.markets.forEach(function(m){m.submissions.forEach(function(s){if(s.n_revisions>0){revisions.push({x:s.initial_score,y:s.final_score,q:s.qualified,color:s.qualified?'#4caf50':'#f44336'});}})});
drawScatter(document.getElementById('revplot'),'Initial Score','Final Score',revisions);

var mpl=Math.max.apply(null,A.map(function(a){return Math.abs(a.pnl)}).concat([.01]));
document.getElementById('pnl').innerHTML=A.slice(0,5).map(function(a){var w=Math.abs(a.pnl)/mpl*100,c=a.pnl>=0?'#4caf50':'#f44336';return'<div class="bar"><div class="bl">'+a.id.substring(0,20)+'</div><div class="bf" style="width:'+w+'%;background:'+c+'"></div><div class="bv">'+(a.pnl>=0?'+':'')+'$'+a.pnl.toFixed(3)+'</div></div>'}).join('');

var sparkTBody='';
A.forEach(function(a,i){
  var c=a.pnl>=0?'p':'n';
  var spark='<div class="spark">';
  var mx=Math.max.apply(null,a.scores.concat([1]));
  a.scores.forEach(function(s){
    var h=Math.max(2,s/mx*12);
    var col=s>=8?'#2e7d32':(s>=6?'#f9a825':'#c62828');
    spark+='<div class="sb" style="background:'+col+';height:'+h+'px" title="'+s+'"></div>';
  });
  spark+='</div>';
  sparkTBody+='<tr><td>'+(i+1)+'</td><td><b>'+a.id.substring(0,16)+'</b></td><td>'+a.economic_strategy+'</td><td>'+a.wins+'</td><td>'+a.losses+'</td><td>'+(a.win_rate*100|0)+'%</td><td>'+a.avg_score.toFixed(1)+'</td><td>'+spark+'</td><td>$'+a.costs.toFixed(3)+'</td><td class="'+c+'"><b>'+(a.pnl>=0?'+':'')+'$'+a.pnl.toFixed(3)+'</b></td></tr>';
});
document.querySelector('#atbl tbody').innerHTML=sparkTBody;

document.getElementById('ttbl').innerHTML='<table><thead><tr><th>Tier</th><th>N</th><th>OK</th><th>Fail</th><th>Avg</th><th>Gap</th></tr></thead><tbody>'+TO.filter(function(t){return D.tier_summary[t]&&D.tier_summary[t].total>0}).map(function(t){var s=D.tier_summary[t];return'<tr><td><span class="tc tc-'+t+'">'+t.substring(0,3)+'</span></td><td>'+s.total+'</td><td>'+s.settled+'</td><td class="'+(s.timeouts?'n':'')+'">'+s.timeouts+'</td><td>'+(s.avg_score?s.avg_score.toFixed(1):'—')+'</td><td class="p">+'+s.quality_gap.toFixed(1)+'</td></tr>'}).join('')+'</tbody></table>';

document.getElementById('sdist').innerHTML=TO.filter(function(t){return D.tier_summary[t]&&D.tier_summary[t].total>0}).map(function(t){
  var all_scores=D.tier_summary[t].all_scores||[];
  if(!all_scores.length){D.markets.forEach(function(m){if(m.tier===t)(m.submissions||[]).forEach(function(s){all_scores.push(s.final_score||s.score||0)})})}
  var bk=Array(10).fill(0);
  all_scores.forEach(function(s){bk[Math.min(Math.max(s,1),10)-1]++});
  var mx=Math.max.apply(null,bk.concat([1]));
  return'<div style="flex:1;min-width:80px"><div style="font-size:.65em;color:'+TC[t]+';margin-bottom:2px">'+t+' n='+all_scores.length+'</div><div style="display:flex;align-items:flex-end;height:40px;gap:1px">'+bk.map(function(c,i){var h=c/mx*40,cl=i>=7?'#2e7d32':(i>=5?'#f9a825':'#c62828');return'<div style="flex:1;background:'+cl+';height:'+h+'px;border-radius:1px 1px 0 0" title="'+(i+1)+': '+c+'"></div>'}).join('')+'</div></div>'
}).join('');

document.getElementById('mlist').innerHTML=S.concat(T).map(function(m){
  var st='';
  if(m.status==='settled'){var rs=m.submissions.filter(function(s){return s.n_revisions>0}),rn=rs.length?' <span class="rb">'+rs.reduce(function(s,r){return s+r.n_revisions},0)+'rev</span>':'';st='<span class="wb">★'+m.winner+'</span> '+m.score+'/10 '+m.elapsed.toFixed(0)+'s'+rn;}else st='<span style="color:#f44336">TIMEOUT</span>';
  var sc=(m.submissions||[]).sort(function(a,b){return b.final_score-a.final_score}).slice(0,6).map(function(s){var c=s.final_score>=8?'sh':(s.final_score>=6?'sm':'sl');return'<span class="sc '+c+'">'+s.agent_id.substring(0,12)+' '+s.final_score+(s.n_revisions?' r'+s.n_revisions:'')+'</span>'}).join('');
  return'<div class="mc"><div style="display:flex;justify-content:space-between"><span><span class="tc tc-'+m.tier+'">'+m.tier+'</span> <b>'+m.market_id+'</b></span><span style="color:#555">$'+m.max_price.toFixed(3)+' q≥'+m.min_quality+'</span></div><div class="pr">'+m.prompt+'</div><div style="margin-top:3px">'+st+'</div><div class="sr">'+sc+'</div></div>'
}).join('');
</script>
</body></html>"""



