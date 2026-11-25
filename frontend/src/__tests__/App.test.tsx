import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

describe('MemoryChat Mainstream Chat UI (Zero Presets)', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockImplementation((url: string, init?: RequestInit) => {
      if (url.includes('/api/providers') && init?.method === 'POST' && !url.includes('/test')) {
        const body = JSON.parse(String(init.body));
        return jsonResponse({ ...body, is_enabled: true, has_key: true });
      }
      if (url.includes('/api/providers')) {
        return jsonResponse([]);
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
            content: '接口风格偏好 FastAPI',
            confidence: 0.95,
            is_pinned: true,
            is_enabled: true,
            status: 'active',
            created_at: '2026-11-25T15:00:00Z',
          },
        ]);
      }
      if (url.includes('/api/summaries') || url.includes('/api/skills')) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    });
  });

  it('starts unconfigured with centered mainstream composer, toggles incognito & drawer, and saves custom provider', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('有什么可以帮你？')).toBeInTheDocument();
    });
    // Starts cleanly with zero fake providers
    expect(screen.getByText('未配置模型')).toBeInTheDocument();

    // Incognito toggle
    const incogBtn = screen.getByRole('button', { name: /无痕对话开关/i });
    expect(incogBtn).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(incogBtn);
    expect(incogBtn).toHaveAttribute('aria-pressed', 'true');

    // Memory inspector drawer toggle
    const memBtn = screen.getByRole('button', { name: /记忆面板开关/i });
    fireEvent.click(memBtn);
    expect(await screen.findByText('接口风格偏好 FastAPI')).toBeInTheDocument();

    // Clicking unconfigured model button opens custom provider modal
    fireEvent.click(screen.getByRole('button', { name: /切换或配置模型/i }));
    fireEvent.change(screen.getByLabelText(/服务商名称/i), { target: { value: 'DeepSeek' } });
    fireEvent.change(screen.getByLabelText(/API 地址/i), { target: { value: 'https://api.deepseek.com/v1' } });
    fireEvent.change(screen.getByLabelText(/可用模型 ID/i), { target: { value: 'deepseek-chat' } });
    fireEvent.click(screen.getByRole('button', { name: /保存配置/i }));

    await waitFor(() => {
      expect(screen.getByText('deepseek-chat')).toBeInTheDocument();
    });
  });
});
