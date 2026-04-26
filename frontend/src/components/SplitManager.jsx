import { useGameStore } from '../store/gameStore'

export function SplitManager() {
  const { inSplit, splitHands, activeSplitHand, setTarget } = useGameStore()
  if (!inSplit) return null

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-purple-400 mb-4">
        ✌️ Manos Divididas
      </h3>

      <div className="grid grid-cols-2 gap-3">
        {splitHands.map((hand, idx) => {
          const isActive = activeSplitHand === idx
          const total = calcTotal(hand)

          return (
            <div
              key={idx}
              onClick={() => setTarget(`split_${idx}`)}
              className={`rounded-xl p-3 cursor-pointer transition-all duration-200 ${
                isActive
                  ? 'bg-purple-500/15 border-2 border-purple-400/50 shadow-lg shadow-purple-500/10'
                  : 'bg-white/5 border border-white/10 hover:bg-white/8'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-400">Mano {idx + 1}</span>
                {hand.length >= 2 && (
                  <span className="text-xs px-2 py-0.5 bg-white/10 rounded-full text-white/70">
                    {total}
                  </span>
                )}
              </div>
              <div className="flex gap-1 flex-wrap">
                {hand.map((card, i) => (
                  <span key={i} className="inline-flex items-center justify-center w-8 h-10
                                          bg-white text-gray-900 rounded text-xs font-bold shadow">
                    {card}
                  </span>
                ))}
                {hand.length < 2 && (
                  <span className="inline-flex items-center justify-center w-8 h-10
                                  border border-dashed border-white/20 rounded text-white/20 text-xs">
                    ?
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function calcTotal(cards) {
  let total = 0, aces = 0
  for (const r of cards) {
    if (r === 'A') { aces++; total += 11 }
    else if (['K','Q','J'].includes(r)) total += 10
    else total += parseInt(r)
  }
  while (total > 21 && aces > 0) { total -= 10; aces-- }
  return total
}
