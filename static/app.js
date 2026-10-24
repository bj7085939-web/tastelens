const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

fetch("/api/health").then(r => r.json()).then(h => {
  const m = $("#mode");
  m.textContent = h.live
    ? "LIVE · Qloo Taste AI API"
    : "DEMO MODE · mock data (add QLOO_API_KEY for live)";
  if (h.live) m.classList.add("live");
  $("#mock-banner").hidden = h.live;
}).catch(() => { $("#mode").textContent = "server unreachable"; });

fetch("/api/presets").then(r => r.json()).then(d => {
  const box = $("#presets");
  (d.presets || []).forEach(p => {
    const b = document.createElement("button");
    b.className = "preset";
    b.innerHTML = `<strong></strong><span></span>`;
    b.querySelector("strong").textContent = p.title;
    b.querySelector("span").textContent =
      p.seeds.map(s => s.name).join(" · ");
    b.addEventListener("click", () => run({ seeds: p.seeds }));
    box.appendChild(b);
  });
}).catch(() => {});

$("#seed-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const names = $$(".seed-name"), types = $$(".seed-type");
  const seeds = [];
  names.forEach((inp, i) => {
    const name = inp.value.trim();
    if (name) seeds.push({ name, type: types[i].value || undefined });
  });
  if (!seeds.length) { $("#status").textContent = "Add at least one seed."; return; }
  const location = $("#location").value.trim();
  run({ seeds, location: location || undefined });
});

async function run(body) {
  const btn = $("#go"), st = $("#status");
  btn.disabled = true;
  st.textContent = "Resolving your seeds in the Qloo taste graph and auditing the receipts…";
  $("#result").hidden = true;
  try {
    const r = await fetch("/api/briefing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "request failed");
    render(data);
    st.textContent = data.mode === "live"
      ? "Live briefing from the Qloo Taste AI API."
      : "Demo briefing from labelled mock data (deterministic, no API key).";
  } catch (err) {
    st.textContent = "Error: " + err.message;
  } finally {
    btn.disabled = false;
  }
}

function seedName(data, entityId) {
  const s = (data.seeds || []).find(x => x.entity_id === entityId);
  return s ? s.name : entityId;
}

function render(data) {
  // Briefing text, sentence by sentence, uncited sentences flagged.
  const ans = $("#briefing");
  ans.innerHTML = "";
  data.segments.forEach(seg => {
    const span = document.createElement("span");
    span.className = "seg" + (seg.cited ? "" : " uncited");
    span.textContent = seg.text + " ";
    seg.refs.forEach(n => {
      const sup = document.createElement("sup");
      sup.className = "ref";
      const a = document.createElement("a");
      a.href = "#ev-" + n; a.textContent = "[" + n + "]";
      sup.appendChild(a);
      span.appendChild(sup); span.appendChild(document.createTextNode(" "));
    });
    ans.appendChild(span);
  });

  const c = $("#coverage");
  const pct = Math.round(data.stats.coverage * 100);
  c.textContent = `Evidence coverage: ${data.stats.cited}/${data.stats.sentences} sentences (${pct}%)`;
  c.className = "coverage " + (data.stats.coverage === 1 ? "ok" : "bad");

  // Recommendation cards per domain.
  const wrap = $("#domains");
  wrap.innerHTML = "";
  data.domains.forEach(d => {
    if (!d.recommendations.length) return;
    const h = document.createElement("h3");
    h.textContent = d.label;
    wrap.appendChild(h);
    const grid = document.createElement("div");
    grid.className = "grid";
    d.recommendations.forEach(r => {
      const card = document.createElement("div");
      card.className = "card";
      const aff = r.affinity != null ? r.affinity.toFixed(2) : "—";
      const drivers = Object.entries(r.explainability || {})
        .sort((a, b) => b[1] - a[1]).slice(0, 3)
        .map(([sid, sc]) => `${seedName(data, sid)} ${Number(sc).toFixed(2)}`)
        .join(" · ");
      card.innerHTML = `
        <div class="card-top"><span class="rname"></span>
          <span class="aff" title="Qloo taste-graph affinity">◆ </span></div>
        <p class="desc"></p>
        <div class="drivers"></div>
        <div class="evref">evidence <a href="#ev-${r.evidence_ref}">[${r.evidence_ref}]</a></div>`;
      card.querySelector(".rname").textContent = r.name;
      card.querySelector(".aff").append(document.createTextNode(aff));
      card.querySelector(".desc").textContent = r.description || "";
      card.querySelector(".drivers").textContent =
        drivers ? "Driven by: " + drivers : "";
      grid.appendChild(card);
    });
    wrap.appendChild(grid);
  });

  // Evidence list.
  const box = $("#evidence");
  box.innerHTML = "";
  data.evidence.forEach(ev => {
    const d = document.createElement("div");
    d.className = "src"; d.id = "ev-" + ev.id;
    d.innerHTML = `<div class="t">[${ev.id}] </div><p></p>`;
    d.querySelector(".t").append(document.createTextNode(ev.title));
    d.querySelector("p").textContent = ev.detail;
    box.appendChild(d);
  });
  $("#result").hidden = false;
}
