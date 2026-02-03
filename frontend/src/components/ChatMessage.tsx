'use client';

import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '@/lib/api';
import clsx from 'clsx';

interface ChatMessageProps {
    message: Message;
    isStreaming?: boolean;
}

export default function ChatMessage({ message, isStreaming }: ChatMessageProps) {
    const isUser = message.role === 'user';

    return (
        <div
            className={clsx(
                'flex gap-4 animate-fade-in-up',
                isUser ? 'flex-row-reverse' : 'flex-row'
            )}
        >
            {/* Avatar */}
            <div
                className={clsx(
                    'flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center',
                    isUser
                        ? 'bg-accent-primary shadow-glow'
                        : 'bg-gradient-to-br from-emerald-500 to-teal-600'
                )}
            >
                {isUser ? (
                    <User className="w-5 h-5 text-white" />
                ) : (
                    <Bot className="w-5 h-5 text-white" />
                )}
            </div>

            {/* Message Content */}
            <div
                className={clsx(
                    'flex-1 max-w-[80%]',
                    isUser ? 'text-right' : 'text-left'
                )}
            >
                <div
                    className={clsx(
                        'inline-block rounded-2xl px-5 py-3.5 text-left',
                        isUser
                            ? 'bg-accent-primary text-white rounded-tr-md'
                            : 'bg-dark-800 border border-dark-700 rounded-tl-md'
                    )}
                >
                    {isUser ? (
                        <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    ) : (
                        <div className="markdown-content text-[15px]">
                            {message.content ? (
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        // Custom code block styling
                                        code({ node, inline, className, children, ...props }) {
                                            return inline ? (
                                                <code className={className} {...props}>
                                                    {children}
                                                </code>
                                            ) : (
                                                <pre className="overflow-x-auto">
                                                    <code className={className} {...props}>
                                                        {children}
                                                    </code>
                                                </pre>
                                            );
                                        },
                                        // Open links in new tab
                                        a({ node, children, ...props }) {
                                            return (
                                                <a target="_blank" rel="noopener noreferrer" {...props}>
                                                    {children}
                                                </a>
                                            );
                                        },
                                    }}
                                >
                                    {message.content}
                                </ReactMarkdown>
                            ) : isStreaming ? (
                                <span className="loading-dots inline-flex gap-1">
                                    <span className="w-2 h-2 rounded-full bg-accent-primary"></span>
                                    <span className="w-2 h-2 rounded-full bg-accent-primary"></span>
                                    <span className="w-2 h-2 rounded-full bg-accent-primary"></span>
                                </span>
                            ) : null}

                            {/* Streaming cursor */}
                            {isStreaming && message.content && (
                                <span className="inline-block w-2 h-5 bg-accent-primary ml-0.5 animate-pulse-subtle rounded-sm" />
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
