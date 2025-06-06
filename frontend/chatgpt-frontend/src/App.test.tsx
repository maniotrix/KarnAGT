import { render, screen } from '@testing-library/react';
import App from './App';

test('renders ChatGPT Clone app', () => {
  render(<App />);
  const titleElement = screen.getByText(/ChatGPT Clone/i);
  expect(titleElement).toBeInTheDocument();
});
