// frontend/src/components/AIAdvisor.jsx
import { useGameStore } from '../store/gameStore'
import { useEffect } from 'react'

const ACTION_LABELS = {
  H: 'PEDIR (Hit)',
  S: 'PLANTARSE (Stand)',
  D: 'DOBLAR (Double Down)',
  P: 'DIVIDIR (Split)',
  R: 'RENDIRSE (Surrender)',
}

const ACTION_COLORS = {
  H: '#7ddf82', S: '#7ab3ff', D: '#ffd070', P: '#c080ff', R: '#ff8080'
}

export function AIAdvisor() {
  const {
    aiRecommendation, aiStatus, aiEnabled,
    toggleAI, triggerTraining, fetchAIStatus
  } = useGameStore()

  useEffect(() => {
    fetchAIStatus()
  }, [])

  const trained = aiStatus?.trained ?? false
  const hands   = aiStatus?.total_hands ?? 0
  const winRate = aiStatus?.win_rate ?? 0
  const states  = aiStatus?.state_count ?? 0

  return (
    <div style={{
      background: 'rgba(26,58,143,0.12)',
      border: '1px solid rgba(122,179,255,0.25)',
      borderRadius: '10px',
      padding: '12px 16px',
      marginBottom: '10px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', color: '#7ab3ff', fontWeight: 600,
                       letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          🧠 Motor Q-Learning
        </span>

        {/* Badge estado */}
        <span style={{
          fontSize: '9px', padding: '2px 8px', borderRadius: '10px', fontWeight: 700,
          background: trained ? 'rgba(26,107,26,0.4)' : 'rgba(26,58,143,0.4)',
          color: trained ? '#7ddf82' : '#7ab3ff',
          border: `1px solid ${trained ? '#3abf3a' : '#3a6abf'}`,
        }}>
          {trained ? `ENTRENADO · ${hands.toLocaleString()} manos` : 'ENTRENANDO...'}
        </span>

        {/* Toggle */}
        <button onClick={toggleAI} style={{
          marginLeft: 'auto', fontSize: '10px', padding: '3px 10px',
          borderRadius: '6px', cursor: 'pointer', border: '1px solid rgba(122,179,255,0.3)',
          background: aiEnabled ? 'rgba(122,179,255,0.15)' : 'transparent',
          color: aiEnabled ? '#7ab3ff' : 'rgba(122,179,255,0.4)',
        }}>
          {aiEnabled ? 'IA ON' : 'IA OFF'}
        </button>
      </div>

      {/* Stats fila */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
        {[
          ['Win rate', `${winRate}%`],
          ['Estados Q', states.toLocaleString()],
          ['Épsilon', aiStatus?.epsilon?.toFixed(3) ?? '—'],
        ].map(([label, val]) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '14px', fontWeight: 600,
                          color: 'rgba(240,232,208,0.9)' }}>{val}</div>
            <div style={{ fontSize: '9px', color: 'rgba(122,179,255,0.5)',
                          textTransform: 'uppercase', letterSpacing: '0.1em' }}>{label}</div>
          </div>
        ))}

        {/* Botón entrenar */}
        {!trained && (
          <button onClick={() => triggerTraining(50000)} style={{
            marginLeft: 'auto', fontSize: '10px', padding: '4px 12px',
            borderRadius: '6px', cursor: 'pointer',
            border: '1px solid rgba(160,100,255,0.4)',
            background: 'rgba(160,100,255,0.1)', color: '#c080ff',
          }}>
            ⚡ Entrenar ahora
          </button>
        )}
      </div>

      {/* Recomendación de la IA */}
      {aiEnabled && aiRecommendation && (
        <div style={{
          borderTop: '1px solid rgba(122,179,255,0.15)',
          paddingTop: '8px', marginTop: '4px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '11px', color: 'rgba(122,179,255,0.6)' }}>
              Sugerencia IA:
            </span>
            <span style={{
              fontSize: '14px', fontWeight: 700,
              color: ACTION_COLORS[aiRecommendation.final_action] || '#fff',
            }}>
              {ACTION_LABELS[aiRecommendation.final_action]}
            </span>
            {aiRecommendation.q_override && (
              <span style={{
                fontSize: '9px', padding: '1px 6px', borderRadius: '8px',
                background: 'rgba(160,100,255,0.2)', color: '#c080ff',
                border: '1px solid rgba(160,100,255,0.3)',
              }}>
                IA overrride
              </span>
            )}
          </div>

          {/* Confianza */}
          <div style={{ marginBottom: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between',
                          fontSize: '9px', color: 'rgba(122,179,255,0.4)',
                          marginBottom: '2px' }}>
              <span>Confianza</span>
              <span>{aiRecommendation.confidence}%</span>
            </div>
            <div style={{ height: '3px', background: 'rgba(0,0,0,0.3)',
                          borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: '2px',
                width: `${aiRecommendation.confidence}%`,
                background: `linear-gradient(90deg, #3a6abf, #c080ff)`,
                transition: 'width 0.4s',
              }}/>
            </div>
          </div>

          {/* Valores Q */}
          {Object.keys(aiRecommendation.q_values).length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
              {Object.entries(aiRecommendation.q_values)
                .sort(([,a],[,b]) => b - a)
                .map(([action, val]) => (
                <div key={action} style={{
                  fontSize: '10px', padding: '2px 7px', borderRadius: '6px',
                  background: 'rgba(0,0,0,0.2)',
                  color: action === aiRecommendation.final_action
                    ? (ACTION_COLORS[action] || '#fff')
                    : 'rgba(255,255,255,0.35)',
                  border: action === aiRecommendation.final_action
                    ? `1px solid ${ACTION_COLORS[action]}44`
                    : '1px solid transparent',
                }}>
                  {ACTION_LABELS[action]?.split(' ')[0]}: {val.toFixed(2)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
