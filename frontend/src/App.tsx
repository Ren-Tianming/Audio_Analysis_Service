import { type DragEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  clearTokens,
  setSession,
  type Analysis,
  type ApiKey,
  type ApiUsage,
  type Package,
  type Plan,
  type Transaction,
  type User
} from "./api";

type Page = "dashboard" | "analyze" | "history" | "pricing" | "keys" | "admin";

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState<Page>("dashboard");
  const [booting, setBooting] = useState(true);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!api.token()) {
      setBooting(false);
      return;
    }
    api.me().then(setUser).catch(() => clearTokens()).finally(() => setBooting(false));
  }, []);

  async function refreshUser() {
    const current = await api.me();
    setUser(current);
  }

  function signedIn(response: { access_token: string; refresh_token: string; user: User; daily_bonus_awarded: number }) {
    setSession(response);
    setUser(response.user);
    setPage("dashboard");
    if (response.daily_bonus_awarded) setNotice(`デイリーボーナス +${response.daily_bonus_awarded} PT を獲得しました。`);
  }

  async function logout() {
    await api.logout().catch(() => undefined);
    clearTokens();
    setUser(null);
    setNotice("");
  }

  if (booting) return <div className="boot-screen"><div className="pulse-ring" /> CONNECTING TO AUDIO_ANALYSIS_SYSTEM</div>;
  if (!user) return <Landing onSignedIn={signedIn} />;

  return (
    <div className="shell">
      <Background />
      <Header user={user} page={page} onNavigate={setPage} onLogout={logout} />
      {notice && <div className="toast" onClick={() => setNotice("")}>{notice}</div>}
      <main className="workspace">
        {page === "dashboard" && <Dashboard user={user} onNavigate={setPage} />}
        {page === "analyze" && <Analyze user={user} onUpdated={refreshUser} onNotice={setNotice} />}
        {page === "history" && <History />}
        {page === "pricing" && <Pricing onUpdated={refreshUser} onNotice={setNotice} />}
        {page === "keys" && <Keys />}
        {page === "admin" && user.role === "ADMIN" && <Admin />}
      </main>
    </div>
  );
}

function Background() {
  return (
    <div className="backdrop" aria-hidden="true">
      <div className="orb orb-pink" />
      <div className="orb orb-blue" />
      <div className="grid-floor" />
    </div>
  );
}

function Landing({ onSignedIn }: { onSignedIn: (data: { access_token: string; refresh_token: string; user: User; daily_bonus_awarded: number }) => void }) {
  return (
    <div className="landing">
      <Background />
      <nav className="landing-nav">
        <Brand />
        <div className="landing-links"><span>FEATURES</span><span>PRICING</span><span>API</span></div>
      </nav>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">AI MUSIC INTELLIGENCE / V1.3</p>
          <h1>Upload your track.<br /><span>Reveal BPM, Key, Energy.</span></h1>
          <p className="lead">制作の直感を、ネオンに光る解析データへ。波形、スペクトログラム、音量指標を一つのワークスペースで確認できます。</p>
          <div className="hero-pills">
            <span>BPM DETECT</span><span>KEY MAP</span><span>LUFS</span><span>PDF REPORT</span>
          </div>
        </div>
        <AuthPanel onSignedIn={onSignedIn} />
      </section>
      <section className="signal-deck">
        <div className="deck-heading"><p className="eyebrow">LIVE SPECTRUM</p><h2>Sound becomes signal.</h2></div>
        <WaveBars />
        <div className="feature-row">
          {["Tempo Engine", "Chromatic Key", "Spectrogram", "Creator API"].map((feature, index) => (
            <div className="feature-card" key={feature}><span>0{index + 1}</span><strong>{feature}</strong><p>解析結果を履歴とレポートへ記録。</p></div>
          ))}
        </div>
      </section>
    </div>
  );
}

