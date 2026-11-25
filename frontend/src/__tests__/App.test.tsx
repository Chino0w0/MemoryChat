import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;

function jsonResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  });
}

describe('MemoryChat Minimal-Text Graphical UI', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/providers/presets')) {
        return jsonResponse([
          {
            id: 'demo',
            name: 'Local Demo',
            badge: '⚡',
            base_url: 'local://demo',
            models: ['memorychat-demo'],
            requires_key: false,
          },
          {
            id: 'deepseek',
            name: 'DeepSeek',
            badge: '🐋',
            base_url: 'https://api.deepseek.com/v1',
            models: ['deepseek-chat', 'deepseek-reasoner'],
            requires_key: true,
          },
        ]);
      }
      if (url.includes('/api/providers')) {
        return jsonResponse([
          {
            id: 'demo',
            name: 'Local Demo',
            base_url: 'local://demo',
            models: ['memorychat-demo'],
            is_enabled: true,
            has_key: true,
          },
        ]);
      }
      if (url.includes('/api/conversations') && !url.includes('/messages')) {
        return jsonResponse([]);
      }
      if (url.includes('/api/memories')) {
        return jsonResponse([
          {
            id: 'm1',
            layer: 'profile',
            category: 'preference',
            content: '偏爱 FastAPI',
            confidence: 0.95,
            is_pinned: true,
            is_enabled: true,
            status: 'active',
            created_at: '2026-11-25T15:00:00Z',
          },
        ]);
      }
      if (url.includes('/api/extensions/slots')) {
        return jsonResponse([
          { slot: 'asr', label: 'ASR', status: 'reserved' },
          { slot: 'skill', label: 'Skill', status: 'reserved' },
          { slot: 'tool', label: 'Tool', status: 'reserved' },
        ]);
      }
      return jsonResponse({});
    });
  });

  it('renders visual starter cards, incognito toggle, memory drawer, and brand presets', async () => {
    render(<App />);

    // 3 graphical starter action buttons appear instead of instructional paragraphs
    await waitFor(() => {
      expect(screen.getByTestId('starter-cards')).toBeInTheDocument();
    });
    const starterGrid = screen.getByTestId('starter-cards');
    expect(within(starterGrid).getAllByRole('button', { name: /录入画像|接入模型|试试记忆/i }).length).toBe(3);

    // Incognito ghost button toggles aria-pressed
    const incogBtn = screen.getByRole('button', { name: /无痕模式/i });
    expect(incogBtn).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(incogBtn);
    expect(incogBtn).toHaveAttribute('aria-pressed', 'true');

    // Memory badge button opens visual drawer showing stored memory card
    const memBtn = screen.getByRole('button', { name: /记忆面板/i });
    fireEvent.click(memBtn);
    expect(await screen.findByText('偏爱 FastAPI')).toBeInTheDocument();

    // Provider modal opens and clicking DeepSeek preset card auto-populates Base URL
    const modelBtn = screen.getByRole('button', { name: /切换或接入模型/i });
    fireEvent.click(modelBtn);
    const addProviderBtn = await screen.findByRole('button', { name: /管理模型供应商/i });
    fireEvent.click(addProviderBtn);

    const deepseekPreset = await screen.findByRole('button', { name: /选择预设 DeepSeek/i });
    fireEvent.click(deepseekPreset);
    const urlInput = screen.getByLabelText(/API 地址/i) as HTMLInputElement;
    expect(urlInput.value).toBe('https://api.deepseek.com/v1');
  });
});
