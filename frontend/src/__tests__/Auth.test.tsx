// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Login } from '../pages/Login';
import { apiClient } from '../api/client';

vi.mock('../api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe('Login Component', () => {
  it('renders login form and submits credentials', async () => {
    (apiClient.post as any).mockResolvedValue({
      data: {
        access_token: 'fake-token',
        user: { username: 'test_user', role: 'HQ_OFFICER' }
      }
    });

    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );

    expect(screen.getByText('CMPDI Secure Portal')).toBeDefined();

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitBtn = screen.getByRole('button', { name: /Authenticate/i });

    fireEvent.change(usernameInput, { target: { value: 'hq_officer' } });
    fireEvent.change(passwordInput, { target: { value: 'Admin123!' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled();
    });
  });
});
