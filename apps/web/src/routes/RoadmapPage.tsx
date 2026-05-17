import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type Item = { text: string; done: boolean }
type Phase = {
  id: number
  title: string
  status: 'active' | 'upcoming'
  goal: string
  items: Item[]
  gate?: string
  extra?: React.ReactNode
}

const phases: Phase[] = [
  {
    id: 1,
    title: 'Measurement Hardening',
    status: 'active',
    goal: 'Semua angka yang tampil di dashboard mencerminkan realita, bukan artefak implementasi.',
    items: [
      { text: 'Deterministic eval pass — eval selalu mulai dari anchor index yang tetap, bukan random', done: true },
      { text: 'Eval env terpisah dari train env — chronological split diterapkan sampai ke evaluation loop', done: true },
      { text: 'Richer executed-trade ledger — catat entry price, exit price, realized PnL, hold duration per trade', done: true },
      { text: 'Replay/history konsisten antara env, trainer, backend, dan frontend', done: true },
    ],
    gate: 'Sharpe di dashboard harus reproducible — run ulang dengan checkpoint yang sama harus menghasilkan angka yang sama.',
  },
  {
    id: 2,
    title: 'Agent Quality Pass',
    status: 'upcoming',
    goal: 'Policy belajar perilaku trading yang masuk akal, bukan exploit noise atau bias data.',
    items: [
      { text: 'Audit reward design — pastikan rolling Sharpe tidak inflate dari episode pendek atau data homogen', done: false },
      { text: 'Overtrading fix — action penalty + cooldown supaya Txns per episode berada di range 4–20', done: false },
      { text: 'Action constraints — action masking yang benar untuk MultiDiscrete([3, 4])', done: false },
      { text: 'Hyperparameter sweep — n_steps, ent_coef, clip_range, episode_length via W&B', done: false },
      { text: 'Baseline benchmark — agent harus konsisten mengalahkan random agent dan buy-and-hold', done: false },
    ],
    gate: 'Sharpe eval out-of-sample > 1.0 secara konsisten selama 50+ generasi berturut-turut tanpa spike ekstrem.',
  },
  {
    id: 3,
    title: 'Research Workflow',
    status: 'upcoming',
    goal: 'Infrastruktur eksperimen yang memungkinkan iterasi cepat dan reproducible.',
    items: [
      { text: 'Run comparison — bandingkan dua checkpoint atau dua config secara visual di dashboard', done: false },
      { text: 'Checkpoint lineage — visualisasi pohon generasi: mana yang dipromosikan, mana yang tidak', done: false },
      { text: 'Experiment presets — simpan dan load konfigurasi hyperparameter sebagai named preset', done: false },
      { text: 'W&B sweep integration — otomasi hyperparameter search', done: false },
      { text: 'Notebook experiment environment — Jupyter notebook standalone untuk rapid prototyping', done: false },
    ],
  },
  {
    id: 4,
    title: 'Backtesting & Analysis',
    status: 'upcoming',
    goal: 'Validasi checkpoint di data historis yang benar-benar baru sebelum forward test.',
    items: [
      { text: 'Backtest runner — putar checkpoint di arbitrary date range dengan data historis', done: false },
      { text: 'Equity curve & drawdown chart per backtest run', done: false },
      { text: 'Trade breakdown — entry/exit/hold duration/PnL per trade dalam tabel', done: false },
      { text: 'Walk-forward validation — eval bergeser seiring waktu, bukan satu slice statis', done: false },
      { text: 'Comparison vs buy-and-hold benchmark di periode yang sama', done: false },
    ],
    gate: 'Agent profitable di minimal 3 backtest window yang berbeda (bull, bear, sideways).',
  },
  {
    id: 5,
    title: 'Deployment-Grade Execution',
    status: 'upcoming',
    goal: 'Agent siap dijalankan di market nyata dengan safeguard yang memadai.',
    items: [
      { text: 'Paper trading — jalankan agent di Binance Testnet minimal 30 hari sebelum uang nyata', done: false },
      { text: 'Risk guardrails — daily drawdown > 10% → sistem mati; consecutive losses > 5 → pause; koneksi putus > 30s → force close', done: false },
      { text: 'Conservative order sizing — mulai dari 5–10% modal per trade', done: false },
      { text: 'Execution layer — rate limit handling, order retry, partial fill reconciliation', done: false },
      { text: 'Alert system — notifikasi Telegram/email untuk setiap anomali', done: false },
    ],
    gate: 'Paper trading profitable selama 30 hari kalender, Sharpe > 1.0, max drawdown < 15%.',
  },
  {
    id: 6,
    title: 'Scale-Out',
    status: 'upcoming',
    goal: 'Perluas ke multi-asset dan multi-timeframe jika loop single-symbol sudah stabil.',
    items: [
      { text: 'Multi-asset — latih agent terpisah per pair (ETH/USDT, SOL/USDT, dll)', done: false },
      { text: 'Multi-timeframe — ensemble agent 15m + 1h untuk konfirmasi sinyal', done: false },
      { text: 'Training orchestration — paralel training di beberapa GPU/mesin', done: false },
      { text: 'Portfolio-level risk management — korelasi antar posisi, total exposure cap', done: false },
    ],
  },
]

export default function RoadmapPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-2 p-6">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold tracking-tight">Roadmap</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          TradingZero dikembangkan dalam enam fase. Setiap fase harus selesai dan stabil sebelum lanjut ke fase berikutnya.
        </p>
      </div>

      <div className="relative space-y-4">
        {/* vertical timeline line */}
        <div className="absolute left-[19px] top-6 bottom-6 w-px bg-border" aria-hidden="true" />

        {phases.map((phase) => (
          <PhaseCard key={phase.id} phase={phase} />
        ))}
      </div>
    </div>
  )
}

function PhaseCard({ phase }: { phase: Phase }) {
  const doneCount = phase.items.filter((i) => i.done).length
  const total = phase.items.length

  return (
    <div className="relative flex gap-4">
      {/* dot */}
      <div
        className={cn(
          'relative z-10 mt-1 flex size-10 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold',
          phase.status === 'active'
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-border bg-background text-muted-foreground',
        )}
      >
        {phase.id}
      </div>

      <div className="flex-1 rounded-lg border border-border bg-card p-4 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">
            Fase {phase.id} — {phase.title}
          </h2>
          {phase.status === 'active' && (
            <Badge variant="default" className="text-xs">
              aktif
            </Badge>
          )}
          <span className="ml-auto text-xs text-muted-foreground">
            {doneCount}/{total}
          </span>
        </div>

        <p className="mt-1 text-sm text-muted-foreground">{phase.goal}</p>

        <ul className="mt-3 space-y-1.5">
          {phase.items.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span
                className={cn(
                  'mt-0.5 size-4 shrink-0 rounded-sm border text-center text-[10px] leading-4',
                  item.done
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-muted-foreground/40 text-transparent',
                )}
              >
                ✓
              </span>
              <span className={cn(item.done && 'text-muted-foreground line-through')}>{item.text}</span>
            </li>
          ))}
        </ul>

        {phase.gate && (
          <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-400">
            <span className="font-semibold">Gate: </span>
            {phase.gate}
          </div>
        )}
      </div>
    </div>
  )
}
