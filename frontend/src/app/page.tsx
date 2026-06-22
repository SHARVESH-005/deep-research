'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function Home() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [report, setReport] = useState<string>('');
  const [error, setError] = useState<string>('');
  const ws = useRef<WebSocket | null>(null);
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setIsSearching(true);
    setStatus('Initializing connection...');
    setReport('');
    setError('');
    
    // Connect to WebSocket
    ws.current = new WebSocket('ws://localhost:8000/ws/research');
    
    ws.current.onopen = () => {
      ws.current?.send(JSON.stringify({ query }));
    };
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'status') {
        setStatus(data.data);
      } else if (data.type === 'node_update') {
        setStatus(`Agent running: ${data.node}`);
        
        if (data.node === 'planner' && data.state.plan) {
           // We could show the plan
        }
        
        if (data.node === 'synthesizer' && data.state.draft_report) {
           setReport(data.state.draft_report);
        }
      } else if (data.type === 'done') {
        setIsSearching(false);
        setStatus('');
        ws.current?.close();
      } else if (data.type === 'error') {
        setError(data.message);
        setIsSearching(false);
        setStatus('');
      }
    };
    
    ws.current.onerror = () => {
      setError('Connection error with the backend.');
      setIsSearching(false);
      setStatus('');
    };
    
    ws.current.onclose = () => {
      if (isSearching) {
         // Unexpected close
         setIsSearching(false);
         setStatus('');
      }
    };
  };

  return (
    <main className="min-h-screen bg-white text-gray-900 font-sans">
      <div className="max-w-4xl mx-auto px-4 py-12 flex flex-col">
        
        <header className="mb-12">
          <h1 className="text-3xl font-bold mb-2">Deep Research</h1>
          <p className="text-gray-600">Autonomous Multi-Agent Synthesizer</p>
        </header>

        <form onSubmit={handleSearch} className="flex gap-4 mb-8">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What do you want to research today?"
            className="flex-1 border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isSearching}
          />
          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isSearching ? 'Researching...' : 'Search'}
          </button>
        </form>

        {status && (
          <div className="mb-8 text-blue-600 font-medium">
            Status: {status}
          </div>
        )}

        {error && (
          <div className="mb-8 p-4 bg-red-50 text-red-700 border border-red-200 rounded-md">
            {error}
          </div>
        )}

        {report && (
          <div className="prose max-w-none">
            <ReactMarkdown>{report}</ReactMarkdown>
          </div>
        )}
        
      </div>
    </main>
  );
}
