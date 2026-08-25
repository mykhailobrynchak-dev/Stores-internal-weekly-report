(() => {
  const fmt = {
    eur: v => new Intl.NumberFormat('en-GB', {style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v || 0),
    eur2: v => new Intl.NumberFormat('en-GB', {style:'currency',currency:'EUR',minimumFractionDigits:2,maximumFractionDigits:2}).format(v || 0),
    num: v => new Intl.NumberFormat('en-GB', {maximumFractionDigits:0}).format(v || 0),
    pct: v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`,
    rate: v => `${(v || 0).toFixed(2)}%`,
    date: s => new Date(`${s}T00:00:00`).toLocaleDateString('en-GB',{day:'numeric',month:'short'}),
    month: s => new Date(`${s}T00:00:00`).toLocaleDateString('en-GB',{month:'long',year:'numeric'}),
  };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sum = (rows, key) => rows.reduce((total, row) => total + (+row[key] || 0), 0);
  const shift = (current, prior) => +prior ? (+current / +prior - 1) * 100 : null;
  const displayShift = (current, prior) => shift(current, prior) == null ? '—' : fmt.pct(shift(current, prior));
  const weekEnd = start => {
    const day = new Date(`${start}T00:00:00`);
    day.setDate(day.getDate() + 6);
    return day.toISOString().slice(0, 10);
  };
  const weekLabel = start => `${fmt.date(start)}–${fmt.date(weekEnd(start))}`;
  const valueOrDash = (value, formatter) => value == null ? '—' : formatter(+value);
  const byPartner = rows => Object.fromEntries(rows.map(row => [row.partner, row]));
  const charts = {};
  let data;
  let weeks;

  function aggregate(rows) {
    const economicsGmv = sum(rows, 'economics_gmv_eur');
    return {
      orders: sum(rows, 'orders'),
      gmv_eur: sum(rows, 'gmv_eur'),
      demand_incentives_eur: sum(rows, 'demand_incentives_eur'),
      demand_refunds_eur: sum(rows, 'demand_refunds_eur'),
      incentive_orders: sum(rows, 'incentive_orders'),
      demand_refund_orders: sum(rows, 'demand_refund_orders'),
      active_partners: new Set(rows.filter(row => +row.orders > 0).map(row => row.partner)).size,
      commission_eur: sum(rows, 'commission_eur'),
      cm_l1_eur: sum(rows, 'cm_l1_eur'),
      economics_gmv_eur: economicsGmv,
      commission_gmv_pct: economicsGmv ? sum(rows, 'commission_eur') / economicsGmv * 100 : null,
      cm_l1_pct: economicsGmv ? sum(rows, 'cm_l1_eur') / economicsGmv * 100 : null,
    };
  }

  function weekRows(week) {
    const economics = byPartner(data.weekly_economics.filter(row => row.week_start === week));
    return data.weekly_partner
      .filter(row => row.week_start === week)
      .map(row => ({...row, ...(economics[row.partner] || {})}));
  }

  function cumulativeRows() {
    const rows = {};
    for (const row of data.weekly_partner) {
      const item = rows[row.partner] ||= {partner:row.partner};
      for (const key of ['orders','gmv_eur','demand_incentives_eur','demand_refunds_eur','incentive_orders','demand_refund_orders']) {
        item[key] = (item[key] || 0) + (+row[key] || 0);
      }
    }
    for (const row of data.weekly_economics) {
      const item = rows[row.partner] ||= {partner:row.partner};
      for (const key of ['commission_eur','cm_l1_eur','economics_gmv_eur']) {
        item[key] = (item[key] || 0) + (+row[key] || 0);
      }
    }
    return Object.values(rows).map(row => ({
      ...row,
      commission_gmv_pct: row.economics_gmv_eur ? row.commission_eur / row.economics_gmv_eur * 100 : null,
      cm_l1_pct: row.economics_gmv_eur ? row.cm_l1_eur / row.economics_gmv_eur * 100 : null,
    }));
  }

  function kpi(label, value, delta, sub, inverse=false) {
    const neutral = delta == null || Math.abs(delta) < .05;
    const good = !neutral && ((delta > 0) !== inverse);
    const cls = neutral ? 'neutral' : good ? 'good' : 'bad';
    const arrow = delta == null ? '→' : delta > 0 ? '↑' : delta < 0 ? '↓' : '→';
    const deltaText = delta == null ? '—' : fmt.pct(delta);
    return `<article class="card kpi">
      <div><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${value}</div></div>
      <div><span class="delta ${cls}">${arrow} ${deltaText}</span><div class="sub">${sub}</div></div>
    </article>`;
  }

  function table(headers, rows, classes='') {
    return `<div class="table-wrap"><table class="${classes}">
      <thead><tr>${headers.map(header => `<th>${header}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
    </table></div>`;
  }

  function makeChart(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), config);
  }

  const baseOptions = yTitle => ({
    responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{usePointStyle:true,boxWidth:7}},tooltip:{padding:10}},
    scales:{
      x:{grid:{display:false},title:{display:true,text:'Week starting'}},
      y:{beginAtZero:true,grid:{color:'#e8edea'},title:{display:true,text:yTitle}},
    },
  });

  function renderOverview() {
    const cumulative = cumulativeRows();
    const total = aggregate(cumulative);
    const latestRows = weekRows(weeks.at(-1));
    const priorRows = weekRows(weeks.at(-2));
    const latest = aggregate(latestRows);
    const prior = aggregate(priorRows);
    const periodLabel = `${fmt.date(data.metadata.period_start)}–${fmt.date(data.metadata.data_through)}`;

    document.getElementById('content').innerHTML = `
      <div class="notice"><span>Cumulative report · ${periodLabel}</span><strong>${weeks.length} complete weeks · latest ${weekLabel(weeks.at(-1))}</strong></div>
      <div class="grid kpis overview-kpis">
        ${kpi('Cumulative GMV',fmt.eur(total.gmv_eur),null,periodLabel)}
        ${kpi('Cumulative orders',fmt.num(total.orders),null,periodLabel)}
        ${kpi('Demand incentives',fmt.eur(total.demand_incentives_eur),null,`${fmt.rate(total.demand_incentives_eur/total.gmv_eur*100)} of GMV`,true)}
        ${kpi('Demand refunds',fmt.eur2(total.demand_refunds_eur),null,`${fmt.rate(total.demand_refunds_eur/total.gmv_eur*100)} of GMV`,true)}
        ${kpi('Latest-week GMV',fmt.eur(latest.gmv_eur),shift(latest.gmv_eur,prior.gmv_eur),`vs ${weekLabel(weeks.at(-2))}`)}
        ${kpi('Latest-week orders',fmt.num(latest.orders),shift(latest.orders,prior.orders),`vs ${weekLabel(weeks.at(-2))}`)}
        ${kpi('Avg commission',valueOrDash(total.commission_gmv_pct,fmt.rate),null,'GMV-weighted across period')}
        ${kpi('CM L1',valueOrDash(total.cm_l1_pct,fmt.rate),null,`${fmt.eur2(total.cm_l1_eur)} across period`)}
      </div>
      <div class="grid two">
        <div class="card"><h3>GMV and orders · all complete weeks</h3><div class="chart-wrap"><canvas id="overviewVolume"></canvas></div></div>
        <div class="card"><h3>Demand costs as share of GMV</h3><div class="chart-wrap"><canvas id="overviewCosts"></canvas></div></div>
      </div>
      <section class="section">
        <div class="section-head"><div><h2>Top 15 cumulative contributors</h2><p>Sorted by GMV across the complete reporting period.</p></div></div>
        <div id="cumulativeTable"></div>
      </section>
      <section class="section grid equal">
        <div><div class="section-head"><div><h2>Top 15 incentive contributors</h2><p>Latest complete week.</p></div></div><div id="topDi"></div></div>
        <div><div class="section-head"><div><h2>Top 15 refund contributors</h2><p>Latest complete week.</p></div></div><div id="topDr"></div></div>
      </section>
      <section class="section">
        <div class="section-head"><div><h2>Top 15 programs · cumulative</h2><p>Named Bolt campaign spend across all complete weeks.</p></div></div>
        <div id="programOverview"></div>
      </section>`;

    const weekTotals = weeks.map(week => aggregate(weekRows(week)));
    makeChart('overviewVolume',{type:'bar',data:{labels:weeks.map(fmt.date),datasets:[
      {label:'GMV (€)',data:weekTotals.map(row=>row.gmv_eur),backgroundColor:'#2f7d5bcc',borderRadius:4,yAxisID:'y'},
      {label:'Orders',data:weekTotals.map(row=>row.orders),type:'line',borderColor:'#3f68a7',backgroundColor:'#3f68a7',pointRadius:3,tension:.25,yAxisID:'y1'}
    ]},options:{...baseOptions('GMV (€)'),scales:{x:{grid:{display:false}},y:{beginAtZero:true,title:{display:true,text:'GMV (€)'}},y1:{beginAtZero:true,position:'right',grid:{display:false},title:{display:true,text:'Orders'}}}}});
    makeChart('overviewCosts',{type:'line',data:{labels:weeks.map(fmt.date),datasets:[
      {label:'Demand incentives / GMV',data:weekTotals.map(row=>row.demand_incentives_eur/row.gmv_eur*100),borderColor:'#9b6a17',backgroundColor:'#9b6a17',tension:.25,pointRadius:3},
      {label:'Demand refunds / GMV',data:weekTotals.map(row=>row.demand_refunds_eur/row.gmv_eur*100),borderColor:'#b34646',backgroundColor:'#b34646',tension:.25,pointRadius:3}
    ]},options:baseOptions('Share of GMV (%)')});

    const topCumulative = [...cumulative].sort((a,b)=>b.gmv_eur-a.gmv_eur).slice(0,15);
    document.getElementById('cumulativeTable').innerHTML = table(
      ['Partner','Orders','GMV','GMV share','AOV','DI','DI / GMV','DR','DR / GMV','Comm %','CM L1 €','CM L1 %'],
      topCumulative.map(row => [
        esc(row.partner),fmt.num(row.orders),fmt.eur(row.gmv_eur),fmt.rate(row.gmv_eur/total.gmv_eur*100),
        fmt.eur2(row.gmv_eur/row.orders),fmt.eur(row.demand_incentives_eur),fmt.rate(row.demand_incentives_eur/row.gmv_eur*100),
        fmt.eur2(row.demand_refunds_eur),fmt.rate(row.demand_refunds_eur/row.gmv_eur*100),
        valueOrDash(row.commission_gmv_pct,fmt.rate),valueOrDash(row.cm_l1_eur,fmt.eur2),valueOrDash(row.cm_l1_pct,fmt.rate),
      ])
    );

    const contributorTable = (metric, moneyFormatter, rateLabel) => {
      const totalMetric = sum(latestRows,metric);
      return table(['Partner',rateLabel,'Share','/ GMV'],[...latestRows]
        .sort((a,b)=>(+b[metric]||0)-(+a[metric]||0)).slice(0,15)
        .map(row=>[esc(row.partner),moneyFormatter(row[metric]),fmt.rate(row[metric]/totalMetric*100),fmt.rate(row[metric]/row.gmv_eur*100)]));
    };
    document.getElementById('topDi').innerHTML = contributorTable('demand_incentives_eur',fmt.eur,'DI');
    document.getElementById('topDr').innerHTML = contributorTable('demand_refunds_eur',fmt.eur2,'DR');

    const programs = {};
    for (const row of data.weekly_campaigns) {
      const key = `${row.campaign}|||${row.objective}`;
      const item = programs[key] ||= {campaign:row.campaign,objective:row.objective,orders:0,bolt_spend_eur:0,weeks:new Set()};
      item.orders += +row.orders || 0;
      item.bolt_spend_eur += +row.bolt_spend_eur || 0;
      item.weeks.add(row.week_start);
    }
    document.getElementById('programOverview').innerHTML = table(
      ['Program','Objective','Active weeks','Campaign orders','Bolt spend'],
      Object.values(programs).sort((a,b)=>b.bolt_spend_eur-a.bolt_spend_eur).slice(0,15)
        .map(row=>[esc(row.campaign),esc(row.objective),fmt.num(row.weeks.size),fmt.num(row.orders),fmt.eur2(row.bolt_spend_eur)]),
      'program-table'
    );
  }

  function renderPartnerTable(week, sortMetric='gmv_eur') {
    const current = weekRows(week);
    const weekIndex = weeks.indexOf(week);
    const previous = weekIndex > 0 ? byPartner(weekRows(weeks[weekIndex-1])) : {};
    const mtd = byPartner(data.weekly_mtd_partner.filter(row=>row.week_start===week));
    const rows = [...current].sort((a,b)=>(+b[sortMetric]||0)-(+a[sortMetric]||0)).slice(0,20);
    document.getElementById('partnerWeekTable').innerHTML = table(
      ['Partner','Orders','Orders WoW','GMV','GMV WoW','AOV','DI','DI WoW','DI / GMV','DR','DR WoW','DR / GMV','Comm %','Comm Δ pp','CM L1 €','CM L1 %','CM L1 Δ pp','GMV MTD','GMV projection'],
      rows.map(row => {
        const prior = previous[row.partner] || {};
        const month = mtd[row.partner] || {};
        const commissionDelta = row.commission_gmv_pct != null && prior.commission_gmv_pct != null ? row.commission_gmv_pct-prior.commission_gmv_pct : null;
        const cmDelta = row.cm_l1_pct != null && prior.cm_l1_pct != null ? row.cm_l1_pct-prior.cm_l1_pct : null;
        return [
          esc(row.partner),fmt.num(row.orders),displayShift(row.orders,prior.orders),
          fmt.eur(row.gmv_eur),displayShift(row.gmv_eur,prior.gmv_eur),fmt.eur2(row.gmv_eur/row.orders),
          fmt.eur(row.demand_incentives_eur),displayShift(row.demand_incentives_eur,prior.demand_incentives_eur),fmt.rate(row.demand_incentives_eur/row.gmv_eur*100),
          fmt.eur2(row.demand_refunds_eur),displayShift(row.demand_refunds_eur,prior.demand_refunds_eur),fmt.rate(row.demand_refunds_eur/row.gmv_eur*100),
          valueOrDash(row.commission_gmv_pct,fmt.rate),commissionDelta == null ? '—' : `${commissionDelta>=0?'+':''}${commissionDelta.toFixed(2)} pp`,
          valueOrDash(row.cm_l1_eur,fmt.eur2),valueOrDash(row.cm_l1_pct,fmt.rate),cmDelta == null ? '—' : `${cmDelta>=0?'+':''}${cmDelta.toFixed(2)} pp`,
          valueOrDash(month.mtd_gmv_eur,fmt.eur),valueOrDash(month.projected_gmv_eur,fmt.eur),
        ];
      })
    );
  }

  function renderWeek(week) {
    const index = weeks.indexOf(week);
    const previousWeek = index > 0 ? weeks[index-1] : null;
    const currentRows = weekRows(week);
    const previousRows = previousWeek ? weekRows(previousWeek) : [];
    const current = aggregate(currentRows);
    const previous = aggregate(previousRows);
    const mtdRows = data.weekly_mtd_partner.filter(row=>row.week_start===week);
    const mtd = {
      orders:sum(mtdRows,'mtd_orders'),gmv_eur:sum(mtdRows,'mtd_gmv_eur'),
      demand_incentives_eur:sum(mtdRows,'mtd_demand_incentives_eur'),demand_refunds_eur:sum(mtdRows,'mtd_demand_refunds_eur'),
      prior_orders:sum(mtdRows,'prior_mtd_orders'),prior_gmv_eur:sum(mtdRows,'prior_mtd_gmv_eur'),
      prior_di:sum(mtdRows,'prior_mtd_demand_incentives_eur'),prior_dr:sum(mtdRows,'prior_mtd_demand_refunds_eur'),
      projected_orders:sum(mtdRows,'projected_orders'),projected_gmv_eur:sum(mtdRows,'projected_gmv_eur'),
      projected_di:sum(mtdRows,'projected_demand_incentives_eur'),projected_dr:sum(mtdRows,'projected_demand_refunds_eur'),
    };
    const snapshot = mtdRows[0] || {};
    const compareLabel = previousWeek ? `vs ${weekLabel(previousWeek)}` : 'first week in report';

    document.getElementById('content').innerHTML = `
      <div class="notice"><span>Complete week · ${weekLabel(week)}</span><strong>${previousWeek ? `WoW against ${weekLabel(previousWeek)}` : 'No prior week available'}</strong></div>
      <div class="grid kpis overview-kpis">
        ${kpi('GMV',fmt.eur(current.gmv_eur),previousWeek?shift(current.gmv_eur,previous.gmv_eur):null,compareLabel)}
        ${kpi('Orders',fmt.num(current.orders),previousWeek?shift(current.orders,previous.orders):null,compareLabel)}
        ${kpi('AOV',fmt.eur2(current.gmv_eur/current.orders),previousWeek?shift(current.gmv_eur/current.orders,previous.gmv_eur/previous.orders):null,'GMV per delivered order')}
        ${kpi('Active partners',fmt.num(current.active_partners),previousWeek?shift(current.active_partners,previous.active_partners):null,'with delivered orders')}
        ${kpi('Demand incentives',fmt.eur(current.demand_incentives_eur),previousWeek?shift(current.demand_incentives_eur,previous.demand_incentives_eur):null,`${fmt.rate(current.demand_incentives_eur/current.gmv_eur*100)} of GMV`,true)}
        ${kpi('Demand refunds',fmt.eur2(current.demand_refunds_eur),previousWeek?shift(current.demand_refunds_eur,previous.demand_refunds_eur):null,`${fmt.rate(current.demand_refunds_eur/current.gmv_eur*100)} of GMV`,true)}
        ${kpi('Commission',valueOrDash(current.commission_gmv_pct,fmt.rate),previousWeek?shift(current.commission_gmv_pct,previous.commission_gmv_pct):null,'GMV-weighted')}
        ${kpi('CM L1',valueOrDash(current.cm_l1_pct,fmt.rate),previousWeek?shift(current.cm_l1_pct,previous.cm_l1_pct):null,fmt.eur2(current.cm_l1_eur))}
      </div>
      <section class="section">
        <div class="section-head"><div><h2>${snapshot.as_of ? fmt.month(snapshot.as_of) : 'Month'} · MTD and projection</h2><p>${esc(data.metadata.projection_method)}</p></div></div>
        <div class="grid kpis projection-kpis">
          ${kpi('GMV MTD',fmt.eur(mtd.gmv_eur),shift(mtd.gmv_eur,mtd.prior_gmv_eur),`Projection ${fmt.eur(mtd.projected_gmv_eur)}`)}
          ${kpi('Orders MTD',fmt.num(mtd.orders),shift(mtd.orders,mtd.prior_orders),`Projection ${fmt.num(mtd.projected_orders)}`)}
          ${kpi('Incentives MTD',fmt.eur(mtd.demand_incentives_eur),shift(mtd.demand_incentives_eur,mtd.prior_di),`Projection ${fmt.eur(mtd.projected_di)}`,true)}
          ${kpi('Refunds MTD',fmt.eur2(mtd.demand_refunds_eur),shift(mtd.demand_refunds_eur,mtd.prior_dr),`Projection ${fmt.eur2(mtd.projected_dr)}`,true)}
        </div>
      </section>
      <section class="section">
        <div class="section-head">
          <div><h2>Top 20 partners · all metrics</h2><p>Ranking is configurable; all values remain visible.</p></div>
          <select id="partnerSort">
            <option value="gmv_eur">Sort by GMV</option><option value="orders">Sort by orders</option>
            <option value="demand_incentives_eur">Sort by incentives</option><option value="demand_refunds_eur">Sort by refunds</option>
            <option value="cm_l1_eur">Sort by CM L1 €</option>
          </select>
        </div>
        <div id="partnerWeekTable"></div>
      </section>
      <section class="section grid equal">
        <div><div class="section-head"><div><h2>Top 15 programs</h2><p>Named programs and WoW movement.</p></div></div><div id="weekPrograms"></div></div>
        <div><div class="section-head"><div><h2>Refund reasons</h2><p>Reason taxonomy and WoW movement.</p></div></div><div id="weekReasons"></div></div>
      </section>`;

    renderPartnerTable(week);
    document.getElementById('partnerSort').addEventListener('change', event => renderPartnerTable(week,event.target.value));

    const priorPrograms = previousWeek ? byProgram(data.weekly_campaigns.filter(row=>row.week_start===previousWeek)) : {};
    const currentPrograms = data.weekly_campaigns.filter(row=>row.week_start===week)
      .map(row=>({...row,prior:priorPrograms[row.campaign]?.bolt_spend_eur||0}))
      .map(row=>({...row,delta:row.bolt_spend_eur-row.prior}))
      .sort((a,b)=>b.bolt_spend_eur-a.bolt_spend_eur).slice(0,15);
    document.getElementById('weekPrograms').innerHTML = table(
      ['Program','Objective','Type','Orders','Spend','Prior','WoW'],
      currentPrograms.map(row=>[
        esc(row.campaign),esc(row.objective),esc(row.campaign_type),fmt.num(row.orders),
        fmt.eur2(row.bolt_spend_eur),fmt.eur2(row.prior),displayShift(row.bolt_spend_eur,row.prior),
      ]),'program-table'
    );

    const currentReasons = byReason(data.weekly_refund_reasons.filter(row=>row.week_start===week));
    const priorReasons = previousWeek ? byReason(data.weekly_refund_reasons.filter(row=>row.week_start===previousWeek)) : {};
    const reasons = [...new Set([...Object.keys(currentReasons),...Object.keys(priorReasons)])]
      .map(reason=>({reason,current:currentReasons[reason]||{},prior:priorReasons[reason]||{}}))
      .sort((a,b)=>(+b.current.demand_refunds_eur||0)-(+a.current.demand_refunds_eur||0));
    document.getElementById('weekReasons').innerHTML = table(
      ['Reason','Orders','Refunds','Prior refunds','WoW'],
      reasons.map(row=>[
        esc(row.reason),fmt.num(row.current.orders),fmt.eur2(row.current.demand_refunds_eur),
        fmt.eur2(row.prior.demand_refunds_eur),displayShift(row.current.demand_refunds_eur,row.prior.demand_refunds_eur),
      ])
    );
  }

  function byProgram(rows) {
    const output = {};
    for (const row of rows) {
      const item = output[row.campaign] ||= {...row,orders:0,bolt_spend_eur:0};
      item.orders += +row.orders || 0;
      item.bolt_spend_eur += +row.bolt_spend_eur || 0;
    }
    return output;
  }
  function byReason(rows) {
    const output = {};
    for (const row of rows) {
      const item = output[row.reason] ||= {reason:row.reason,orders:0,demand_refunds_eur:0};
      item.orders += +row.orders || 0;
      item.demand_refunds_eur += +row.demand_refunds_eur || 0;
    }
    return output;
  }

  function activate(button, render) {
    document.querySelectorAll('.tab').forEach(item=>item.classList.toggle('active',item===button));
    render();
    window.scrollTo({top:0,behavior:'smooth'});
  }

  async function init() {
    data = await fetch('./data.json').then(response => {
      if (!response.ok) throw new Error(`data.json: HTTP ${response.status}`);
      return response.json();
    });
    weeks = [...new Set(data.weekly_partner.map(row=>row.week_start))].sort();
    const main = document.querySelector('main.shell');
    main.innerHTML = `
      <header>
        <div><div class="eyebrow">Ukraine · 3P Stores</div><h1>Cumulative weekly performance</h1>
          <p>Volume, economics, demand costs, programs and partner contribution</p></div>
        <div class="meta">Data through <strong>${esc(data.metadata.data_through)}</strong><br>${weeks.length} complete weeks · EUR</div>
      </header>
      <nav class="tabs" id="reportTabs"><button class="tab active" id="overviewTab">Overview</button>
        ${[...weeks].reverse().map(week=>`<button class="tab" data-week="${week}">${weekLabel(week)}</button>`).join('')}
      </nav>
      <section id="content"></section>
      <footer>Source: Databricks · fact_order_delivery, fact_provider_weekly, dim_order_campaign_delivery, dim_campaign_delivery_v2 and refund reason tables. Orders and GMV use delivered orders; demand refunds include all states. Monthly projections use straight-line calendar-day run rate.</footer>`;

    const style = document.createElement('style');
    style.textContent = `
      .overview-kpis { grid-template-columns:repeat(4,minmax(0,1fr)); }
      .projection-kpis { grid-template-columns:repeat(4,minmax(0,1fr)); }
      .program-table td:first-child { white-space:normal; min-width:280px; }
      #partnerWeekTable .table-wrap { max-height:680px; }
      @media(max-width:1080px){.overview-kpis,.projection-kpis{grid-template-columns:repeat(2,1fr)}}
      @media(max-width:700px){.overview-kpis,.projection-kpis{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
    document.getElementById('overviewTab').addEventListener('click',event=>activate(event.currentTarget,renderOverview));
    document.querySelectorAll('[data-week]').forEach(button=>
      button.addEventListener('click',event=>activate(event.currentTarget,()=>renderWeek(button.dataset.week))));
    renderOverview();
  }

  init().catch(error => {
    document.querySelector('main.shell').innerHTML = `<div class="card"><h2>Report could not load</h2><p>${esc(error.message)}</p></div>`;
  });
})();
