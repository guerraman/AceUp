import { useEffect, useState } from 'react'
import { useGameStore } from './store/gameStore'
import { CardPicker } from './components/CardPicker'
import { HandDisplay } from './components/HandDisplay'
import { ActionBox } from './components/ActionBox'
import { CountDisplay } from './components/CountDisplay'
import { ShoeBar } from './components/ShoeBar'
import { BetAdvisor } from './components/BetAdvisor'
import { InsuranceBox } from './components/InsuranceBox'
import { SplitManager } from './components/SplitManager'
import { AIAdvisor } from './components/AIAdvisor'
import './index.css'

function App() {
  const {
    initSession, sessionId, nextHand, finishGame,
    bankroll, setBankroll, minBet, setMinBet,
    error, clearError,
    playerCards, dealerCard, fetchAIRecommendation
  } = useGameStore()

  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    initSession()
  }, [])

  useEffect(() => {
    fetchAIRecommendation()
  }, [playerCards, dealerCard])

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 glass-dark border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600
                            flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <span className="text-white font-bold text-lg">A</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">AceUp</h1>
              <p className="text-[10px] text-emerald-400/60 uppercase tracking-widest">Blackjack Assistant</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="px-3 py-1.5 text-xs rounded-lg bg-white/5 text-gray-400
                         hover:bg-white/10 hover:text-white transition-all cursor-pointer
                         border border-white/5"
            >
              ⚙️ Config
            </button>
            <button
              onClick={nextHand}
              className="px-4 py-1.5 text-xs font-medium rounded-lg
                         bg-emerald-500/20 text-emerald-300 border border-emerald-500/30
                         hover:bg-emerald-500/30 transition-all cursor-pointer"
            >
              Siguiente Mano →
            </button>
            <button
              onClick={finishGame}
              className="px-4 py-1.5 text-xs font-medium rounded-lg
                         bg-red-500/10 text-red-400 border border-red-500/20
                         hover:bg-red-500/20 transition-all cursor-pointer"
            >
              Finalizar
            </button>
          </div>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="border-t border-white/5 bg-black/20">
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Bankroll $</label>
                <input
                  type="number"
                  value={bankroll}
                  onChange={e => setBankroll(Number(e.target.value))}
                  className="w-24 px-2 py-1 text-sm bg-white/5 border border-white/10
                             rounded-lg text-white outline-none focus:border-emerald-500/50"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Apuesta min $</label>
                <input
                  type="number"
                  value={minBet}
                  onChange={e => setMinBet(Number(e.target.value))}
                  className="w-20 px-2 py-1 text-sm bg-white/5 border border-white/10
                             rounded-lg text-white outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Error Toast */}
      {error && (
        <div className="fixed top-20 right-4 z-50 animate-slide-in">
          <div className="bg-red-500/90 text-white px-4 py-2 rounded-xl shadow-lg flex items-center gap-3">
            <span className="text-sm">{error}</span>
            <button onClick={clearError} className="text-white/60 hover:text-white cursor-pointer">✕</button>
          </div>
        </div>
      )}

      {/* Connection status */}
      {!sessionId && (
        <div className="max-w-7xl mx-auto px-4 mt-4">
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
            <p className="text-amber-300 text-sm">
              ⏳ Conectando con el servidor... Asegurate de que el backend este corriendo en puerto 8000
            </p>
          </div>
        </div>
      )}

      {/* Main Layout */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

          {/* Left Column - Count & Shoe */}
          <div className="lg:col-span-3 space-y-5">
            <CountDisplay />
            <BetAdvisor />
            <ShoeBar />
          </div>

          {/* Center Column - Hands & Cards */}
          <div className="lg:col-span-6 space-y-5">
            <HandDisplay />
            <SplitManager />
            <AIAdvisor />
            <ActionBox />
            <InsuranceBox />
            <CardPicker />
          </div>

          {/* Right Column - Info */}
          <div className="lg:col-span-3 space-y-5">
            <QuickGuide />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-gray-600">
        <p>AceUp — Asistente de Blackjack con conteo Hi-Lo</p>
        <p className="mt-1">Estrategia Basica + Illustrious 18 + Fab 4 | 6 Mazos S17 DAS</p>
      </footer>
    </div>
  )
}


function QuickGuide() {
  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-emerald-400 mb-3">
        Guia Rapida
      </h3>
      <div className="space-y-3 text-xs text-gray-400">
        <div className="flex gap-2">
          <span className="text-emerald-400 mt-0.5">1.</span>
          <p>Haz click en <span className="text-white">"Tu Mano"</span> o <span className="text-white">"Dealer"</span> para seleccionar donde registrar</p>
        </div>
        <div className="flex gap-2">
          <span className="text-emerald-400 mt-0.5">2.</span>
          <p>Selecciona las cartas que se repartieron del selector inferior</p>
        </div>
        <div className="flex gap-2">
          <span className="text-emerald-400 mt-0.5">3.</span>
          <p>La recomendacion aparece automaticamente con 2+ cartas del jugador y 1 del dealer</p>
        </div>
        <div className="flex gap-2">
          <span className="text-emerald-400 mt-0.5">4.</span>
          <p>Usa <span className="text-white">"Siguiente Mano"</span> para mantener el conteo entre manos</p>
        </div>
        <div className="flex gap-2">
          <span className="text-emerald-400 mt-0.5">5.</span>
          <p>Click en una carta ya registrada para deshacerla</p>
        </div>

        <hr className="border-white/5" />

        <div>
          <p className="text-white/60 font-medium mb-1">Colores Hi-Lo:</p>
          <div className="space-y-1">
            <p><span className="text-blue-400">■</span> 2-6: +1 (favorables)</p>
            <p><span className="text-gray-400">■</span> 7-9: 0 (neutras)</p>
            <p><span className="text-red-400">■</span> 10-A: -1 (desfavorables)</p>
          </div>
        </div>

        <hr className="border-white/5" />

        <div>
          <p className="text-white/60 font-medium mb-1">Desviaciones:</p>
          <p>El sistema aplica automaticamente <span className="text-purple-300">Illustrious 18</span> y <span className="text-purple-300">Fab 4</span> cuando el True Count lo indica.</p>
        </div>
      </div>
    </div>
  )
}

export default App
