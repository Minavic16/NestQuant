/* NestQuant Studio operator dashboard */
(function () {
  const $ = (id) => document.getElementById(id);
  const errEl = $("err");
  const btn = $("btn-refresh");
  let snapshot = null;

  function showErr(msg) {
    if (!msg) {
      errEl.hidden = true;
      errEl.textContent = "";
      return;
    }
    errEl.hidden = false;
    errEl.textContent = msg;
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
      return d.toLocaleString(undefined, {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function statusPill(status) {
    const s = String(status || "");
    let cls = "info";
    if (s === "killed" || s === "failed") cls = "err";
    else if (s.includes("approved") || s === "ok" || s === "done") cls = "ok";
    else if (s.includes("awaiting") || s === "running") cls = "warn";
    return `<span class="pill ${cls}">${escapeHtml(s)}</span>`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderKpis(counts) {
    const items = [
      ["Hypotheses", counts.hypotheses],
      ["In flight", counts.active_like],
      ["Composites", counts.composites],
      ["Activity", counts.activity],
      ["Eng open", counts.engineering_open],
    ];
    $("kpis").innerHTML = items
      .map(
        ([label, value]) =>
          `<div class="kpi"><div class="label">${escapeHtml(label)}</div><div class="value">${value ?? 0}</div></div>`
      )
      .join("");
  }

  function renderHyps(data) {
    const lock = data.lock;
    const badge = $("lock-badge");
    if (lock && lock.hypothesis_id) {
      badge.textContent = "lock on";
      badge.classList.add("on");
      badge.title = lock.hypothesis_id;
    } else {
      badge.textContent = "lock free";
      badge.classList.remove("on");
      badge.title = "";
    }

    const list = data.hypotheses || [];
    if (!list.length) {
      $("hyp-list").innerHTML = `<div class="empty">No hypotheses yet.</div>`;
      return;
    }
    $("hyp-list").innerHTML = list
      .map(({ hypothesis: h, candidate_counts, candidates_total, level_runs }) => {
        const cc = Object.entries(candidate_counts || {})
          .map(([k, v]) => `${k}:${v}`)
          .join(" · ");
        const lastRun = (level_runs || []).slice(-1)[0];
        return `<article class="card">
          <h3>${escapeHtml(h.title)}</h3>
          <div class="meta">
            ${statusPill(h.status)}
            <span>candidates ${candidates_total || 0}</span>
            ${h.priority_score != null ? `<span>prio ${h.priority_score}</span>` : ""}
          </div>
          <div class="meta" style="margin-top:6px">${escapeHtml(cc || "no candidates")}</div>
          ${
            lastRun
              ? `<div class="meta" style="margin-top:6px">last ${escapeHtml(lastRun.level_id)} · ${escapeHtml(lastRun.status)}</div>`
              : ""
          }
          <div class="act-kind" style="margin-top:8px">${escapeHtml(h.hypothesis_id)}</div>
        </article>`;
      })
      .join("");
  }

  function renderActivity(items, filter) {
    const q = (filter || "").trim().toLowerCase();
    let rows = items || [];
    if (q) {
      rows = rows.filter((a) =>
        [a.title, a.detail, a.kind, a.actor, a.entity_type]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(q)
      );
    }
    if (!rows.length) {
      $("activity").innerHTML = `<div class="empty">No activity${q ? " matching filter" : ""}.</div>`;
      return;
    }
    $("activity").innerHTML = rows
      .map((a) => {
        const sev = a.severity || "info";
        return `<div class="act-item ${escapeHtml(sev)}">
          <div class="act-time">${escapeHtml(fmtTime(a.at))}</div>
          <div>
            <div class="act-title">${escapeHtml(a.title)}</div>
            ${a.detail ? `<div class="act-detail">${escapeHtml(a.detail)}</div>` : ""}
            <div class="act-kind">${escapeHtml(a.kind)}${a.actor ? " · " + escapeHtml(a.actor) : ""}</div>
          </div>
        </div>`;
      })
      .join("");
  }

  function renderLadder(data) {
    const rows = [];
    (data.hypotheses || []).forEach(({ hypothesis: h, level_runs }) => {
      (level_runs || []).forEach((r) => {
        rows.push({
          hyp: h.title,
          level: r.level_id,
          status: r.status,
          report: r.report,
          started: r.started_at,
          finished: r.finished_at,
        });
      });
    });
    if (!rows.length) {
      $("ladder").innerHTML = `<div class="empty">No ladder runs yet.</div>`;
      return;
    }
    $("ladder").innerHTML = `<table>
      <thead><tr><th>Hypothesis</th><th>Level</th><th>Status</th><th>Passed/In</th><th>Finished</th></tr></thead>
      <tbody>
      ${rows
        .map((r) => {
          const rep = r.report || {};
          const pi =
            rep.passed != null ? `${rep.passed}/${rep.input ?? "—"}` : "—";
          return `<tr>
            <td>${escapeHtml(r.hyp)}</td>
            <td>${escapeHtml(r.level)}</td>
            <td>${statusPill(r.status)}</td>
            <td>${escapeHtml(String(pi))}</td>
            <td>${escapeHtml(fmtTime(r.finished || r.started))}</td>
          </tr>`;
        })
        .join("")}
      </tbody></table>`;
  }

  function renderEng(items) {
    if (!items || !items.length) {
      $("engineering").innerHTML = `<div class="empty">No engineering tasks.</div>`;
      return;
    }
    $("engineering").innerHTML = items
      .map(
        (t) => `<article class="card">
        <h3>${escapeHtml(t.title)}</h3>
        <div class="meta">${statusPill(t.status)}
          ${t.git_commit ? `<span>${escapeHtml(t.git_commit.slice(0, 8))}</span>` : ""}
          <span>${escapeHtml(fmtTime(t.updated_at || t.created_at))}</span>
        </div>
      </article>`
      )
      .join("");
  }

  function renderComposites(items) {
    if (!items || !items.length) {
      $("composites").innerHTML = `<div class="empty">No composites.</div>`;
      return;
    }
    $("composites").innerHTML = items
      .map(
        (c) => `<article class="card">
        <h3>${escapeHtml(c.title)}</h3>
        <div class="meta">${statusPill(c.status)}
          <span>v${c.version}</span>
          <span>${escapeHtml(c.composite_id)}</span>
        </div>
      </article>`
      )
      .join("");
  }

  async function load() {
    showErr("");
    btn.disabled = true;
    try {
      const res = await fetch("/api/dashboard", { cache: "no-store" });
      if (!res.ok) throw new Error(`dashboard ${res.status}`);
      snapshot = await res.json();
      $("freshness").textContent = `as of ${fmtTime(snapshot.generated_at)}`;
      renderKpis(snapshot.counts || {});
      renderHyps(snapshot);
      renderActivity(snapshot.activity || [], $("act-filter").value);
      renderLadder(snapshot);
      renderEng(snapshot.engineering || []);
      renderComposites(snapshot.composites || []);
    } catch (e) {
      showErr(String(e.message || e));
    } finally {
      btn.disabled = false;
    }
  }

  btn.addEventListener("click", load);
  $("act-filter").addEventListener("input", () => {
    if (snapshot) renderActivity(snapshot.activity || [], $("act-filter").value);
  });

  load();
  setInterval(load, 15000);
})();