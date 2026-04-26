import { useGameStore } from '../store/gameStore'

export function InsuranceBox() {
  const { insurance } = useGameStore()
  if (!insurance) return null

  const isConsider = insurance.type === 'consider'

  return (
    <div className={`rounded-2xl border p-4 transition-all duration-300 animate-slide-in ${
      isConsider
        ? 'bg-amber-500/10 border-amber-500/30'
        : 'bg-blue-500/10 border-blue-500/30'
    }`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{isConsider ? '🛡️' : '❌'}</span>
        <h4 className={`font-bold text-sm ${
          isConsider ? 'text-amber-300' : 'text-blue-300'
        }`}>
          {insurance.verdict}
        </h4>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">
        {insurance.reason}
      </p>
    </div>
  )
}
