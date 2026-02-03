import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Cloud-Native RAG | AI Knowledge Assistant',
    description: 'Upload documents and chat with your knowledge base using AI-powered retrieval augmented generation.',
    keywords: ['RAG', 'AI', 'Chat', 'Knowledge Base', 'Document Analysis'],
    authors: [{ name: 'Cloud-Native RAG Team' }],
    viewport: 'width=device-width, initial-scale=1',
    themeColor: '#0d0d0f',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className="min-h-screen bg-dark-950 text-dark-100 antialiased">
                {children}
            </body>
        </html>
    );
}
