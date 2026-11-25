import { useState } from 'react';
import {
  Coffee,
  Code2,
  Eye,
  EyeOff,
  FileText,
  GraduationCap,
  Pin,
  Plus,
  Puzzle,
  SlidersHorizontal,
  Target,
  Trash2,
  UserRound,
  X,
} from 'lucide-react';
import type { MemoryItem, MemoryLayer, SessionSummary } from '../types';

interface Props {
  memories: MemoryItem[];
  summaries: SessionSummary[];
  topK: number;
  threshold: number;
  onChangeTopK: (val: number) => void;
  onChangeThreshold: (val: number) => void;
  onAddMemory: (layer: MemoryLayer, category: string, content: string) => Promise<void>;
  onToggleEnable: (mem: MemoryItem) => Promise<void>;
  onTogglePin: (mem: MemoryItem) => Promise<void>;
  onArchive: (memId: string) => Promise<void>;
  onClose: () => void;
}

const CATEGORY_CHIPS = [
  { id: 'identity', label: '身份', icon: GraduationCap, layer: 'profile' as MemoryLayer },
  { id: 'preference', label: '偏好', icon: Code2, layer: 'profile' as MemoryLayer },
  { id: 'habit', label: '习惯', icon: Coffee, layer: 'episodic' as MemoryLayer },
  { id: 'project', label: '近期', icon: Target, layer: 'episodic' as MemoryLayer },
];

export function MemoryDrawer({
  memories,
  summaries,
  topK,
  threshold,
  onChangeTopK,
  onChangeThreshold,
  onAddMemory,
  onToggleEnable,
  onTogglePin,
  onArchive,
  onClose,
}: Props) {
  const [tab, setTab] = useState<'profile' | 'episodic' | 'summary'>('profile');
  const [selectedCat, setSelectedCat] = useState(CATEGORY_CHIPS[1]);
  const [draft, setDraft] = useState('');

  const filtered = memories.filter((m) => (tab === 'profile' ? m.layer === 'profile' : m.layer === 'episodic'));

  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    await onAddMemory(tab === 'episodic' ? 'episodic' : selectedCat.layer, selectedCat.id, draft.trim());
    setDraft('');
  };

  return (
    <aside className="drawer" aria-label="个人记忆抽屉">
      {/* Header + Segmented Icon Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            type="button"
            className={`icon-btn ${tab === 'profile' ? 'memory-active' : ''}`}
            onClick={() => setTab('profile')}
            aria-label="画像层"
          >
            <UserRound size={14} aria-hidden="true" />
            画像
          </button>
          <button
            type="button"
            className={`icon-btn ${tab === 'episodic' ? 'memory-active' : ''}`}
            onClick={() => setTab('episodic')}
            aria-label="情景记忆层"
          >
            <Puzzle size={14} aria-hidden="true" />
            记忆
          </button>
          <button
            type="button"
            className={`icon-btn ${tab === 'summary' ? 'memory-active' : ''}`}
            onClick={() => setTab('summary')}
            aria-label="会话摘要层"
          >
            <FileText size={14} aria-hidden="true" />
            摘要
          </button>
        </div>

        <button
          type="button"
          className="icon-btn"
          style={{ padding: 6 }}
          onClick={onClose}
          aria-label="收起记忆抽屉"
        >
          <X size={15} aria-hidden="true" />
        </button>
      </div>

      {/* Category Icon Chips + 1-Line Quick Add */}
      {tab !== 'summary' && (
        <form onSubmit={handleQuickAdd} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            {CATEGORY_CHIPS.map((c) => {
              const Icon = c.icon;
              const active = selectedCat.id === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedCat(c)}
                  className={`icon-btn ${active ? 'memory-active' : ''}`}
                  style={{ padding: '4px 9px', fontSize: 12 }}
                  aria-label={`分类 ${c.label}`}
                >
                  <Icon size={13} aria-hidden="true" />
                  {c.label}
                </button>
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="+ 添加记忆..."
              aria-label="快速添加记忆"
              style={{
                flex: 1,
                borderRadius: 12,
                border: '1px solid var(--border)',
                background: 'var(--surface-muted)',
                color: 'var(--fg)',
                padding: '7px 10px',
                fontSize: 13,
                outline: 'none',
              }}
            />
            <button type="submit" className="icon-btn primary" style={{ padding: '7px 10px' }} aria-label="确认添加">
              <Plus size={15} aria-hidden="true" />
            </button>
          </div>
        </form>
      )}

      {/* Memory / Summary Card List */}
      <div className="scroller" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {tab === 'summary' ? (
          summaries.length === 0 ? (
            <div style={{ margin: 'auto', color: 'var(--fg-muted)', fontSize: 12 }}>∅</div>
          ) : (
            summaries.map((s) => (
              <div
                key={s.id}
                style={{
                  padding: 10,
                  borderRadius: 12,
                  border: '1px solid var(--border)',
                  background: 'var(--surface-muted)',
                  fontSize: 12,
                  lineHeight: 1.5,
                }}
              >
                <div>{s.summary_text}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                  {s.key_topics.map((t) => (
                    <span key={t} className="micro-badge recall" style={{ fontSize: 11, padding: '1px 7px' }}>
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )
        ) : filtered.length === 0 ? (
          <div style={{ margin: 'auto', color: 'var(--fg-muted)', fontSize: 12 }}>∅</div>
        ) : (
          filtered.map((m) => (
            <div
              key={m.id}
              style={{
                padding: '9px 10px',
                borderRadius: 12,
                border: '1px solid var(--border)',
                background: m.is_enabled ? 'var(--surface-muted)' : 'transparent',
                opacity: m.is_enabled ? 1 : 0.5,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8,
              }}
            >
              <span style={{ fontSize: 13, lineHeight: 1.4, wordBreak: 'break-word' }}>{m.content}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                <button
                  type="button"
                  onClick={() => onTogglePin(m)}
                  aria-label="置顶常驻"
                  title="置顶"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: m.is_pinned ? 'var(--brand)' : 'var(--fg-muted)',
                    cursor: 'pointer',
                    padding: 4,
                  }}
                >
                  <Pin size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => onToggleEnable(m)}
                  aria-label={m.is_enabled ? '暂停注入' : '恢复注入'}
                  title={m.is_enabled ? '已启用' : '已暂停'}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: m.is_enabled ? '#10b981' : 'var(--fg-muted)',
                    cursor: 'pointer',
                    padding: 4,
                  }}
                >
                  {m.is_enabled ? <Eye size={14} aria-hidden="true" /> : <EyeOff size={14} aria-hidden="true" />}
                </button>
                <button
                  type="button"
                  onClick={() => onArchive(m.id)}
                  aria-label="归档删除"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--fg-muted)',
                    cursor: 'pointer',
                    padding: 4,
                  }}
                >
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Compact Retrieval Control Sliders */}
      <div
        style={{
          borderTop: '1px solid var(--border)',
          paddingTop: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          fontSize: 12,
          color: 'var(--fg-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <SlidersHorizontal size={13} aria-hidden="true" /> Top-{topK}
          </span>
          <input
            type="range"
            min={1}
            max={10}
            value={topK}
            aria-label="单轮最大召回记忆条数"
            onChange={(e) => onChangeTopK(Number(e.target.value))}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>🎯 {threshold.toFixed(2)}</span>
          <input
            type="range"
            min={0.05}
            max={0.8}
            step={0.05}
            value={threshold}
            aria-label="语义相似度阈值"
            onChange={(e) => onChangeThreshold(Number(e.target.value))}
          />
        </div>
      </div>
    </aside>
  );
}
