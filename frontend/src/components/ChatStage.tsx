import { useState } from 'react';
import {
  Brain,
  Mic,
  PlugZap,
  Puzzle,
  RotateCcw,
  SendHorizontal,
  Sparkles,
  UserPlus,
  Wrench,
} from 'lucide-react';
import type { ChatMessage, ExtensionSlot } from '../types';

interface Props {
  messages: ChatMessage[];
  incognito: boolean;
  streaming: boolean;
  extensionSlots: ExtensionSlot[];
  onSend: (text: string) => Promise<void>;
  onOpenProfile: () => void;
  onOpenProviders: () => void;
  onUndoMemory: (memId: string, msgId: string) => Promise<void>;
}

export function ChatStage({
  messages,
  incognito,
  streaming,
  extensionSlots,
  onSend,
  onOpenProfile,
  onOpenProviders,
  onUndoMemory,
}: Props) {
  const [input, setInput] = useState('');
  const [expandedMsgId, setExpandedMsgId] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    await onSend(text);
  };

  const slotIcon = (slot: ExtensionSlot['slot']) => {
    if (slot === 'asr') return <Mic size={15} aria-hidden="true" />;
    if (slot === 'skill') return <Puzzle size={15} aria-hidden="true" />;
    return <Wrench size={15} aria-hidden="true" />;
  };

  return (
    <>
      <div
        className="scroller"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 20px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', maxWidth: 560 }}>
            {/* Crisp Brand Emblem without verbose onboarding text */}
            <div
              style={{
                width: 58,
                height: 58,
                margin: '0 auto 14px',
                borderRadius: 18,
                background: incognito ? 'var(--incog-soft)' : 'var(--brand-soft)',
                color: incognito ? 'var(--incog)' : 'var(--brand)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Brain size={28} aria-hidden="true" />
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.02em' }}>MemoryChat</div>

            {/* 3 Graphical Starter Cards */}
            <div className="starter-grid" data-testid="starter-cards">
              <button
                type="button"
                className="starter-card"
                aria-label="录入画像"
                onClick={onOpenProfile}
              >
                <div className="starter-icon-ring">
                  <UserPlus size={22} aria-hidden="true" />
                </div>
                <span style={{ fontSize: 13, fontWeight: 600 }}>录入画像</span>
                <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>🎓 · 💻 · ☕</span>
              </button>

              <button
                type="button"
                className="starter-card"
                aria-label="接入模型"
                onClick={onOpenProviders}
              >
                <div className="starter-icon-ring">
                  <PlugZap size={22} aria-hidden="true" />
                </div>
                <span style={{ fontSize: 13, fontWeight: 600 }}>接入模型</span>
                <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>🐋 · ✦ · ◎ · 🦙</span>
              </button>

              <button
                type="button"
                className="starter-card"
                aria-label="试试记忆"
                onClick={() => onSend('我是大四计算机专业学生，平时写Python后端最喜欢用FastAPI')}
              >
                <div className="starter-icon-ring">
                  <Sparkles size={22} aria-hidden="true" />
                </div>
                <span style={{ fontSize: 13, fontWeight: 600 }}>试试记忆</span>
                <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>⚡ 1-Click</span>
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              width: 'min(740px, 100%)',
              margin: '0 auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
            }}
          >
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    gap: 6,
                  }}
                >
                  {/* Assistant Recall Micro-Badge */}
                  {!isUser && msg.memory_refs?.length > 0 && (
                    <div>
                      <button
                        type="button"
                        className="micro-badge recall"
                        aria-label={`展开参考的 ${msg.memory_refs.length} 条记忆`}
                        onClick={() => setExpandedMsgId(expandedMsgId === msg.id ? null : msg.id)}
                      >
                        <Brain size={12} aria-hidden="true" />×{msg.memory_refs.length}
                      </button>
                      {expandedMsgId === msg.id && (
                        <div
                          style={{
                            marginTop: 6,
                            padding: '8px 10px',
                            borderRadius: 12,
                            background: 'var(--surface)',
                            border: '1px solid var(--border)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 4,
                            fontSize: 12,
                          }}
                        >
                          {msg.memory_refs.map((r) => (
                            <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ color: 'var(--brand)', fontWeight: 600 }}>
                                {Math.round((r.score ?? 1) * 100)}%
                              </span>
                              <span>{r.content}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Chat Bubble */}
                  <div
                    style={{
                      maxWidth: '84%',
                      padding: '11px 15px',
                      borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                      background: isUser ? 'var(--brand)' : 'var(--surface)',
                      color: isUser ? '#ffffff' : 'var(--fg)',
                      border: isUser ? 'none' : '1px solid var(--border)',
                      fontSize: 14,
                      lineHeight: 1.6,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {msg.content || (msg.streaming ? '•••' : '')}
                  </div>

                  {/* User Captured-Memory Micro-Badge with 1-Click Undo */}
                  {isUser &&
                    msg.memory_events?.map((ev) =>
                      ev.undone ? null : (
                        <div key={ev.memory.id} className="micro-badge captured">
                          <Sparkles size={12} aria-hidden="true" />
                          <span>
                            {ev.action === 'UPDATE' ? '↻' : '+'} {ev.memory.content.slice(0, 22)}
                          </span>
                          <button
                            type="button"
                            onClick={() => onUndoMemory(ev.memory.id, msg.id)}
                            aria-label="撤销此记忆"
                            title="撤销"
                            style={{
                              border: 'none',
                              background: 'transparent',
                              color: 'inherit',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              padding: 2,
                            }}
                          >
                            <RotateCcw size={12} aria-hidden="true" />
                          </button>
                        </div>
                      ),
                    )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Minimalist Icon-Guided Composer with Reserved Phase 2 Extension Slots */}
      <form
        onSubmit={handleSubmit}
        className={`composer-shell ${incognito ? 'incognito' : ''}`}
      >
        <div style={{ display: 'flex', gap: 4 }}>
          {extensionSlots.map((slot) => (
            <button
              key={slot.slot}
              type="button"
              disabled={slot.status === 'reserved'}
              className="icon-btn"
              style={{ padding: 7, border: 'none' }}
              aria-label={`${slot.label} 扩展插槽`}
              title={`${slot.label} (Phase 2 Slot)`}
            >
              {slotIcon(slot.slot)}
            </button>
          ))}
        </div>

        <input
          className="composer-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={incognito ? '👻 ...' : 'Message...'}
          aria-label="发送消息输入框"
        />

        <button
          type="submit"
          disabled={!input.trim() || streaming}
          className="icon-btn primary"
          style={{ padding: '8px 12px' }}
          aria-label="发送消息"
        >
          <SendHorizontal size={16} aria-hidden="true" />
        </button>
      </form>
    </>
  );
}
