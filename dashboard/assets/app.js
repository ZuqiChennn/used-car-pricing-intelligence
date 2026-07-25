const D=window.DASHBOARD_DATA;
const eur=v=>new Intl.NumberFormat("en-DE",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(v);
const num=v=>new Intl.NumberFormat("en-DE").format(v);
const esc=s=>String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
document.getElementById("freshness").textContent=`Data as of ${D.summary.as_of} · ${D.summary.data_label}`;
document.getElementById("kpis").innerHTML=[
  [eur(D.summary.mae_eur),"Holdout MAE"],
  [`${D.summary.baseline_improvement_pct}%`,"MAE improvement vs median baseline"],
  [D.summary.test_rows.toLocaleString(),"Latest-period holdout listings"],
  [D.summary.action_candidates,"Inventory price reviews"]
].map(x=>`<div class="kpi"><strong>${x[0]}</strong><span>${x[1]}</span></div>`).join("");
const select=document.getElementById("brandFilter");
D.byBrand.forEach(x=>select.insertAdjacentHTML("beforeend",`<option>${esc(x.brand)}</option>`));
select.addEventListener("change",render);

function frame(w=560,h=280){return {w,h,l:58,r:18,t:18,b:42,iw:w-76,ih:h-60}}
function brandChart(rows){
  const f=frame(), max=Math.max(...rows.flatMap(d=>[d.median_asking,d.median_model]))*1.15;
  const bw=f.iw/Math.max(rows.length,1), bar=Math.min(25,bw*.28);
  let svg=`<svg viewBox="0 0 ${f.w} ${f.h}" class="chart" role="img" aria-label="Median asking and model prices by brand">`;
  [0,.25,.5,.75,1].forEach(q=>{const y=f.t+f.ih*(1-q);svg+=`<line x1="${f.l}" y1="${y}" x2="${f.w-f.r}" y2="${y}" class="gridline"/><text x="${f.l-8}" y="${y+4}" text-anchor="end" class="label">${Math.round(max*q/1000)}k</text>`});
  rows.forEach((d,i)=>{const x=f.l+bw*i+bw/2,y1=f.t+f.ih*(1-d.median_asking/max),y2=f.t+f.ih*(1-d.median_model/max);svg+=`<rect x="${x-bar-2}" y="${y1}" width="${bar}" height="${f.t+f.ih-y1}" rx="3" fill="#1769aa"><title>${d.brand}: asking ${eur(d.median_asking)}</title></rect><rect x="${x+2}" y="${y2}" width="${bar}" height="${f.t+f.ih-y2}" rx="3" fill="#d89b28"><title>${d.brand}: model ${eur(d.median_model)}</title></rect><text x="${x}" y="${f.h-16}" text-anchor="middle" class="label">${esc(d.brand)}</text>`});
  return svg+`</svg><div class="legend"><span><i class="swatch" style="background:#1769aa"></i>Asking price</span><span><i class="swatch" style="background:#d89b28"></i>Model estimate</span></div>`;
}
function ageChart(rows){
  const f=frame(), max=Math.max(...rows.flatMap(d=>[d.asking,d.model]))*1.1,minAge=Math.min(...rows.map(d=>d.age_years)),maxAge=Math.max(...rows.map(d=>d.age_years));
  const px=x=>f.l+(x-minAge)/(maxAge-minAge||1)*f.iw,py=y=>f.t+f.ih*(1-y/max);
  let svg=`<svg viewBox="0 0 ${f.w} ${f.h}" class="chart" role="img" aria-label="Median used-car price by age">`;
  [0,.25,.5,.75,1].forEach(q=>{const y=f.t+f.ih*(1-q);svg+=`<line x1="${f.l}" y1="${y}" x2="${f.w-f.r}" y2="${y}" class="gridline"/><text x="${f.l-8}" y="${y+4}" text-anchor="end" class="label">${Math.round(max*q/1000)}k</text>`});
  svg+=`<polyline points="${rows.map(d=>`${px(d.age_years)},${py(d.asking)}`).join(" ")}" class="line-a"/><polyline points="${rows.map(d=>`${px(d.age_years)},${py(d.model)}`).join(" ")}" class="line-b"/>`;
  rows.forEach(d=>{svg+=`<circle cx="${px(d.age_years)}" cy="${py(d.asking)}" r="3" class="dot-a"><title>Age ${d.age_years}: ${eur(d.asking)}</title></circle><circle cx="${px(d.age_years)}" cy="${py(d.model)}" r="3" class="dot-b"/>`});
  [minAge,Math.round((minAge+maxAge)/2),maxAge].forEach(x=>svg+=`<text x="${px(x)}" y="${f.h-16}" text-anchor="middle" class="label">${x} years</text>`);
  return svg+`</svg><div class="legend"><span><i class="swatch" style="background:#1769aa"></i>Asking price</span><span><i class="swatch" style="background:#d89b28"></i>Model estimate</span></div>`;
}
function render(){
  const b=select.value;
  const brands=b==="All"?D.byBrand:D.byBrand.filter(x=>x.brand===b);
  const inventory=b==="All"?D.inventory:D.inventory.filter(x=>x.brand===b);
  document.getElementById("brandChart").innerHTML=brandChart(brands);
  document.getElementById("ageChart").innerHTML=ageChart(D.byAge);
  document.getElementById("inventory").innerHTML=inventory.slice(0,20).map(x=>`<tr><td><b>${esc(x.brand)} ${esc(x.model)}</b><br><span class="note">${x.listing_id}</span></td><td>${x.age_years}y</td><td>${num(x.mileage_km)} km</td><td>${x.days_on_market}</td><td>${eur(x.asking_price_eur)}</td><td>${eur(x.model_price_eur)}</td><td>${x.price_gap_pct>0?"+":""}${x.price_gap_pct}%</td><td><span class="pill ${x.recommended_action==="Review markdown"?"review":x.recommended_action==="Check underpricing"?"under":""}">${x.recommended_action}</span></td></tr>`).join("")||`<tr><td colspan="8">No rows for this filter.</td></tr>`;
}
render();
