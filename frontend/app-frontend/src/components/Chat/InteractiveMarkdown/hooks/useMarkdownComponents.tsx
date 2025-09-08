import React from 'react';
import { Theme } from '../types';

// Component imports
import { LinkComponent } from '../components/LinkComponent';
import { 
  TableComponent, 
  TheadComponent, 
  ThComponent, 
  TbodyComponent, 
  TrComponent, 
  TdComponent 
} from '../components/TableComponents';
import { 
  H1Component, 
  H2Component, 
  H3Component, 
  H4Component, 
  H5Component, 
  H6Component 
} from '../components/HeadingComponents';
import { 
  ParagraphComponent, 
  StrongComponent, 
  EmComponent, 
  BlockquoteComponent, 
  HrComponent, 
  ImgComponent 
} from '../components/TextComponents';
import { UlComponent, OlComponent, LiComponent } from '../components/ListComponents';

// Code Block Components (assuming these exist)
import { CodeComponent, PreBlock } from '../CodeBlock';

// Interactive Components (assuming these exist)
import { ActionButton, QuickForm, CodeRunner, DataFetcher } from '../InteractiveComponents';

// Theme utilities
import { getThemeStyles } from '../utils/themeUtils';

export const useMarkdownComponents = (theme: Theme) => {
  const styles = getThemeStyles(theme);

  return React.useMemo(() => ({
    // Enhanced pre blocks with copy button
    pre: ({ children, ...props }: any) => (
      <PreBlock {...props} className={styles.codeBlock}>
        {children}
      </PreBlock>
    ),

    // Enhanced code with copy functionality
    code: ({ children, className, inline, ...props }: any) => {
      if (inline) {
        return (
          <CodeComponent 
            {...props} 
            className={styles.inlineCode}
            inline={true}
          >
            {children}
          </CodeComponent>
        );
      } else {
        return (
          <code 
            {...props} 
            className={className}
          >
            {children}
          </code>
        );
      }
    },

    // Link component with theme
    a: (props: any) => <LinkComponent {...props} theme={theme} />,

    // Table components
    table: (props: any) => <TableComponent {...props} theme={theme} />,
    thead: (props: any) => <TheadComponent {...props} theme={theme} />,
    th: (props: any) => <ThComponent {...props} theme={theme} />,
    tbody: (props: any) => <TbodyComponent {...props} theme={theme} />,
    tr: (props: any) => <TrComponent {...props} theme={theme} />,
    td: (props: any) => <TdComponent {...props} theme={theme} />,

    // Heading components
    h1: (props: any) => <H1Component {...props} theme={theme} />,
    h2: (props: any) => <H2Component {...props} theme={theme} />,
    h3: (props: any) => <H3Component {...props} theme={theme} />,
    h4: (props: any) => <H4Component {...props} theme={theme} />,
    h5: (props: any) => <H5Component {...props} theme={theme} />,
    h6: (props: any) => <H6Component {...props} theme={theme} />,

    // Text components
    p: (props: any) => <ParagraphComponent {...props} theme={theme} />,
    strong: (props: any) => <StrongComponent {...props} theme={theme} />,
    em: (props: any) => <EmComponent {...props} theme={theme} />,
    blockquote: (props: any) => <BlockquoteComponent {...props} theme={theme} />,
    hr: (props: any) => <HrComponent {...props} theme={theme} />,
    img: (props: any) => <ImgComponent {...props} theme={theme} />,

    // List components
    ul: (props: any) => <UlComponent {...props} theme={theme} />,
    ol: (props: any) => <OlComponent {...props} theme={theme} />,
    li: (props: any) => <LiComponent {...props} theme={theme} />,

    // Interactive Components
    ActionButton: (props: any) => <ActionButton {...props} />,
    QuickForm: (props: any) => <QuickForm {...props} />,
    CodeRunner: (props: any) => <CodeRunner {...props} />,
    DataFetcher: (props: any) => <DataFetcher {...props} />,
  }), [theme, styles]);
};
