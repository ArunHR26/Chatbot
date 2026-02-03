'use client';

import { useState, useCallback } from 'react';
import { Upload, X, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument } from '@/lib/api';
import clsx from 'clsx';

interface FileUploadProps {
    onClose: () => void;
}

interface UploadedFile {
    name: string;
    status: 'uploading' | 'success' | 'error';
    message?: string;
    chunks?: number;
}

export default function FileUpload({ onClose }: FileUploadProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [files, setFiles] = useState<UploadedFile[]>([]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const processFile = async (file: File) => {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setFiles(prev => [
                ...prev,
                { name: file.name, status: 'error', message: 'Only PDF files are supported' }
            ]);
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            setFiles(prev => [
                ...prev,
                { name: file.name, status: 'error', message: 'File size exceeds 50MB limit' }
            ]);
            return;
        }

        setFiles(prev => [...prev, { name: file.name, status: 'uploading' }]);

        try {
            const result = await uploadDocument(file);
            setFiles(prev =>
                prev.map(f =>
                    f.name === file.name
                        ? { ...f, status: 'success', message: result.message, chunks: result.chunks_created }
                        : f
                )
            );
        } catch (error) {
            setFiles(prev =>
                prev.map(f =>
                    f.name === file.name
                        ? { ...f, status: 'error', message: error instanceof Error ? error.message : 'Upload failed' }
                        : f
                )
            );
        }
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const droppedFiles = Array.from(e.dataTransfer.files);
        droppedFiles.forEach(processFile);
    }, []);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const selectedFiles = Array.from(e.target.files);
            selectedFiles.forEach(processFile);
        }
    }, []);

    return (
        <div className="max-w-2xl mx-auto">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Upload Documents</h2>
                <button
                    onClick={onClose}
                    className="p-2 rounded-lg hover:bg-dark-700 transition-colors"
                >
                    <X className="w-5 h-5 text-dark-400" />
                </button>
            </div>

            {/* Drop Zone */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={clsx(
                    'relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 cursor-pointer',
                    isDragging
                        ? 'border-accent-primary bg-accent-primary/5'
                        : 'border-dark-600 hover:border-dark-500 bg-dark-800/30'
                )}
            >
                <input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={handleFileSelect}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="flex flex-col items-center">
                    <div
                        className={clsx(
                            'w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-all',
                            isDragging
                                ? 'bg-accent-primary shadow-glow scale-110'
                                : 'bg-dark-700'
                        )}
                    >
                        <Upload className={clsx('w-7 h-7', isDragging ? 'text-white' : 'text-dark-400')} />
                    </div>
                    <p className="font-medium mb-1">
                        {isDragging ? 'Drop your files here' : 'Drag & drop PDF files here'}
                    </p>
                    <p className="text-sm text-dark-400">or click to browse (max 50MB)</p>
                </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
                <div className="mt-4 space-y-2">
                    {files.map((file, index) => (
                        <div
                            key={index}
                            className={clsx(
                                'flex items-center gap-3 p-3 rounded-xl border transition-all',
                                file.status === 'uploading' && 'bg-dark-800/50 border-dark-600',
                                file.status === 'success' && 'bg-emerald-500/5 border-emerald-500/30',
                                file.status === 'error' && 'bg-red-500/5 border-red-500/30'
                            )}
                        >
                            <div
                                className={clsx(
                                    'flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
                                    file.status === 'uploading' && 'bg-dark-700',
                                    file.status === 'success' && 'bg-emerald-500/10',
                                    file.status === 'error' && 'bg-red-500/10'
                                )}
                            >
                                {file.status === 'uploading' && (
                                    <Loader2 className="w-5 h-5 text-accent-primary animate-spin" />
                                )}
                                {file.status === 'success' && (
                                    <CheckCircle className="w-5 h-5 text-emerald-500" />
                                )}
                                {file.status === 'error' && (
                                    <AlertCircle className="w-5 h-5 text-red-500" />
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate">{file.name}</p>
                                {file.message && (
                                    <p
                                        className={clsx(
                                            'text-xs',
                                            file.status === 'success' && 'text-emerald-400',
                                            file.status === 'error' && 'text-red-400',
                                            file.status === 'uploading' && 'text-dark-400'
                                        )}
                                    >
                                        {file.status === 'uploading' ? 'Uploading...' : file.message}
                                    </p>
                                )}
                                {file.chunks && (
                                    <p className="text-xs text-dark-400">{file.chunks} chunks created</p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
