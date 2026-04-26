import { useGameStore } from '../store/gameStore'

const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

export function ShoeBar() {
  const { shoe } = useGameStore()
  if (!shoe || Object.keys(shoe).length === 0) return null

  const maxPerRank = 24

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400 mb-4">
        Estado del Mazo
      </h3>
      <div className="space-y-1.5">
        {RANKS.map(rank => {
          const remaining = shoe[rank] ?? 0
          const pct = (remaining / maxPerRank) * 100
          const barColor = pct > 60 ? 'bg-emerald-500' :
                          pct > 30 ? 'bg-amber-500' : 'bg-red-500'

          return (
            <div key={rank} className="flex items-center gap-2">
              <span className="w-6 text-right text-xs font-mono text-gray-400">{rank}</span>
              <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-5 text-right text-[10px] font-mono text-gray-500">{remaining}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
