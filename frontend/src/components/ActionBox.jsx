import { useGameStore } from '../store/gameStore'

const ACTION_CONFIG = {
  H:  { label: 'PEDIR (Hit)',          bg: 'rgba(34,197,94,0.15)',  border: '#22c55e', color: '#4ade80', icon: '👆' },
  S:  { label: 'PLANTARSE (Stand)',    bg: 'rgba(59,130,246,0.15)', border: '#3b82f6', color: '#60a5fa', icon: '✋' },
  D:  { label: 'DOBLAR (Double Down)', bg: 'rgba(245,158,11,0.15)', border: '#f59e0b', color: '#fbbf24', icon: '💰' },
  Ds: { label: 'DOBLAR (Double Down)', bg: 'rgba(245,158,11,0.15)', border: '#f59e0b', color: '#fbbf24', icon: '💰' },
  P:  { label: 'DIVIDIR (Split)',      bg: 'rgba(139,92,246,0.15)', border: '#8b5cf6', color: '#a78bfa', icon: '✌️' },
  R:  { label: 'RENDIRSE (Surrender)', bg: 'rgba(239,68,68,0.15)',  border: '#ef4444', color: '#f87171', icon: '🏳️' },
}

export function ActionBox() {
  const { recommendation, isLoading, enterSplit } = useGameStore()

  if (isLoading) return (
    <div className="glass rounded-2xl p-6 text-center">
      <div className="animate-shimmer rounded-xl h-20 w-full"></div>
      <p className="text-gray-500 text-sm mt-3">Calculando estrategia...</p>
    </div>
  )

  if (!recommendation) return (
    <div className="glass rounded-2xl p-6 text-center">
      <div className="text-4xl mb-3 opacity-30">🃏</div>
      <p className="text-gray-400 text-sm">
        Registra las cartas del jugador y dealer para ver la recomendacion
      </p>
      <p className="text-gray-600 text-xs mt-1">Minimo: 2 cartas del jugador + 1 del dealer</p>
    </div>
  )

  const cfg = ACTION_CONFIG[recommendation.action] || ACTION_CONFIG.H

  return (
    <div
      className="rounded-2xl border-2 p-5 text-center transition-all duration-300 animate-slide-in"
      style={{ background: cfg.bg, borderColor: cfg.border }}
    >
      <div className="text-3xl mb-2">{cfg.icon}</div>
      <h2 className="text-2xl font-bold mb-2" style={{ color: cfg.color }}>
        {cfg.label}
      </h2>
      <p className="text-sm text-gray-300 leading-relaxed">{recommendation.reason}</p>

      {recommendation.deviation_applied && (
        <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs
                        bg-purple-500/20 text-purple-300 rounded-full border border-purple-500/30">
          <span>⚡</span>
          <span>Desviacion por conteo aplicada</span>
        </div>
      )}

      {recommendation.action === 'P' && (
        <button
          onClick={enterSplit}
          className="mt-4 px-5 py-2 text-sm border border-purple-400/40 text-purple-300
                     rounded-xl hover:bg-purple-500/10 transition-all cursor-pointer"
        >
          Simular split →
        </button>
      )}

      <div className="mt-4 flex justify-center gap-4 text-xs text-gray-500">
        <span>Total: {recommendation.player_total}</span>
        <span>{recommendation.is_soft ? 'Blanda' : 'Dura'}</span>
        {recommendation.is_pair && <span>Par</span>}
      </div>
    </div>
  )
}
