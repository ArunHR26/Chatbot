'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Send, Sparkles, FileText, Bot, User, Loader2, AlertCircle } from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import ChatMessage from '@/components/ChatMessage';
import { sendChatMessage, Message } from '@/lib/api';

export default function Home() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [sources, setSources] = useState<string[]>([]);
    const [showUpload, setShowUpload] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-resize textarea
    useEffect(() => {
        if (inputRef.current) {
            inputRef.current.style.height = 'auto';
            inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
        }
    }, [input]);

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = { role: 'user', content: input.trim() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setError(null);
        setSources([]);

        // Add placeholder for assistant message
        const assistantMessage: Message = { role: 'assistant', content: '' };
        setMessages(prev => [...prev, assistantMessage]);

        try {
            await sendChatMessage(
                userMessage.content,
                messages,
                // Handle streaming content
                (chunk) => {
                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastMessage = newMessages[newMessages.length - 1];
                        if (lastMessage.role === 'assistant') {
                            lastMessage.content += chunk;
                        }
                        return newMessages;
                    });
                },
                // Handle sources
                (newSources) => {
                    setSources(newSources);
                }
            );
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
            // Remove empty assistant message on error
            setMessages(prev => prev.filter(m => m.content !== ''));
        } finally {
            setIsLoading(false);
        }
    }, [input, isLoading, messages]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as unknown as React.FormEvent);
        }
    };

    return (
        <div className="flex flex-col h-screen max-h-screen">
            {/* Header */}
            <header className="glass border-b border-dark-700 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-purple-500 flex items-center justify-center shadow-glow">
                        <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-semibold gradient-text">Cloud-Native RAG</h1>
                        <p className="text-xs text-dark-400">AI-Powered Knowledge Assistant</p>
                    </div>
                </div>
                <button
                    onClick={() => setShowUpload(!showUpload)}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-dark-800 hover:bg-dark-700 border border-dark-600 transition-all duration-200 hover:border-accent-primary/50 group"
                >
                    <FileText className="w-4 h-4 text-dark-400 group-hover:text-accent-primary transition-colors" />
                    <span className="text-sm font-medium">Upload Document</span>
                </button>
            </header>

            {/* Upload Panel */}
            {showUpload && (
                <div className="p-6 border-b border-dark-700 animate-fade-in-up">
                    <FileUpload onClose={() => setShowUpload(false)} />
                </div>
            )}

            {/* Messages Area */}
            <main className="flex-1 overflow-y-auto px-4 py-6">
                <div className="max-w-4xl mx-auto space-y-6">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
                            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent-primary to-purple-500 flex items-center justify-center mb-6 shadow-glow-lg">
                                <Bot className="w-10 h-10 text-white" />
                            </div>
                            <h2 className="text-2xl font-semibold mb-3 gradient-text">Welcome to Cloud-Native RAG</h2>
                            <p className="text-dark-400 max-w-md mb-8">
                                Upload your documents and ask questions. I'll search through your knowledge base
                                to provide accurate, context-aware answers.
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-2xl">
                                {[
                                    { icon: '📄', title: 'Upload PDFs', desc: 'Add documents to your knowledge base' },
                                    { icon: '🔍', title: 'Ask Questions', desc: 'Query your documents naturally' },
                                    { icon: '✨', title: 'Get Answers', desc: 'AI-powered contextual responses' },
                                ].map((item, i) => (
                                    <div
                                        key={i}
                                        className="p-4 rounded-xl bg-dark-800/50 border border-dark-700 hover:border-accent-primary/30 transition-all"
                                    >
                                        <div className="text-2xl mb-2">{item.icon}</div>
                                        <h3 className="font-medium text-sm mb-1">{item.title}</h3>
                                        <p className="text-xs text-dark-400">{item.desc}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        messages.map((message, index) => (
                            <ChatMessage
                                key={index}
                                message={message}
                                isStreaming={isLoading && index === messages.length - 1}
                            />
                        ))
                    )}

                    {/* Sources */}
                    {sources.length > 0 && !isLoading && (
                        <div className="flex flex-wrap gap-2 pl-14 animate-fade-in-up">
                            <span className="text-xs text-dark-400">Sources:</span>
                            {sources.map((source, i) => (
                                <span
                                    key={i}
                                    className="text-xs px-2 py-1 rounded-md bg-dark-800 border border-dark-600 text-dark-300"
                                >
                                    {source}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Error */}
                    {error && (
                        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 animate-fade-in-up">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <p className="text-sm">{error}</p>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </main>

            {/* Input Area */}
            <footer className="border-t border-dark-700 p-4">
                <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
                    <div className="relative flex items-end gap-3 p-2 rounded-2xl bg-dark-800 border border-dark-600 focus-within:border-accent-primary/50 transition-colors">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask a question about your documents..."
                            className="flex-1 bg-transparent resize-none outline-none text-dark-100 placeholder-dark-500 px-2 py-2 min-h-[44px] max-h-[200px]"
                            rows={1}
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className="p-3 rounded-xl bg-accent-primary hover:bg-accent-hover disabled:bg-dark-700 disabled:cursor-not-allowed transition-all duration-200 btn-glow"
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 text-white animate-spin" />
                            ) : (
                                <Send className="w-5 h-5 text-white" />
                            )}
                        </button>
                    </div>
                    <p className="text-xs text-dark-500 text-center mt-2">
                        Press Enter to send, Shift+Enter for new line
                    </p>
                </form>
            </footer>
        </div>
    );
}
