import { create } from 'zustand'
import API from '../api/client'

export const useGameStore = create((set, get) => ({
  sessionId: null,
  aiStatus: null,
  aiRecommendation: null,
  aiEnabled: true,
  lastHandResult: null,
  playerCards: [],
  dealerCard: null,
  splitHands: [[], []],
  inSplit: false,
  activeSplitHand: 0,
  target: 'player',
  shoe: {},
  runningCount: 0,
  trueCount: 0,
  handsPlayed: 0,
  recommendation: null,
  betAdvice: null,
  insurance: null,
  isLoading: false,
  bankroll: 1000,
  minBet: 10,
  error: null,

  initSession: async () => {
    try {
      const { data } = await API.post('/session/new')
      set({
        sessionId: data.session_id,
        shoe: data.shoe.cards,
        runningCount: 0,
        trueCount: 0,
        error: null,
      })
    } catch (e) {
      set({ error: 'No se pudo conectar con el servidor' })
    }
  },

  setTarget: (target) => set({ target }),

  addCard: async (rank) => {
    const { sessionId, target, playerCards, splitHands, shoe } = get()
    if (!sessionId) return
    if ((shoe[rank] || 0) <= 0) return

    if (target === 'dealer') {
      set({ dealerCard: rank })
    } else if (target === 'player') {
      set({ playerCards: [...playerCards, rank] })
    } else if (target === 'split_0') {
      const h = [...splitHands]; h[0] = [...h[0], rank]
      set({ splitHands: h })
    } else if (target === 'split_1') {
      const h = [...splitHands]; h[1] = [...h[1], rank]
      set({ splitHands: h })
    }

    try {
      const { data } = await API.post('/card/add', { rank, target, session_id: sessionId })
      const newShoe = data.shoe
      set({
        shoe: newShoe.cards,
        runningCount: newShoe.running_count,
        trueCount: newShoe.true_count,
      })
      await get().fetchStrategy()
    } catch (e) {
      set({ error: 'Error al registrar carta' })
    }
  },

  removeCard: async (rank, target) => {
    const { sessionId } = get()
    try {
      await API.post('/card/undo', { rank, target, session_id: sessionId })
      const s = get()
      if (target === 'dealer') {
        set({ dealerCard: null })
      } else if (target === 'player') {
        const idx = s.playerCards.lastIndexOf(rank)
        if (idx !== -1) {
          const cards = [...s.playerCards]
          cards.splice(idx, 1)
          set({ playerCards: cards })
        }
      }
      await get().fetchStrategy()
    } catch (e) {
      set({ error: 'Error al deshacer carta' })
    }
  },

  fetchStrategy: async () => {
    const { sessionId, playerCards, dealerCard, bankroll, minBet } = get()
    if (playerCards.length < 2 || !dealerCard) {
      set({ recommendation: null, betAdvice: null, insurance: null })
      return
    }
    set({ isLoading: true })
    try {
      const { data } = await API.post('/strategy', {
        player_cards: playerCards,
        dealer_card: dealerCard,
        session_id: sessionId,
        bankroll,
        min_bet: minBet,
      })
      set({
        recommendation: data,
        betAdvice: data.bet_advice,
        insurance: data.insurance,
        trueCount: data.true_count,
        runningCount: data.running_count,
        shoe: data.shoe.cards,
      })
    } catch (e) {
      set({ error: 'Error al calcular estrategia' })
    } finally {
      set({ isLoading: false })
    }
  },

  enterSplit: () => {
    const { playerCards } = get()
    if (playerCards.length !== 2) return
    const base = playerCards[0]
    set({
      inSplit: true,
      splitHands: [[base], [base]],
      playerCards: [],
      activeSplitHand: 0,
      target: 'split_0',
    })
  },

  nextHand: async () => {
    const { sessionId } = get()
    try {
      const { data } = await API.post(`/hand/next?session_id=${sessionId}`)
      set({
        playerCards: [],
        dealerCard: null,
        splitHands: [[], []],
        inSplit: false,
        activeSplitHand: 0,
        target: 'player',
        recommendation: null,
        betAdvice: null,
        insurance: null,
        handsPlayed: data.hands_played,
        shoe: data.shoe.cards,
        runningCount: data.shoe.running_count,
        trueCount: data.shoe.true_count,
      })
    } catch (e) {
      set({ error: 'Error al avanzar mano' })
    }
  },

  finishGame: async () => {
    const { sessionId } = get()
    try {
      await API.post(`/game/finish?session_id=${sessionId}`)
      await get().initSession()
      set({
        playerCards: [],
        dealerCard: null,
        splitHands: [[], []],
        inSplit: false,
        handsPlayed: 0,
        recommendation: null,
        betAdvice: null,
        insurance: null,
      })
    } catch (e) {
      set({ error: 'Error al finalizar juego' })
    }
  },

  setBankroll: (amount) => set({ bankroll: amount }),
  setMinBet: (amount) => set({ minBet: amount }),
  clearError: () => set({ error: null }),

  fetchAIStatus: async () => {
    try {
      const { data } = await API.get('/ai/status')
      set({ aiStatus: data })
    } catch (e) { /* silencioso */ }
  },

  fetchAIRecommendation: async () => {
    const { sessionId, playerCards, dealerCard, bankroll, minBet, aiEnabled } = get()
    if (!aiEnabled || playerCards.length < 2 || !dealerCard) return

    try {
      const { data } = await API.post('/ai/recommend', {
        player_cards: playerCards,
        dealer_card:  dealerCard,
        session_id:   sessionId,
        bankroll,
        min_bet: minBet,
      })
      set({ aiRecommendation: data })
    } catch (e) { /* silencioso, fallback a estrategia básica */ }
  },

  reportHandResult: async (actionTaken, reward) => {
    const { sessionId, playerCards, dealerCard, trueCount } = get()
    if (!playerCards.length || !dealerCard) return

    try {
      await API.post('/ai/learn', {
        session_id:   sessionId,
        player_cards: playerCards,
        dealer_card:  dealerCard,
        true_count:   trueCount,
        action_taken: actionTaken,
        reward,
      })
    } catch (e) { /* silencioso */ }
  },

  triggerTraining: async (nHands = 50000) => {
    await API.post(`/ai/train?n_hands=${nHands}`)
    const poll = setInterval(async () => {
      await get().fetchAIStatus()
      const s = get().aiStatus
      if (s && s.total_hands > 0) {
        set({ aiStatus: s })
      }
    }, 3000)
    setTimeout(() => clearInterval(poll), 120_000)
  },

  toggleAI: () => set(s => ({ aiEnabled: !s.aiEnabled })),
}))
