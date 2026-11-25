import { useState } from 'react';
import {
  ArrowUp,
  Blocks,
  ChevronDown,
  EyeOff,
  Layers,
  Mic,
  PanelLeftOpen,
  Paperclip,
  Plus,
  RotateCcw,
} from 'lucide-react';
import { useChatStore } from '../store/useChatStore';

export function ChatArea() {
  const [input, setInput] = useState('');
  const [modelMenuOpen, setModelMenuOpen] = useState(false);

  const {
    sidebarOpen,
    drawerOpen,
    incognito,
    streaming,
    providers,
    selectedProviderId,
    selectedModel,
    messages,
    memories,
    setSidebarOpen,
    setDrawerOpen,
    setSettingsOpen,
    setSelectedModel,
    toggleIncognito,
    sendMessage,
    undoMessageMemory,
  } = useChatStore();

  const activeProvider = providers.find((p) => p.id === selectedProviderId);
  const enabledMemCount = memories.filter((m) => m.is_enabled).length;

  const submitCurrent = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    if (!selectedProviderId || !selectedModel) {
      setSettingsOpen(true);
      return;
    }
    setInput('');
    await sendMessage(text);
  };

  const renderComposer = () => (
    <div
      className="w-full rounded-3xl border px-3.5 pt-3 pb-2.5 shadow-xs transition-colors"
      style={{
        background: 'var(--mc-surface)',
        borderColor: 'var(--mc-border)',
        borderStyle: incognito ? 'dashed' : 'solid',
      }}
    >
      <textarea
        rows={2}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitCurrent();
          }
        }}
        placeholder={incognito ? '当前处于无痕对话，不会读取或记录个人记忆...' : '发送消息...'}
        aria-label="消息输入框"
        className="w-full bg-transparent outline-none text-[14px] leading-relaxed resize-none"
      />

      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled
            aria-label="附件扩展槽"
            title="附件（二期扩展槽）"
            className="w-8 h-8 rounded-lg flex items-center justify-center opacity-45 cursor-not-allowed"
            style={{ color: 'var(--mc-fg-muted)' }}
          >
            <Paperclip size={16} strokeWidth={1.75} aria-hidden="true" />
          </button>
          <button
            type="button"
            disabled
            aria-label="Skill 技能扩展槽"
            title="Skills 技能挂载（二期扩展槽）"
            className="w-8 h-8 rounded-lg flex items-center justify-center opacity-45 cursor-not-allowed"
            style={{ color: 'var(--mc-fg-muted)' }}
          >
            <Blocks size={16} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            disabled
            aria-label="语音输入扩展槽"
            title="语音输入（二期扩展槽）"
            className="w-8 h-8 rounded-lg flex items-center justify-center opacity-45 cursor-not-allowed"
            style={{ color: 'var(--mc-fg-muted)' }}
          >
            <Mic size={16} strokeWidth={1.75} aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={submitCurrent}
            disabled={!input.trim() || streaming}
            aria-label="发送消息"
            className="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer transition-opacity disabled:opacity-35"
            style={{ background: 'var(--mc-primary)', color: 'var(--mc-primary-fg)' }}
          >
            <ArrowUp size={16} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <main className="flex-1 flex flex-col min-w-0 relative">
      {/* Mainstream Minimal Header */}
      <header className="h-[52px] px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5 relative">
          {!sidebarOpen && (
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="展开侧边栏"
              className="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
              style={{ color: 'var(--mc-fg-muted)' }}
            >
              <PanelLeftOpen size={18} strokeWidth={1.75} aria-hidden="true" />
            </button>
          )}

          <button
            type="button"
            aria-label="切换或配置模型"
            onClick={() => {
              if (providers.length === 0) setSettingsOpen(true);
              else setModelMenuOpen((o) => !o);
            }}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm font-medium cursor-pointer"
          >
            <span>{selectedModel || '未配置模型'}</span>
            <span className="text-xs font-normal" style={{ color: 'var(--mc-fg-muted)' }}>
              {activeProvider ? activeProvider.name : '点击接入'}
            </span>
            <ChevronDown size={14} strokeWidth={1.75} style={{ color: 'var(--mc-fg-muted)' }} aria-hidden="true" />
          </button>

          {modelMenuOpen && (
            <div
              className="absolute left-0 top-11 w-64 rounded-xl border p-1.5 shadow-xl z-30"
              style={{ background: 'var(--mc-elevated)', borderColor: 'var(--mc-border)' }}
            >
              <div className="space-y-0.5 max-h-56 overflow-y-auto text-[13px]">
                {providers.flatMap((p) =>
                  p.models.map((m) => (
                    <button
                      key={`${p.id}:${m}`}
                      type="button"
                      onClick={() => {
                        setSelectedModel(p.id, m);
                        setModelMenuOpen(false);
                      }}
                      className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left cursor-pointer"
                      style={{
                        background:
                          p.id === selectedProviderId && m === selectedModel ? 'var(--mc-surface)' : 'transparent',
                      }}
                    >
                      <span className="truncate font-medium">{m}</span>
                      <span className="text-[11px]" style={{ color: 'var(--mc-fg-muted)' }}>
                        {p.name}
                      </span>
                    </button>
                  )),
                )}
              </div>
              <div className="border-t mt-1.5 pt-1.5" style={{ borderColor: 'var(--mc-border)' }}>
                <button
                  type="button"
                  onClick={() => {
                    setModelMenuOpen(false);
                    setSettingsOpen(true);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
                  style={{ color: 'var(--mc-fg-muted)' }}
                >
                  <Plus size={14} strokeWidth={1.75} aria-hidden="true" />
                  配置模型服务商...
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Header Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-label="无痕对话开关"
            aria-pressed={incognito}
            onClick={toggleIncognito}
            title="无痕对话：开启后本会话不读取也不写入个人记忆"
            className="flex items-center gap-1.5 px-2.5 h-8 rounded-lg border text-xs font-medium cursor-pointer transition-colors"
            style={{
              background: incognito ? 'var(--mc-surface)' : 'transparent',
              borderColor: incognito ? 'var(--mc-border)' : 'transparent',
              color: incognito ? 'var(--mc-fg)' : 'var(--mc-fg-muted)',
            }}
          >
            <EyeOff size={15} strokeWidth={1.75} aria-hidden="true" />
            <span className="hidden sm:inline">无痕</span>
          </button>

          <button
            type="button"
            aria-label="记忆面板开关"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen(!drawerOpen)}
            className="flex items-center gap-1.5 px-2.5 h-8 rounded-lg border text-xs font-medium cursor-pointer"
            style={{
              background: drawerOpen ? 'var(--mc-surface)' : 'transparent',
              borderColor: 'var(--mc-border)',
            }}
          >
            <Layers size={15} strokeWidth={1.75} aria-hidden="true" />
            <span>{enabledMemCount}</span>
          </button>
        </div>
      </header>

      {/* Center Empty State vs Active Message Stream */}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center px-4 pb-12">
          <div className="w-full max-w-[720px] text-center">
            <h1 className="text-2xl font-semibold tracking-tight mb-7">有什么可以帮你？</h1>
            {renderComposer()}
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto px-4">
            <div className="max-w-[740px] mx-auto py-6 space-y-7">
              {messages.map((msg) =>
                msg.role === 'user' ? (
                  <div key={msg.id} className="flex flex-col items-end gap-1.5">
                    <div
                      className="max-w-[76%] rounded-3xl px-4 py-2.5 text-[14px] leading-relaxed whitespace-pre-wrap"
                      style={{ background: 'var(--mc-surface)' }}
                    >
                      {msg.content}
                    </div>
                    {msg.memory_events?.map((ev) =>
                      ev.undone ? null : (
                        <div
                          key={ev.memory.id}
                          className="flex items-center gap-2 text-xs px-2"
                          style={{ color: 'var(--mc-fg-muted)' }}
                        >
                          <span>
                            {ev.action === 'UPDATE' ? '已更新记忆：' : '已记录记忆：'}
                            {ev.memory.content}
                          </span>
                          <button
                            type="button"
                            onClick={() => undoMessageMemory(ev.memory.id, msg.id)}
                            aria-label="撤销此条记忆"
                            className="inline-flex items-center gap-1 underline cursor-pointer hover:opacity-80"
                          >
                            <RotateCcw size={11} strokeWidth={1.75} aria-hidden="true" />
                            撤销
                          </button>
                        </div>
                      ),
                    )}
                  </div>
                ) : (
                  <div key={msg.id} className="flex items-start gap-3.5">
                    <div
                      className="w-7 h-7 rounded-full border flex items-center justify-center shrink-0 mt-0.5"
                      style={{ background: 'var(--mc-surface)', borderColor: 'var(--mc-border)' }}
                    >
                      <Layers size={13} strokeWidth={1.75} aria-hidden="true" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-2">
                      {msg.memory_refs?.length > 0 && (
                        <details className="text-xs">
                          <summary
                            className="inline-flex items-center gap-1.5 cursor-pointer select-none py-0.5 px-2 rounded-md border"
                            style={{ borderColor: 'var(--mc-border)', color: 'var(--mc-fg-muted)' }}
                          >
                            已结合 {msg.memory_refs.length} 条个人记忆
                          </summary>
                          <div
                            className="mt-1.5 pl-2.5 border-l-2 space-y-1 py-0.5"
                            style={{ borderColor: 'var(--mc-border)', color: 'var(--mc-fg-muted)' }}
                          >
                            {msg.memory_refs.map((r) => (
                              <div key={r.id}>{r.content}</div>
                            ))}
                          </div>
                        </details>
                      )}

                      <div className="text-[15px] leading-7 whitespace-pre-wrap">
                        {msg.content || (msg.streaming ? '...' : '')}
                      </div>

                      {msg.model_used && (
                        <div className="text-xs" style={{ color: 'var(--mc-fg-muted)' }}>
                          {msg.model_used}
                        </div>
                      )}
                    </div>
                  </div>
                ),
              )}
            </div>
          </div>

          <div className="px-4 pb-4 pt-2">
            <div className="max-w-[740px] mx-auto">{renderComposer()}</div>
          </div>
        </>
      )}
    </main>
  );
}
