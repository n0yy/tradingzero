import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { fetchActiveConfig, saveActiveConfig } from '@/lib/api'
import { useUIStore } from '../store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
}

function ConfigGroup({ legend, children }: { legend: string; children: React.ReactNode }) {
  return (
    <fieldset
      aria-label={legend}
      className="grid gap-3 rounded-xl border border-border bg-card p-4"
    >
      <legend className="px-2 font-display text-sm font-semibold tracking-wide text-foreground">
        {legend}
      </legend>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{children}</div>
    </fieldset>
  )
}

function FieldLabel({
  label,
  name,
  defaultValue,
  type = 'text',
  step,
}: {
  label: string
  name: string
  defaultValue: string | number
  type?: 'text' | 'number'
  step?: string
}) {
  return (
    <label className="grid gap-1 text-xs text-muted-foreground">
      <span>{label}</span>
      <input
        name={name}
        type={type}
        step={step}
        defaultValue={defaultValue}
        className="rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      />
    </label>
  )
}

export default function ConfigPage() {
  const qc = useQueryClient()
  const timeMode = useUIStore((s) => s.timeMode)

  const activeConfigQuery = useQuery({
    queryKey: ['active-config'],
    queryFn: fetchActiveConfig,
    refetchInterval: 7000,
  })
  const saveConfigMutation = useMutation({
    mutationFn: saveActiveConfig,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['active-config'] })
    },
  })

  return (
    <main className="dashboard">
      <header className="topbar">
        <h1>Config</h1>
        <p className="text-xs text-muted-foreground">
          Active version: {activeConfigQuery.data?.version ?? '—'} · Updated{' '}
          {formatTimestamp(activeConfigQuery.data?.created_at ?? null, timeMode)}
        </p>
      </header>

      {activeConfigQuery.data?.config ? (
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            const form = new FormData(e.currentTarget)
            saveConfigMutation.mutate({
              data: {
                exchange: String(form.get('data.exchange') || ''),
                symbol: String(form.get('data.symbol') || ''),
                timeframe: String(form.get('data.timeframe') || ''),
                window_size: Number(form.get('data.window_size') || 0),
              },
              env: {
                initial_balance: Number(form.get('env.initial_balance') || 0),
                transaction_cost: Number(form.get('env.transaction_cost') || 0),
                episode_length: Number(form.get('env.episode_length') || 0),
              },
              agent: {
                learning_rate: Number(form.get('agent.learning_rate') || 0),
                n_steps: Number(form.get('agent.n_steps') || 0),
                batch_size: Number(form.get('agent.batch_size') || 0),
                clip_range: Number(form.get('agent.clip_range') || 0),
                total_episodes: Number(form.get('agent.total_episodes') || 0),
                promote_threshold: Number(form.get('agent.promote_threshold') || 0),
              },
              self_play: {
                checkpoint_interval: Number(form.get('self_play.checkpoint_interval') || 0),
                checkpoint_dir: String(form.get('self_play.checkpoint_dir') || ''),
              },
            })
          }}
        >
          <ConfigGroup legend="Data">
            <FieldLabel label="Exchange" name="data.exchange" defaultValue={activeConfigQuery.data.config.data.exchange} />
            <FieldLabel label="Symbol" name="data.symbol" defaultValue={activeConfigQuery.data.config.data.symbol} />
            <FieldLabel label="Timeframe" name="data.timeframe" defaultValue={activeConfigQuery.data.config.data.timeframe} />
            <FieldLabel label="Window size" name="data.window_size" type="number" defaultValue={activeConfigQuery.data.config.data.window_size} />
          </ConfigGroup>

          <ConfigGroup legend="Environment">
            <FieldLabel label="Initial balance" name="env.initial_balance" type="number" step="0.01" defaultValue={activeConfigQuery.data.config.env.initial_balance} />
            <FieldLabel label="Transaction cost" name="env.transaction_cost" type="number" step="0.0001" defaultValue={activeConfigQuery.data.config.env.transaction_cost} />
            <FieldLabel label="Episode length" name="env.episode_length" type="number" defaultValue={activeConfigQuery.data.config.env.episode_length} />
          </ConfigGroup>

          <ConfigGroup legend="Agent">
            <FieldLabel label="Learning rate" name="agent.learning_rate" type="number" step="0.00001" defaultValue={activeConfigQuery.data.config.agent.learning_rate} />
            <FieldLabel label="n_steps" name="agent.n_steps" type="number" defaultValue={activeConfigQuery.data.config.agent.n_steps} />
            <FieldLabel label="Batch size" name="agent.batch_size" type="number" defaultValue={activeConfigQuery.data.config.agent.batch_size} />
            <FieldLabel label="Clip range" name="agent.clip_range" type="number" step="0.01" defaultValue={activeConfigQuery.data.config.agent.clip_range} />
            <FieldLabel label="Total episodes" name="agent.total_episodes" type="number" defaultValue={activeConfigQuery.data.config.agent.total_episodes} />
            <FieldLabel label="Promote threshold" name="agent.promote_threshold" type="number" step="0.01" defaultValue={activeConfigQuery.data.config.agent.promote_threshold} />
          </ConfigGroup>

          <ConfigGroup legend="Self-play">
            <FieldLabel label="Checkpoint interval" name="self_play.checkpoint_interval" type="number" defaultValue={activeConfigQuery.data.config.self_play.checkpoint_interval} />
            <FieldLabel label="Checkpoint dir" name="self_play.checkpoint_dir" defaultValue={activeConfigQuery.data.config.self_play.checkpoint_dir} />
          </ConfigGroup>

          <div className="flex items-center justify-end gap-3">
            {saveConfigMutation.isError && <p className="text-sm text-loss">Save failed. Check the values.</p>}
            {saveConfigMutation.isSuccess && <p className="text-sm text-gain">Revision saved.</p>}
            <Button type="submit" disabled={saveConfigMutation.isPending}>
              {saveConfigMutation.isPending ? 'Saving...' : 'Save Revision'}
            </Button>
          </div>
        </form>
      ) : (
        <p className="text-sm text-muted-foreground">No active config yet.</p>
      )}
    </main>
  )
}
