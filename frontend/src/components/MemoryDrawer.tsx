import { useState } from 'react';
import { Pin, X } from 'lucide-react';
import { useChatStore } from '../store/useChatStore';

export function MemoryDrawer() {
  const [tab, setTab] = useState<'profile' | 'episodic' | 'summary'>('profile');
  const [draft, setDraft] = useState('');

  const {
    drawerOpen,
    memories,
    summaries,
    topK,
    threshold,
    setDrawerOpen,
    setTopK,
    setThreshold,
    addMemory,
    toggleMemoryEnable,
    toggleMemoryPin,
    archiveMemory,
  } = useChatStore();

  if (!drawerOpen) return null;

  const filtered = memories.filter((m) => (tab === 'profile' ? m.layer === 'profile' : m.layer === 'episodic'));

  const submitAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    await addMemory(tab === 'episodic' ? 'episodic' : 'profile', draft.trim());
    setDraft('');
  };

  return (
    <aside
      aria-label="记忆与上下文面板"
      className="w-[336px] shrink-0 border-l flex flex-col"
      style={{ background: 'var(--mc-sidebar)', borderColor: 'var(--mc-border)' }}
    >
      <div
        className="h-[52px] px-4 flex items-center justify-between border-b"
        style={{ borderColor: 'var(--mc-border)' }}
      >
        <span className="text-sm font-semibold">记忆与上下文</span>
        <button
          type="button"
          onClick={() => setDrawerOpen(false)}
          aria-label="关闭记忆面板"
          className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer"
          style={{ color: 'var(--mc-fg-muted)' }}
        >
          <X size={16} strokeWidth={1.75} aria-hidden="true" />
        </button>
      </div>

      {/* Segmented Control */}
      <div className="px-3 pt-3">
        <div
          className="grid grid-cols-3 p-0.5 rounded-lg border text-xs"
          style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
        >
          {(['profile', 'episodic', 'summary'] as const).map((key) => {
            const label = key === 'profile' ? '核心画像' : key === 'episodic' ? '情景记忆' : '会话摘要';
            const active = tab === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className="py-1.5 rounded-md font-medium cursor-pointer transition-colors"
                style={{
                  background: active ? 'var(--mc-surface)' : 'transparent',
                  color: active ? 'var(--mc-fg)' : 'var(--mc-fg-muted)',
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {tab !== 'summary' && (
        <form onSubmit={submitAdd} className="px-3 pt-2.5 flex items-center gap-1.5">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="添加一条记忆条目..."
            aria-label="手动添加记忆"
            className="flex-1 h-8 px-2.5 rounded-lg border text-xs outline-none"
            style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
          />
          <button
            type="submit"
            className="h-8 px-2.5 rounded-lg text-xs font-medium shrink-0 cursor-pointer"
            style={{ background: 'var(--mc-primary)', color: 'var(--mc-primary-fg)' }}
          >
            添加
          </button>
        </form>
      )}

      {/* List Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
        {tab === 'summary' ? (
          summaries.length === 0 ? (
            <div className="py-14 text-center" style={{ color: 'var(--mc-fg-muted)' }}>
              长对话满阈值后自动生成阶段摘要
            </div>
          ) : (
            summaries.map((s) => (
              <div
                key={s.id}
                className="p-3 rounded-xl border leading-relaxed"
                style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
              >
                {s.summary_text}
              </div>
            ))
          )
        ) : filtered.length === 0 ? (
          <div className="py-14 text-center" style={{ color: 'var(--mc-fg-muted)' }}>
            暂无记录
          </div>
        ) : (
          filtered.map((m) => (
            <div
              key={m.id}
              className="p-2.5 rounded-xl border flex items-start justify-between gap-2.5 transition-opacity"
              style={{
                background: 'var(--mc-bg)',
                borderColor: 'var(--mc-border)',
                opacity: m.is_enabled ? 1 : 0.5,
              }}
            >
              <span className="leading-relaxed break-words flex-1">{m.content}</span>
              <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                <button
                  type="button"
                  onClick={() => toggleMemoryPin(m)}
                  aria-label="置顶记忆"
                  className="w-6 h-6 rounded flex items-center justify-center cursor-pointer"
                  style={{ color: m.is_pinned ? 'var(--mc-fg)' : 'var(--mc-fg-muted)' }}
                >
                  <Pin size={13} strokeWidth={1.75} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  role="switch"
                  aria-checked={m.is_enabled}
                  aria-label={`切换记忆启用 ${m.content}`}
                  onClick={() => toggleMemoryEnable(m)}
                  className="mc-switch"
                />
                <button
                  type="button"
                  onClick={() => archiveMemory(m.id)}
                  aria-label={`删除记忆 ${m.content}`}
                  className="w-6 h-6 rounded flex items-center justify-center cursor-pointer"
                  style={{ color: 'var(--mc-fg-muted)' }}
                >
                  <X size={13} strokeWidth={1.75} aria-hidden="true" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Retrieval Tuning Sliders */}
      <div
        className="p-3 border-t space-y-2 text-xs"
        style={{ borderColor: 'var(--mc-border)', color: 'var(--mc-fg-muted)' }}
      >
        <div className="flex items-center justify-between">
          <span>单轮最大召回</span>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={1}
              max={10}
              value={topK}
              aria-label="单轮最大召回条数"
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-24"
            />
            <span className="w-4 text-right font-mono" style={{ color: 'var(--mc-fg)' }}>
              {topK}
            </span>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span>语义相关度阈值</span>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0.05}
              max={0.8}
              step={0.05}
              value={threshold}
              aria-label="语义相关度阈值"
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-24"
            />
            <span className="w-8 text-right font-mono" style={{ color: 'var(--mc-fg)' }}>
              {threshold.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
