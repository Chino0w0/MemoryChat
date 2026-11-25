import { useEffect, useRef, useState } from 'react';
import { Check, KeyRound, Link2, Sparkles, X } from 'lucide-react';
import type { ProviderPreset } from '../types';

interface Props {
  open: boolean;
  presets: ProviderPreset[];
  onClose: () => void;
  onSave: (payload: { id: string; name: string; base_url: string; api_key: string; models: string[] }) => Promise<void>;
}

export function ProviderDialog({ open, presets, onClose, onSave }: Props) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const [selectedId, setSelectedId] = useState<string>('deepseek');
  const [name, setName] = useState<string>('DeepSeek');
  const [baseUrl, setBaseUrl] = useState<string>('https://api.deepseek.com/v1');
  const [apiKey, setApiKey] = useState<string>('');
  const [modelsText, setModelsText] = useState<string>('deepseek-chat, deepseek-reasoner');
  const [saving, setSaving] = useState<boolean>(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.hasAttribute('open')) {
      dialog.showModal();
    } else if (!open && dialog.hasAttribute('open')) {
      dialog.close();
    }
  }, [open]);

  // Mandatory coordinate-checked fallback when <dialog closedby="any"> is not natively supported
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleClose = () => {
      dialog.returnValue = '';
      onClose();
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
  }, [onClose]);

  const applyPreset = (p: ProviderPreset) => {
    setSelectedId(p.id);
    setName(p.name);
    setBaseUrl(p.base_url);
    setModelsText(p.models.join(', '));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const models = modelsText
        .split(',')
        .map((m) => m.trim())
        .filter(Boolean);
      await onSave({
        id: selectedId.trim() || 'custom',
        name: name.trim() || selectedId,
        base_url: baseUrl.trim(),
        api_key: apiKey.trim(),
        models: models.length ? models : ['default'],
      });
      setApiKey('');
      dialogRef.current?.close('saved');
    } finally {
      setSaving(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="provider-dialog-title"
      {...({ closedby: 'any' } as Record<string, string>)}
    >
      <div style={{ padding: '18px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <h1 id="provider-dialog-title" style={{ margin: 0, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} aria-hidden="true" color="var(--brand)" />
            模型连接
          </h1>
          <button
            type="button"
            className="icon-btn"
            style={{ padding: 6 }}
            aria-label="关闭窗口"
            onClick={() => dialogRef.current?.close()}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        {/* 1-Click Visual Brand Preset Grid */}
        <div className="preset-grid" style={{ marginBottom: 16 }}>
          {presets.map((p) => (
            <button
              key={p.id}
              type="button"
              aria-label={`选择预设 ${p.name}`}
              className={`preset-card ${selectedId === p.id ? 'selected' : ''}`}
              onClick={() => applyPreset(p)}
            >
              <span style={{ fontSize: 20 }} aria-hidden="true">
                {p.badge}
              </span>
              <span>{p.name}</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface-muted)', padding: '8px 12px', borderRadius: 12, border: '1px solid var(--border)' }}>
            <Link2 size={15} aria-hidden="true" color="var(--fg-muted)" />
            <input
              aria-label="API 地址"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.../v1"
              style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', color: 'var(--fg)', fontSize: 13 }}
            />
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface-muted)', padding: '8px 12px', borderRadius: 12, border: '1px solid var(--border)' }}>
            <KeyRound size={15} aria-hidden="true" color="var(--fg-muted)" />
            <input
              type="password"
              aria-label="API Key"
              autoFocus
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="API Key"
              style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', color: 'var(--fg)', fontSize: 13 }}
            />
          </label>

          <input
            aria-label="模型列表"
            value={modelsText}
            onChange={(e) => setModelsText(e.target.value)}
            placeholder="model-a, model-b"
            style={{ background: 'var(--surface-muted)', padding: '8px 12px', borderRadius: 12, border: '1px solid var(--border)', color: 'var(--fg)', fontSize: 12 }}
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 6 }}>
            <button
              type="submit"
              disabled={saving}
              className="icon-btn primary"
              aria-label="保存模型连接"
            >
              <Check size={15} aria-hidden="true" />
              连接
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
