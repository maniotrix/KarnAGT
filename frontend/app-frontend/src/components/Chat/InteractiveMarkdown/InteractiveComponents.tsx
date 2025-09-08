import React, { useState } from 'react';
import { Play, Download, ExternalLink, RefreshCw, Check, X } from 'lucide-react';

// Interactive Button Component
export const ActionButton: React.FC<{
  children: React.ReactNode;
  action?: string;
  url?: string;
  variant?: 'primary' | 'secondary' | 'success' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}> = ({ children, action, url, variant = 'primary', size = 'md' }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleClick = async () => {
    if (url) {
      // Open external URL
      window.open(url, '_blank', 'noopener noreferrer');
      return;
    }

    if (action) {
      setLoading(true);
      try {
        // Simulate API call based on action
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        switch (action) {
          case 'run_code':
            setResult('Code executed successfully!');
            break;
          case 'download':
            setResult('Download started!');
            break;
          case 'refresh':
            setResult('Data refreshed!');
            break;
          default:
            setResult('Action completed!');
        }
        
        // Clear result after 3 seconds
        setTimeout(() => setResult(null), 3000);
      } catch (error) {
        setResult('Action failed!');
        setTimeout(() => setResult(null), 3000);
      } finally {
        setLoading(false);
      }
    }
  };

  const getVariantClasses = () => {
    switch (variant) {
      case 'secondary':
        return 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 border border-gray-300 dark:border-gray-600';
      case 'success':
        return 'bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600 text-white';
      case 'danger':
        return 'bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600 text-white';
      default:
        return 'bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 text-white';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-2 py-1';
      case 'lg':
        return 'px-6 py-3';
      default:
        return 'px-4 py-2';
    }
  };

  const getIcon = () => {
    if (loading) return <RefreshCw className="w-4 h-4 animate-spin" />;
    if (result) {
      return result.includes('success') || result.includes('completed') || result.includes('started') 
        ? <Check className="w-4 h-4" />
        : <X className="w-4 h-4" />;
    }
    
    switch (action) {
      case 'run_code':
        return <Play className="w-4 h-4" />;
      case 'download':
        return <Download className="w-4 h-4" />;
      case 'refresh':
        return <RefreshCw className="w-4 h-4" />;
      default:
        return url ? <ExternalLink className="w-4 h-4" /> : null;
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={`
        inline-flex items-center gap-2 rounded-lg font-medium transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed
        ${getVariantClasses()} ${getSizeClasses()}
      `}
    >
      {getIcon()}
      {result || children}
    </button>
  );
};

// Interactive Form Component
export const QuickForm: React.FC<{
  title?: string;
  placeholder?: string;
  buttonText?: string;
  action?: string;
}> = ({ 
  title = "Quick Input", 
  placeholder = "Enter value...", 
  buttonText = "Submit",
  action = "submit"
}) => {
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;

    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setResult(`Submitted: "${value}"`);
      setValue('');
      setTimeout(() => setResult(null), 3000);
    } catch (error) {
      setResult('Submission failed!');
      setTimeout(() => setResult(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">{title}</h4>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          className="flex-1 px-3 py-2 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="px-4 py-2 bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading && <RefreshCw className="w-4 h-4 animate-spin" />}
          {buttonText}
        </button>
      </form>
      {result && (
        <div className="mt-2 text-green-600 dark:text-green-400">
          {result}
        </div>
      )}
    </div>
  );
};

// Code Runner Component
export const CodeRunner: React.FC<{
  code: string;
  language?: string;
}> = ({ code, language = 'javascript' }) => {
  const [output, setOutput] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const runCode = async () => {
    setLoading(true);
    try {
      // Simulate code execution
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Mock different outputs based on language
      switch (language) {
        case 'python':
          setOutput('Output: Hello from Python!\nExecution completed successfully.');
          break;
        case 'javascript':
          setOutput('Output: Hello from JavaScript!\n> true');
          break;
        default:
          setOutput('Code executed successfully!');
      }
    } catch (error) {
      setOutput('Error: Code execution failed!');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">Code Runner ({language})</h4>
        <button
          onClick={runCode}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1 bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600 text-white rounded-md disabled:opacity-50"
        >
          {loading ? (
            <RefreshCw className="w-3 h-3 animate-spin" />
          ) : (
            <Play className="w-3 h-3" />
          )}
          {loading ? 'Running...' : 'Run Code'}
        </button>
      </div>
      
      <pre className="bg-gray-900 text-gray-100 p-3 rounded-md mb-3 overflow-x-auto">
        <code>{code}</code>
      </pre>
      
      {output && (
        <div className="mt-3 p-3 bg-black text-green-400 rounded-md font-mono">
          <div className="text-gray-400 mb-1">Output:</div>
          <pre>{output}</pre>
        </div>
      )}
    </div>
  );
};

// API Data Fetcher Component
export const DataFetcher: React.FC<{
  endpoint?: string;
  title?: string;
}> = ({ endpoint = '/api/example', title = 'Fetch Data' }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock API response
      const mockData = {
        timestamp: new Date().toISOString(),
        data: {
          users: 1234,
          posts: 5678,
          comments: 9012
        },
        status: 'success'
      };
      
      setData(mockData);
    } catch (err) {
      setError('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">{title}</h4>
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1 bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 text-white rounded-md disabled:opacity-50"
        >
          {loading ? (
            <RefreshCw className="w-3 h-3 animate-spin" />
          ) : (
            <RefreshCw className="w-3 h-3" />
          )}
          {loading ? 'Fetching...' : 'Fetch Data'}
        </button>
      </div>
      
      {error && (
        <div className="text-red-600 dark:text-red-400 mb-2">
          Error: {error}
        </div>
      )}
      
      {data && (
        <div className="bg-white dark:bg-gray-900 p-3 rounded-md">
          <pre className="text-gray-800 dark:text-gray-200">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};