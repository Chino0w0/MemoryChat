import { useEffect, useRef, useState } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import { api } from '../api';
import { useChatStore } from '../store/useChatStore';

export function ModelSettings() {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const { settingsOpen, providers, setSettingsOpen, saveProvider, deleteProvider } = useChatStore();

  const [providerId, setProviderId] = useState('custom-1');
  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelsText, setModelsText] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    if (providers.length > 0) {
      const p = providers[0];
      setProviderId(p.id);
      setName(p.name);
      setBaseUrl(p.base_url);
      setModelsText(p.models.join(', '));
    }
  }, [providers, settingsOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (settingsOpen && !dialog.hasAttribute('open')) {
      dialog.showModal();
    } else if (!settingsOpen && dialog.hasAttribute('open')) {
      dialog.close();
    }
  }, [settingsOpen]);

  // Coordinate-checked light-dismiss fallback when <dialog closedby="any"> is unsupported
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleClose = () => {
      dialog.returnValue = '';
      setSettingsOpen(false);
    };
    dialog.addEventListener('close', handleClose);

    let cleanupFallback: (() => void) | undefined;
    if (typeof HTMLDialogElement !== 'undefined' && !('closedBy' in HTMLDialogElement.prototype)) {
      let pressedOutside = false;
      const isOutside = (e: PointerEvent) => {
        const r = dialog.getBoundingClientRect();
        return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      };
      const onDown = (e: PointerEvent) => {
        pressedOutside = e.target === dialog && isOutside(e);
      };
      const onUp = (e: PointerEvent) => {
        if (pressedOutside && e.target === dialog && isOutside(e)) {
          dialog.close();
        }
        pressedOutside = false;
      };
      dialog.addEventListener('pointerdown', onDown);
      dialog.addEventListener('pointerup', onUp);
      cleanupFallback = () => {
        dialog.removeEventListener('pointerdown', onDown);
        dialog.removeEventListener('pointerup', onUp);
      };
    }

    return () => {
      dialog.removeEventListener('close', handleClose);
      cleanupFallback?.();
    };
  }, [setSettingsOpen]);

  const startNewBlank = () => {
    setProviderId(`provider-${Date.now().toString().slice(-4)}`);
    setName('');
    setBaseUrl('');
    setApiKey('');
    setModelsText('');
    setStatusMsg('');
  };

  const handleTest = async () => {
    if (!baseUrl.trim()) return;
    setStatusMsg('正在测试连接...');
    try {
      const res = await api.testProvider({ base_url: baseUrl.trim(), api_key: apiKey.trim() });
      if (res.models.length > 0 && !modelsText.trim()) {
        setModelsText(res.models.slice(0, 5).join(', '));
      }
      setStatusMsg(`连接成功（发现 ${res.models.length} 个模型）`);
    } catch (err) {
      setStatusMsg(`连接失败：${err instanceof Error ? err.message : '未知错误'}`);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const models = modelsText
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (!name.trim() || !baseUrl.trim() || models.length === 0) {
      setStatusMsg('请填写服务商名称、API 地址及至少一个模型 ID');
      return;
    }
    await saveProvider({
      id: providerId,
      name: name.trim(),
      base_url: baseUrl.trim(),
      api_key: apiKey.trim(),
      models,
    });
    setApiKey('');
    dialogRef.current?.close('saved');
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="model-settings-heading"
      {...({ closedby: 'any' } as Record<string, string>)}
    >
      <div className="flex h-[430px]">
        {/* Left Provider Rail */}
        <div
          className="w-[196px] border-r p-3 flex flex-col justify-between"
          style={{ background: 'var(--mc-sidebar)', borderColor: 'var(--mc-border)' }}
        >
          <div>
            <h1
              id="model-settings-heading"
              className="text-xs font-semibold px-2 pb-2 m-0"
              style={{ color: 'var(--mc-fg-muted)' }}
            >
              模型服务商
            </h1>
            <div className="space-y-1 text-[13px]">
              {providers.map((p) => (
                <div
                  key={p.id}
                  onClick={() => {
                    setProviderId(p.id);
                    setName(p.name);
                    setBaseUrl(p.base_url);
                    setModelsText(p.models.join(', '));
                    setApiKey('');
                    setStatusMsg('');
                  }}
                  className="group flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer"
                  style={{
                    background: p.id === providerId ? 'var(--mc-surface)' : 'transparent',
                  }}
                >
                  <span className="truncate font-medium">{p.name}</span>
                  <button
                    type="button"
                    aria-label={`移除服务商 ${p.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteProvider(p.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 cursor-pointer"
                    style={{ color: 'var(--mc-fg-muted)' }}
                  >
                    <Trash2 size={13} strokeWidth={1.75} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={startNewBlank}
            className="w-full h-8 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 cursor-pointer"
            style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
          >
            <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
            添加服务商
          </button>
        </div>

        {/* Right Configuration Form */}
        <form onSubmit={handleSave} className="flex-1 p-5 flex flex-col justify-between text-xs">
          <div className="space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">接口配置</span>
              <button
                type="button"
                aria-label="关闭设置弹窗"
                onClick={() => dialogRef.current?.close()}
                className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer"
                style={{ color: 'var(--mc-fg-muted)' }}
              >
                <X size={16} strokeWidth={1.75} aria-hidden="true" />
              </button>
            </div>

            <label className="block space-y-1">
              <span style={{ color: 'var(--mc-fg-muted)' }}>服务商名称</span>
              <input
                aria-label="服务商名称"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：DeepSeek / Gemini / 本地 Ollama"
                className="w-full h-8 px-2.5 rounded-lg border outline-none"
                style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
              />
            </label>

            <label className="block space-y-1">
              <span style={{ color: 'var(--mc-fg-muted)' }}>API 地址 (Base URL)</span>
              <input
                aria-label="API 地址"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.example.com/v1"
                className="w-full h-8 px-2.5 rounded-lg border outline-none font-mono"
                style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
              />
            </label>

            <label className="block space-y-1">
              <span style={{ color: 'var(--mc-fg-muted)' }}>API 密钥 (API Key)</span>
              <div className="flex gap-2">
                <input
                  type="password"
                  aria-label="API 密钥"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="填入 API Key（本地模型可留空）"
                  className="flex-1 h-8 px-2.5 rounded-lg border outline-none font-mono"
                  style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
                />
                <button
                  type="button"
                  onClick={handleTest}
                  className="h-8 px-3 rounded-lg border font-medium cursor-pointer"
                  style={{ borderColor: 'var(--mc-border)' }}
                >
                  测试并拉取模型
                </button>
              </div>
            </label>

            <label className="block space-y-1">
              <span style={{ color: 'var(--mc-fg-muted)' }}>可用模型 ID（英文逗号分隔）</span>
              <input
                aria-label="可用模型 ID"
                value={modelsText}
                onChange={(e) => setModelsText(e.target.value)}
                placeholder="deepseek-chat, gemini-2.5-flash"
                className="w-full h-8 px-2.5 rounded-lg border outline-none font-mono"
                style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
              />
            </label>
          </div>

          <div
            className="flex items-center justify-between pt-3 border-t"
            style={{ borderColor: 'var(--mc-border)' }}
          >
            <span style={{ color: 'var(--mc-fg-muted)' }}>{statusMsg || '兼容 OpenAI /v1 协议端点'}</span>
            <button
              type="submit"
              className="h-8 px-4 rounded-lg font-medium cursor-pointer"
              style={{ background: 'var(--mc-primary)', color: 'var(--mc-primary-fg)' }}
            >
              保存配置
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
