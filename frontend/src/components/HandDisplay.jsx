import { useGameStore } from '../store/gameStore'

const CARD_DISPLAY = {
  'A': { symbol: 'A', suit: '♠' },
  '2': { symbol: '2', suit: '♥' }, '3': { symbol: '3', suit: '♦' },
  '4': { symbol: '4', suit: '♣' }, '5': { symbol: '5', suit: '♠' },
  '6': { symbol: '6', suit: '♥' }, '7': { symbol: '7', suit: '♦' },
  '8': { symbol: '8', suit: '♣' }, '9': { symbol: '9', suit: '♠' },
  '10': { symbol: '10', suit: '♥' }, 'J': { symbol: 'J', suit: '♦' },
  'Q': { symbol: 'Q', suit: '♣' }, 'K': { symbol: 'K', suit: '♠' },
}

function MiniCard({ rank, onClick, index }) {
  const display = CARD_DISPLAY[rank] || { symbol: rank, suit: '♠' }
  const isRed = ['♥','♦'].includes(display.suit)

  return (
    <div
      onClick={onClick}
      className="animate-slide-in relative w-14 h-20 rounded-lg bg-white shadow-lg
                 flex flex-col items-center justify-center cursor-pointer
                 hover:shadow-xl hover:-translate-y-1 transition-all duration-200
                 border border-gray-200 group"
      style={{ animationDelay: `${index * 80}ms` }}
      title="Click para deshacer"
    >
      <span className={`text-lg font-bold ${isRed ? 'text-red-600' : 'text-gray-900'}`}>
        {display.symbol}
      </span>
      <span className={`text-xs ${isRed ? 'text-red-400' : 'text-gray-400'}`}>
        {display.suit}
      </span>
      <div className="absolute inset-0 rounded-lg bg-red-500/0 group-hover:bg-red-500/10 transition-colors
                      flex items-center justify-center opacity-0 group-hover:opacity-100">
        <span className="text-red-500 text-xs font-bold">✕</span>
      </div>
    </div>
  )
}

function EmptySlot({ label }) {
  return (
    <div className="w-14 h-20 rounded-lg border-2 border-dashed border-white/15
                    flex items-center justify-center">
      <span className="text-white/20 text-xs">{label}</span>
    </div>
  )
}

export function HandDisplay() {
  const { playerCards, dealerCard, removeCard, setTarget, target } = useGameStore()

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Dealer */}
      <div
        onClick={() => setTarget('dealer')}
        className={`glass rounded-2xl p-4 cursor-pointer transition-all duration-200 ${
          target === 'dealer' ? 'ring-2 ring-amber-400/60 shadow-lg shadow-amber-400/10' : 'hover:bg-white/8'
        }`}
      >
        <div className="flex items-center gap-2 mb-3">
          <span className="text-amber-400 text-sm">🎰</span>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-amber-400">Dealer</h3>
          {target === 'dealer' && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 ml-auto">
              ACTIVO
            </span>
          )}
        </div>
        <div className="flex gap-2 min-h-[80px] items-center">
          {dealerCard ? (
            <>
              <MiniCard rank={dealerCard} onClick={() => removeCard(dealerCard, 'dealer')} index={0} />
              <div className="w-14 h-20 rounded-lg bg-gradient-to-br from-blue-800 to-blue-950
                              border border-blue-700 flex items-center justify-center shadow-lg">
                <span className="text-blue-400 text-xl">?</span>
              </div>
            </>
          ) : (
            <>
              <EmptySlot label="1" />
              <EmptySlot label="?" />
            </>
          )}
        </div>
      </div>

      {/* Player */}
      <div
        onClick={() => setTarget('player')}
        className={`glass rounded-2xl p-4 cursor-pointer transition-all duration-200 ${
          target === 'player' ? 'ring-2 ring-emerald-400/60 shadow-lg shadow-emerald-400/10' : 'hover:bg-white/8'
        }`}
      >
        <div className="flex items-center gap-2 mb-3">
          <span className="text-emerald-400 text-sm">🃏</span>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400">Tu Mano</h3>
          {target === 'player' && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 ml-auto">
              ACTIVO
            </span>
          )}
          {playerCards.length >= 2 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-white/70 ml-auto">
              Total: {calcTotal(playerCards)}
            </span>
          )}
        </div>
        <div className="flex gap-2 min-h-[80px] items-center flex-wrap">
          {playerCards.length > 0 ? (
            playerCards.map((c, i) => (
              <MiniCard key={i} rank={c} onClick={() => removeCard(c, 'player')} index={i} />
            ))
          ) : (
            <>
              <EmptySlot label="1" />
              <EmptySlot label="2" />
            </>
          )}
        </div>
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
