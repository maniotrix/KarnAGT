export type Theme = 'light' | 'dark' | 'user' | 'assistant';

export interface InteractiveMarkdownProps {
  content: string;
  className?: string;
  theme?: Theme;
}

export interface ThemeStyles {
  codeBlock: string;
  inlineCode: string;
  link: string;
  table: TableStyles;
}

export interface TableStyles {
  wrapper: string;
  table: string;
  headerRow: string;
  headerCell: string;
  bodyRowHover: string;
  bodyCell: string;
}

export interface MarkdownComponentProps {
  theme: Theme;
  children?: React.ReactNode;
  [key: string]: any;
}