function AuthPanel({ onSignedIn }: { onSignedIn: (data: { access_token: string; refresh_token: string; user: User; daily_bonus_awarded: number }) => void }) {
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      const result = register ? await api.register(email, username, password) : await api.login(email, password);
      onSignedIn(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "認証に失敗しました。");
    } finally {
      setWorking(false);
    }
  }

  return (
    <form className="auth-panel glass" onSubmit={submit}>
      <div className="tab-switch">
        <button type="button" className={!register ? "active" : ""} onClick={() => setRegister(false)}>LOGIN</button>
        <button type="button" className={register ? "active" : ""} onClick={() => setRegister(true)}>CREATE</button>
      </div>
      <h2>{register ? "Create your signal ID" : "Enter the studio"}</h2>
      {register && <Field label="DISPLAY NAME" value={username} onChange={setUsername} placeholder="audio_creator" />}
      <Field label="EMAIL" value={email} onChange={setEmail} placeholder="you@studio.jp" type="email" />
      <Field label="PASSWORD" value={password} onChange={setPassword} placeholder="8文字以上" type="password" />
      {error && <p className="form-error">{error}</p>}
      <button className="neon-button" disabled={working}>{working ? "CONNECTING..." : register ? "START FREE / +20 PT" : "SIGN IN"}</button>
      <p className="fineprint">毎日の初回ログインで +10 PT。解析成功時のみ 5 PT を使用します。</p>
    </form>
  );
}

function Header({ user, page, onNavigate, onLogout }: { user: User; page: Page; onNavigate: (page: Page) => void; onLogout: () => void }) {
  const links: Array<[Page, string]> = [["dashboard", "DASHBOARD"], ["analyze", "ANALYZE"], ["history", "HISTORY"], ["pricing", "PRICING"], ["keys", "API KEYS"]];
  if (user.role === "ADMIN") links.push(["admin", "ADMIN"]);
  return (
    <header className="topbar glass">
      <Brand />
      <nav>{links.map(([target, label]) => <button key={target} className={page === target ? "selected" : ""} onClick={() => onNavigate(target)}>{label}</button>)}</nav>
      <div className="account">
        <div className="points"><b>{user.points_balance}</b><span>PT</span></div>
        <div><strong>{user.username}</strong><small>{user.role}</small></div>
        <button className="ghost" onClick={onLogout}>LOGOUT</button>
      </div>
    </header>
  );
}

