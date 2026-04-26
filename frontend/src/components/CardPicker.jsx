import { useGameStore } from '../store/gameStore'

const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

const SUIT_SYMBOLS = {
  high: { icon: '♠', color: '#ef4444' },
  low: { icon: '♦', color: '#3b82f6' },
  neutral: { icon: '♣', color: '#a3a3a3' },
}

function getCountType(rank) {
  if (['2','3','4','5','6'].includes(rank)) return 'low'
  if (['10','J','Q','K','A'].includes(rank)) return 'high'
  return 'neutral'
}

export function CardPicker() {
  const { shoe, addCard, target } = useGameStore()

  const targetLabels = {
    player: 'Jugador',
    dealer: 'Dealer',
    split_0: 'Split Mano 1',
    split_1: 'Split Mano 2',
  }

  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400">
          Seleccionar Carta
        </h3>
        <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          → {targetLabels[target] || target}
        </span>
      </div>

      <div className="grid grid-cols-5 sm:grid-cols-7 lg:grid-cols-13 gap-2">
        {RANKS.map((rank) => {
          const remaining = shoe[rank] ?? 0
          const depleted = remaining <= 0
          const countType = getCountType(rank)
          const countColors = {
            low: 'border-blue-400/50 hover:border-blue-400 hover:shadow-blue-400/20',
            high: 'border-red-400/50 hover:border-red-400 hover:shadow-red-400/20',
            neutral: 'border-gray-500/50 hover:border-gray-400 hover:shadow-gray-400/20',
          }

          return (
            <button
              key={rank}
              onClick={() => !depleted && addCard(rank)}
              disabled={depleted}
              className={`
                relative flex flex-col items-center justify-center
                rounded-xl border-2 p-2.5 min-h-[72px]
                transition-all duration-200 cursor-pointer
                ${depleted
                  ? 'opacity-25 cursor-not-allowed border-gray-700 bg-gray-900/50'
                  : `bg-white/5 ${countColors[countType]} hover:bg-white/10 hover:scale-105 hover:shadow-lg active:scale-95`
                }
              `}
            >
              <span className={`text-lg font-bold ${
                countType === 'low' ? 'text-blue-300' :
                countType === 'high' ? 'text-red-300' :
                'text-gray-300'
              }`}>
                {rank}
              </span>
              <span className="text-[10px] mt-1 text-gray-500 font-mono">
                {remaining}
              </span>
            </button>
          )
        })}
      </div>

      <div className="flex items-center gap-4 mt-3 text-[10px] text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-400"></span> +1 (Low)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-gray-400"></span> 0 (Neutral)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-400"></span> -1 (High)
        </span>
      </div>
    </div>
  )
}
