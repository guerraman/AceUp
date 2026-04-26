import { useGameStore } from '../store/gameStore'

export function BetAdvisor() {
  const { betAdvice, trueCount } = useGameStore()
  if (!betAdvice) return null

  const isWong = betAdvice.units === 0
  const isFav = trueCount >= 3
  const isUnfav = trueCount <= -3

  const bgClass = isWong ? 'bg-red-500/10 border-red-500/30' :
                  isFav ? 'bg-green-500/10 border-green-500/30' :
                  isUnfav ? 'bg-orange-500/10 border-orange-500/30' :
                  'bg-white/5 border-white/10'

  const iconMap = {
    wong: '🚫',
    fav: '🔥',
    unfav: '⚠️',
    normal: '💰'
  }
  const icon = isWong ? iconMap.wong : isFav ? iconMap.fav : isUnfav ? iconMap.unfav : iconMap.normal

  return (
    <div className={`glass rounded-2xl p-5 border ${bgClass}`}>
      <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400 mb-3">
        Apuesta Recomendada
      </h3>

      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="font-bold text-white">
            {isWong
              ? 'Abandona la mesa'
              : `${betAdvice.units} unidad${betAdvice.units !== 1 ? 'es' : ''}`
            }
          </p>
          {!isWong && betAdvice.amount > 0 && (
            <p className="text-sm text-gray-400">
              ${betAdvice.amount.toFixed(2)}
            </p>
          )}
        </div>
      </div>

      <p className="text-xs text-gray-500">{betAdvice.message}</p>

      {betAdvice.edge_pct > 0 && (
        <div className="mt-2 flex items-center gap-1.5">
          <span className="text-xs text-green-400">↑ Ventaja: +{betAdvice.edge_pct}%</span>
        </div>
      )}

      {betAdvice.kelly_pct > 0 && (
        <p className="text-[10px] text-gray-600 mt-1">
          Kelly 0.5x: {betAdvice.kelly_pct}% del bankroll
        </p>
      )}
    </div>
  )
}
