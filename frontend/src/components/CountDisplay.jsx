import { useGameStore } from '../store/gameStore'

export function CountDisplay() {
  const { runningCount, trueCount, shoe, handsPlayed } = useGameStore()

  const cardsLeft = shoe ? Object.values(shoe).reduce((a, b) => a + b, 0) : 312
  const decksRem = Math.max(0.5, cardsLeft / 52)
  const penetration = ((312 - cardsLeft) / 312 * 100).toFixed(0)

  const tcColor = trueCount >= 3 ? 'text-green-400' :
                  trueCount >= 1 ? 'text-emerald-400' :
                  trueCount <= -2 ? 'text-red-400' :
                  trueCount < 0 ? 'text-orange-400' : 'text-gray-300'

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400 mb-4">
        Conteo Hi-Lo
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white/5 rounded-xl p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Running</p>
          <p className={`text-2xl font-bold font-mono ${runningCount > 0 ? 'text-green-400' : runningCount < 0 ? 'text-red-400' : 'text-gray-300'}`}>
            {runningCount > 0 ? '+' : ''}{runningCount}
          </p>
        </div>

        <div className="bg-white/5 rounded-xl p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">True Count</p>
          <p className={`text-2xl font-bold font-mono ${tcColor}`}>
            {trueCount > 0 ? '+' : ''}{typeof trueCount === 'number' ? trueCount.toFixed(1) : '0.0'}
          </p>
        </div>

        <div className="bg-white/5 rounded-xl p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Cartas</p>
          <p className="text-lg font-bold text-gray-200 font-mono">{cardsLeft}<span className="text-gray-600">/312</span></p>
        </div>

        <div className="bg-white/5 rounded-xl p-3 text-center">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Mazos</p>
          <p className="text-lg font-bold text-gray-200 font-mono">{decksRem.toFixed(1)}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
        <span>Penetracion: {penetration}%</span>
        <span>Manos: {handsPlayed}</span>
      </div>

      {/* Penetration bar */}
      <div className="mt-2 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${penetration}%`,
            background: parseInt(penetration) > 75 ? '#ef4444' :
                        parseInt(penetration) > 50 ? '#f59e0b' : '#10b981'
          }}
        />
      </div>
    </div>
  )
}