function Dashboard({ user, onNavigate }: { user: User; onNavigate: (page: Page) => void }) {
  const [history, setHistory] = useState<Analysis[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  useEffect(() => {
    Promise.all([api.history(), api.transactions()]).then(([songs, points]) => {
      setHistory(songs.items);
      setTransactions(points);
    }).catch(() => undefined);
  }, []);
  const successful = history.filter((song) => song.status === "SUCCESS");
  const avgBpm = successful.length ? Math.round(successful.reduce((sum, song) => sum + Number(song.bpm ?? 0), 0) / successful.length) : "--";
  return (
    <>
      <section className="workspace-title">
        <div><p className="eyebrow">CONTROL CENTER</p><h1>Welcome, {user.username}</h1><p>解析キューとクリエイティブ資産を一望できます。</p></div>
        <button className="neon-button compact" onClick={() => onNavigate("analyze")}>NEW ANALYSIS</button>
      </section>
      <div className="metric-grid">
        <Metric label="POINT BALANCE" value={`${user.points_balance} PT`} accent="pink" />
        <Metric label="TOTAL ANALYSES" value={`${history.length}`} accent="blue" />
        <Metric label="AVERAGE BPM" value={`${avgBpm}`} accent="cyan" />
        <Metric label="CURRENT PLAN" value="FREE" accent="purple" />
      </div>
      <div className="dashboard-grid">
        <section className="panel glass"><PanelTitle title="RECENT TRACKS" action="VIEW ALL" onAction={() => onNavigate("history")} />
          <TrackRows rows={history.slice(0, 5)} empty="まだ解析データがありません。" />
        </section>
        <section className="panel glass"><PanelTitle title="POINT LEDGER" />
          <div className="ledger">{transactions.slice(0, 5).map((entry) => (
            <div key={entry.id}><span>{entry.description}</span><b className={entry.points_change > 0 ? "positive" : ""}>{entry.points_change > 0 ? "+" : ""}{entry.points_change}</b></div>
          ))}</div>
        </section>
      </div>
    </>
  );
}

function Analyze({ user, onUpdated, onNotice }: { user: User; onUpdated: () => Promise<void>; onNotice: (text: string) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");

  function receive(files: FileList | null) {
    if (files?.[0]) setFile(files[0]);
  }

  function dropped(event: DragEvent) {
    event.preventDefault();
    setDrag(false);
    receive(event.dataTransfer.files);
  }

  async function submit() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const analysis = await api.analyze(file);
      setResult(analysis);
      await onUpdated();
      onNotice("解析が完了しました。成功処理として 5 PT を使用しました。");
    } catch (reason) {
      setError(reason instanceof Error ? `${reason.message} ポイントは消費されていません。` : "解析に失敗しました。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="workspace-title"><div><p className="eyebrow">ANALYSIS LAB</p><h1>Decode a new track</h1><p>最大 50MB / 10分、MP3・WAV・FLAC・M4A 対応。</p></div><div className="cost-badge">BALANCE <b>{user.points_balance}</b> PT <span>-5 PT ON SUCCESS</span></div></section>
      <section className={`upload-zone glass ${drag ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={dropped} onClick={() => input.current?.click()}>
        <input ref={input} type="file" accept=".mp3,.wav,.flac,.m4a" onChange={(event) => receive(event.target.files)} hidden />
        <div className="upload-icon"><i /></div>
        <h2>{file ? file.name : "DROP YOUR AUDIO SIGNAL"}</h2>
        <p>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB / READY TO SCAN` : "クリックして選択、またはここへドラッグ&ドロップ"}</p>
        {file && <button className="neon-button compact" onClick={(event) => { event.stopPropagation(); submit(); }} disabled={loading}>{loading ? "SCANNING SIGNAL..." : "RUN ANALYSIS / 5 PT"}</button>}
      </section>
      {loading && <div className="analyzing glass"><WaveBars /><span>Extracting rhythm, key and spectral energy...</span></div>}
      {error && <p className="inline-error">{error}</p>}
      {result && <AnalysisResult result={result} />}
    </>
  );
}

function AnalysisResult({ result }: { result: Analysis }) {
  async function download() {
    const blob = await api.report(result.id);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `analysis-report-${result.id}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="result-suite">
      <div className="result-head"><p className="eyebrow">RESULT / {result.original_filename}</p><button className="outline-button" onClick={download}>EXPORT PDF</button></div>
      <div className="metric-grid result-metrics">
        <Metric label="BPM" value={`${result.bpm ?? "--"}`} accent="pink" />
        <Metric label="KEY" value={result.musical_key ?? "--"} accent="blue" />
        <Metric label="DURATION" value={`${result.duration_sec ?? "--"} s`} accent="cyan" />
        <Metric label="LUFS / RMS" value={`${result.lufs ?? "--"} / ${result.rms ?? "--"}`} accent="purple" />
      </div>
      <div className="visual-grid">
        <section className="panel glass"><PanelTitle title="WAVEFORM" /><Waveform values={result.waveform ?? []} /></section>
        <section className="panel glass"><PanelTitle title="SPECTROGRAM" /><Spectrogram values={result.spectrogram ?? []} /></section>
      </div>
    </section>
  );
}

function History() {
  const [rows, setRows] = useState<Analysis[]>([]);
  const [filename, setFilename] = useState("");
  const [key, setKey] = useState("");
  async function search(event?: FormEvent) {
    event?.preventDefault();
    const params = new URLSearchParams();
    if (filename) params.set("filename", filename);
    if (key) params.set("key", key);
    const query = params.toString();
    const data = await api.history(query ? `?${query}` : "");
    setRows(data.items);
  }
  useEffect(() => { search().catch(() => undefined); }, []);
  return (
    <>
      <section className="workspace-title"><div><p className="eyebrow">ARCHIVE</p><h1>Analysis history</h1><p>保存された解析結果とレポートを検索します。</p></div></section>
      <form className="filterbar glass" onSubmit={search}>
        <input value={filename} onChange={(event) => setFilename(event.target.value)} placeholder="ファイル名" />
        <input value={key} onChange={(event) => setKey(event.target.value)} placeholder="Key (例: C Major)" />
        <button className="outline-button">FILTER</button>
      </form>
      <section className="panel glass table-panel"><TrackRows rows={rows} empty="該当する解析結果がありません。" /></section>
    </>
  );
}

function Pricing({ onUpdated, onNotice }: { onUpdated: () => Promise<void>; onNotice: (text: string) => void }) {
  const [packages, setPackages] = useState<Package[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [coupon, setCoupon] = useState("");
  useEffect(() => { Promise.all([api.packages(), api.plans()]).then(([pointPacks, planRows]) => { setPackages(pointPacks); setPlans(planRows); }); }, []);
  async function purchase(item: Package) {
    try {
      const order = await api.order(item.id);
      await api.pay(order.id);
      await onUpdated();
      onNotice(`${item.points} PT の Mock Pay が完了しました。`);
    } catch (reason) {
      onNotice(reason instanceof Error ? reason.message : "購入処理に失敗しました。");
    }
  }
  async function applyCoupon() {
    try {
      await api.redeem(coupon);
      await onUpdated();
      setCoupon("");
      onNotice("クーポンポイントを反映しました。");
    } catch (reason) {
      onNotice(reason instanceof Error ? reason.message : "クーポンを利用できません。");
    }
  }
  async function selectPlan(plan: Plan) {
    await api.subscribe(plan.id);
    onNotice(`${plan.name} プランの状態を開始しました。`);
  }
  return (
    <>
      <section className="workspace-title"><div><p className="eyebrow">POWER UP</p><h1>Plans & points</h1><p>制作速度に合わせて解析容量を拡張できます。</p></div></section>
      <h2 className="section-caption">POINT PACKS / MOCK PAYMENT</h2>
      <section className="coupon-box glass"><input value={coupon} onChange={(event) => setCoupon(event.target.value)} placeholder="CAMPAIGN CODE" /><button className="outline-button" onClick={applyCoupon}>REDEEM</button></section>
      <div className="pricing-grid">{packages.map((item) => (
        <section className="price-card glass" key={item.id}><span>POINT BOOST</span><h2>{item.points}<small> PT</small></h2><p>¥{Number(item.price).toLocaleString()}</p><button className="neon-button compact" onClick={() => purchase(item)}>MOCK PAY</button></section>
      ))}</div>
      <h2 className="section-caption">SUBSCRIPTION MATRIX</h2>
      <div className="plan-grid">{plans.map((plan) => (
        <section className={`plan-card glass ${plan.name === "Pro" ? "recommended" : ""}`} key={plan.id}><strong>{plan.name}</strong><h2>¥{Number(plan.monthly_price).toLocaleString()}<small>/mo</small></h2><p>{plan.monthly_points} monthly points</p><p>API limit {plan.api_limit}</p><button className="ghost plan-action" onClick={() => selectPlan(plan)}>SELECT PLAN</button></section>
      ))}</div>
    </>
  );
}

function Keys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [usage, setUsage] = useState<ApiUsage[]>([]);
  const [issued, setIssued] = useState("");
  const [name, setName] = useState("Production Studio");
  async function load() {
    const [storedKeys, logs] = await Promise.all([api.keys(), api.keyUsage()]);
    setKeys(storedKeys);
    setUsage(logs);
  }
  useEffect(() => { load().catch(() => undefined); }, []);
  async function issue() {
    const key = await api.issueKey(name);
    setIssued(key.api_key ?? "");
    await load();
  }
  async function revoke(id: number) { await api.revokeKey(id); await load(); }
  return (
    <>
      <section className="workspace-title"><div><p className="eyebrow">DEVELOPER CONSOLE</p><h1>API Keys</h1><p>発行されたキーはハッシュ保存され、平文表示は発行時のみです。</p></div></section>
      <section className="key-create glass"><input value={name} onChange={(event) => setName(event.target.value)} /><button className="neon-button compact" onClick={issue}>ISSUE KEY</button></section>
      {issued && <div className="issued-key glass"><span>今回のみ表示</span><code>{issued}</code></div>}
      <section className="panel glass"><div className="key-list">{keys.map((key) => <div key={key.id}><code>{key.key_prefix}...</code><span>{key.name}</span><b>{key.status}</b>{key.status === "ACTIVE" && <button className="ghost" onClick={() => revoke(key.id)}>REVOKE</button>}</div>)}</div></section>
      <h2 className="section-caption">RECENT API USAGE</h2>
      <section className="panel glass"><div className="usage-list">{usage.map((item) => <div key={item.id}><code>{item.key_prefix}...</code><span>{item.endpoint}</span><b>{item.status_code}</b><strong>-{item.points_cost} PT</strong></div>)}</div></section>
    </>
  );
}

function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  async function load() { setUsers(await api.adminUsers()); }
  useEffect(() => { load().catch(() => undefined); }, []);
  async function toggleStatus(user: User) {
    await api.adminStatus(user.id, user.status === "ACTIVE" ? "DISABLED" : "ACTIVE");
    await load();
  }
  async function grant(user: User) {
    await api.adminPoints(user.id, 10);
    await load();
  }
  return (
    <>
      <section className="workspace-title"><div><p className="eyebrow">OPERATIONS</p><h1>Admin console</h1><p>ユーザー、残高、状態を監査する運用パネル。</p></div></section>
      <section className="panel glass admin-table">
        <div className="table-head"><span>USER</span><span>ROLE</span><span>STATUS</span><span>POINTS / ACTION</span></div>
        {users.map((user) => <div className="table-row" key={user.id}><span>{user.email}<small>{user.username}</small></span><span>{user.role}</span><button className="status-button" onClick={() => toggleStatus(user)}>{user.status}</button><div className="admin-actions"><b>{user.points_balance} PT</b><button className="ghost" onClick={() => grant(user)}>+10</button></div></div>)}
      </section>
    </>
  );
}

function Brand() {
  return (
    <div className="brand">
      <img src="/audio-analysis-logo.png" alt="Audio_Analysis_System logo" />
      <div>
        <strong>Audio_<span>Analysis_System</span></strong>
        <small>AUDIO INTELLIGENCE</small>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; type?: string }) {
  return <label className="field"><span>{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required /></label>;
}

function Metric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return <div className={`metric glass ${accent}`}><span>{label}</span><strong>{value}</strong><i /></div>;
}

function PanelTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return <header className="panel-title"><h2>{title}</h2>{action && <button onClick={onAction}>{action}</button>}</header>;
}

function TrackRows({ rows, empty }: { rows: Analysis[]; empty: string }) {
  if (!rows.length) return <p className="empty">{empty}</p>;
  return <div className="tracks">{rows.map((row) => (
    <div className="track" key={row.id}><div><strong>{row.original_filename}</strong><small>{new Date(row.created_at).toLocaleString("ja-JP")}</small></div><span className="tag">{row.bpm ?? "--"} BPM</span><span className="tag blue">{row.musical_key ?? row.status}</span></div>
  ))}</div>;
}

function WaveBars() {
  return <div className="wave-bars" aria-hidden="true">{Array.from({ length: 44 }, (_, index) => <i key={index} style={{ height: `${15 + Math.abs(Math.sin(index * 1.9)) * 75}%`, animationDelay: `${index * 0.035}s` }} />)}</div>;
}

function Waveform({ values }: { values: number[] }) {
  const path = useMemo(() => {
    if (!values.length) return "";
    return values.map((value, index) => `${index === 0 ? "M" : "L"} ${(index / (values.length - 1)) * 1000} ${100 - value * 90}`).join(" ");
  }, [values]);
  return <svg className="waveform" viewBox="0 0 1000 200" preserveAspectRatio="none"><path d={path} /></svg>;
}

function Spectrogram({ values }: { values: number[][] }) {
  const rows = values.filter((_, index) => index % 3 === 0);
  return <div className="spectrogram">{rows.flatMap((row, y) => row.filter((_, index) => index % 2 === 0).map((value, x) => {
    const energy = Math.max(0, Math.min(1, (value + 80) / 80));
    return <i key={`${y}-${x}`} style={{ backgroundColor: `hsl(${265 + energy * 70} ${80 + energy * 20}% ${12 + energy * 52}%)` }} />;
  }))}</div>;
}
