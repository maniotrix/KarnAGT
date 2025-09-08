import { render, screen } from '@testing-library/react';
import App from './App';

test('renders KarnAGT app', () => {
  render(<App />);
  const titleElement = screen.getByText(/KarnAGT/i);
  expect(titleElement).toBeInTheDocument();
});
