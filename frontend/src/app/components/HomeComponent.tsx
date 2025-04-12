'use client';

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { Upload, CloudDownload, Sparkles } from "lucide-react";
import Image from "next/image";

// API endpoint configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_GOST_API_URL || 'http://localhost:5000';

export default function HomeComponent() {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [documentUrl, setDocumentUrl] = useState<string | null>(null);
    const [fileName, setFileName] = useState<string>("document.docx");
    const [apiStatus, setApiStatus] = useState<'loading' | 'online' | 'offline'>('loading');
    const [warnings, setWarnings] = useState<string[]>([]);
    const [useLLM, setUseLLM] = useState<boolean>(true);
    
    // Metadata state
    const [title, setTitle] = useState<string>("");
    const [author, setAuthor] = useState<string>("");
    const [institution, setInstitution] = useState<string>("");
    const [city, setCity] = useState<string>("");
    const [year, setYear] = useState<string>("");

    // Check API status on component mount
    useEffect(() => {
        const checkApiStatus = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/health`, {
                    method: 'GET',
                    mode: 'cors',
                });
                
                if (response.ok) {
                    setApiStatus('online');
                } else {
                    setApiStatus('offline');
                }
            } catch (error) {
                console.error('Error checking API status:', error);
                setApiStatus('offline');
            }
        };
        
        checkApiStatus();
    }, []);

    const handleSubmit = async () => {
        if (!file) {
            setError("Пожалуйста, выберите файл");
            return;
        }

        setLoading(true);
        setError(null);
        setDocumentUrl(null);
        setWarnings([]);

        try {
            const formData = new FormData();
            formData.append('file', file);
            
            // Add metadata fields to the form data - use placeholders if empty
            formData.append('title', title || "Заголовок работы");
            formData.append('author', author || "ФИО автора");
            formData.append('institution', institution || "Название учебного заведения");
            formData.append('city', city || "Город");
            formData.append('year', year || "2023");
            
            // Set parameters for ML and LLM usage
            formData.append('use_ml', 'true'); // Always use ML for section detection
            formData.append('use_llm', String(useLLM)); // Control smart placeholder generation based on toggle

            const response = await fetch(`${API_BASE_URL}/api/format`, {
                method: 'POST',
                body: formData,
                mode: 'cors',
                credentials: 'same-origin',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка при форматировании документа');
            }

            // Helper function to decode base64
            const decodeBase64 = (str: string): string => {
                try {
                    // Decode from base64 and then from UTF-8
                    return decodeURIComponent(atob(str).split('').map(function(c) {
                        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                    }).join(''));
                } catch (e) {
                    console.error('Failed to decode base64 string:', e);
                    return str;
                }
            };

            // Create an array to collect all warnings
            let allWarnings: string[] = [];
            
            // Get missing sections if available - for base64 encoded headers
            const missingSectionsBase64 = response.headers.get('X-Missing-Sections-Base64');
            if (missingSectionsBase64) {
                try {
                    const decodedSections = decodeBase64(missingSectionsBase64);
                    const missingSections = JSON.parse(decodedSections);
                    if (Array.isArray(missingSections) && missingSections.length > 0) {
                        // Add specific warning for each missing section
                        const sectionWarnings = missingSections.map(section => 
                            `В документе отсутствует раздел "${section}". Добавлен шаблон.`
                        );
                        allWarnings = [...allWarnings, ...sectionWarnings];
                    }
                } catch (e) {
                    console.error('Failed to parse missing sections:', e);
                    
                    // Fallback to ASCII transliterated headers if base64 decoding fails
                    const asciiSections = response.headers.get('X-Missing-Sections-ASCII');
                    if (asciiSections) {
                        try {
                            const missingSections = JSON.parse(asciiSections);
                            if (Array.isArray(missingSections) && missingSections.length > 0) {
                                // Use transliterated section names
                                const translationMap: Record<string, string> = {
                                    'introduction': 'введение',
                                    'conclusion': 'заключение',
                                    'references': 'список использованных источников'
                                };
                                
                                const sectionWarnings = missingSections.map(section => {
                                    const translatedSection = translationMap[section] || section;
                                    return `В документе отсутствует раздел "${translatedSection}". Добавлен шаблон.`;
                                });
                                
                                allWarnings = [...allWarnings, ...sectionWarnings];
                            }
                        } catch (e) {
                            console.error('Failed to parse ASCII sections:', e);
                        }
                    }
                }
            }
            
            // Get additional warnings if available
            const extraWarningsBase64 = response.headers.get('X-Extra-Warnings-Base64');
            if (extraWarningsBase64) {
                try {
                    const decodedWarnings = decodeBase64(extraWarningsBase64);
                    const extraWarnings = JSON.parse(decodedWarnings);
                    if (Array.isArray(extraWarnings) && extraWarnings.length > 0) {
                        allWarnings = [...allWarnings, ...extraWarnings];
                    }
                } catch (e) {
                    console.error('Failed to parse extra warnings:', e);
                }
            }
            
            // Set all warnings in state for display
            if (allWarnings.length > 0) {
                console.log('Setting warnings:', allWarnings);
                setWarnings(allWarnings);
            }

            // Get filename from Content-Disposition header if available
            const contentDisposition = response.headers.get('Content-Disposition');
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    setFileName(filenameMatch[1].replace(/['"]/g, ''));
                }
            }

            // Create blob URL
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            setDocumentUrl(url);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Произошла неизвестная ошибка');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = () => {
        if (documentUrl) {
            const a = document.createElement('a');
            a.href = documentUrl;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    };

    const toggleLLM = () => {
        setUseLLM(!useLLM);
    };

    return (
        <div className="min-h-screen bg-[#808AFC] flex items-center justify-center p-8">
            <div className="bg-white rounded-2xl p-10 max-w-4xl w-full">
                <div className="flex items-center space-x-8">
                    <div className="flex-1">
                        <h1 className="text-5xl font-bold text-black">МЫ</h1>
                        <h2 className="text-4xl font-bold text-black">СДЕЛАЕМ ТВОЙ ОТЧЕТ</h2>
                        <p className="text-gray-600 text-sm mt-2">ГОСТ 7.32-2017</p>
                        
                        <p className="text-gray-700 mt-4">
                            Не трать время на оформление — доверь это нам!<br />
                            Быстрое и качественное оформление документов.
                        </p>
                        
                        {/* API Status Indicator */}
                        <div className="mt-2 flex items-center">
                            <span className="text-sm mr-2">API статус:</span>
                            <span className={`inline-block w-3 h-3 rounded-full mr-1 ${
                                apiStatus === 'online' 
                                    ? 'bg-green-500' 
                                    : apiStatus === 'offline' 
                                        ? 'bg-red-500' 
                                        : 'bg-yellow-500'
                            }`}></span>
                            <span className="text-sm">
                                {apiStatus === 'online' 
                                    ? 'онлайн' 
                                    : apiStatus === 'offline' 
                                        ? 'оффлайн' 
                                        : 'проверка...'}
                            </span>
                        </div>
                    </div>

                    <div className="w-100 h-100 flex-shrink-0">
                        <Image src="/images/report.png" alt="Cloud Report" width={500} height={500} />
                    </div>
                </div>

                <div className="mt-8">
                    {/* Smart Generation Toggle */}
                    <div className="mb-6">
                        <button 
                            onClick={toggleLLM}
                            className={`flex items-center px-4 py-2 rounded-full text-sm font-medium ${
                                useLLM 
                                ? 'bg-purple-600 text-white hover:bg-purple-700' 
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                        >
                            <Sparkles className={`w-4 h-4 mr-2 ${useLLM ? 'text-yellow-300' : 'text-gray-500'}`} />
                            {useLLM ? 'Умное заполнение: Вкл' : 'Умное заполнение: Выкл'}
                        </button>
                        <p className="text-xs text-gray-500 mt-1">
                            {useLLM 
                             ? 'ИИ будет использован для создания контекстных заполнителей для отсутствующих разделов.' 
                             : 'Будут использоваться стандартные заполнители для отсутствующих разделов.'}
                        </p>
                    </div>

                    {/* Metadata Section - Moved above file upload */}
                    <div className="mb-6">
                        <h3 className="text-sm font-semibold text-gray-800 mb-4">МЕТАДАННЫЕ ДОКУМЕНТА</h3>
                        
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="text-sm text-gray-700 mb-1 block">Заголовок:</label>
                                <input 
                                    type="text" 
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="Заголовок работы"
                                    className="w-full p-2 border border-gray-300 rounded-md"
                                />
                            </div>
                            <div>
                                <label className="text-sm text-gray-700 mb-1 block">Автор:</label>
                                <input 
                                    type="text" 
                                    value={author}
                                    onChange={(e) => setAuthor(e.target.value)}
                                    placeholder="ФИО автора"
                                    className="w-full p-2 border border-gray-300 rounded-md"
                                />
                            </div>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="text-sm text-gray-700 mb-1 block">Учебное заведение:</label>
                                <input 
                                    type="text" 
                                    value={institution}
                                    onChange={(e) => setInstitution(e.target.value)}
                                    placeholder="Название учебного заведения"
                                    className="w-full p-2 border border-gray-300 rounded-md"
                                />
                            </div>
                            <div>
                                <label className="text-sm text-gray-700 mb-1 block">Город:</label>
                                <input 
                                    type="text" 
                                    value={city}
                                    onChange={(e) => setCity(e.target.value)}
                                    placeholder="Город"
                                    className="w-full p-2 border border-gray-300 rounded-md"
                                />
                            </div>
                        </div>
                        
                        <div className="mb-4">
                            <label className="text-sm text-gray-700 mb-1 block">Год:</label>
                            <input 
                                type="text" 
                                value={year}
                                onChange={(e) => setYear(e.target.value)}
                                placeholder="2023"
                                className="w-full p-2 border border-gray-300 rounded-md"
                            />
                        </div>
                    </div>

                    <label className="text-sm font-semibold text-gray-800">ФАЙЛ ДЛЯ ОФОРМЛЕНИЯ:</label>
                    <div className="flex items-center mt-2 space-x-2 bg-[#DBDEFF] rounded-[30px] p-2">
                        <div className="flex-grow overflow-hidden px-3">
                            <p className="text-sm text-gray-600 truncate">
                                {file ? file.name : 'Выберите файл...'}
                            </p>
                        </div>
                        <input 
                            type="file" 
                            onChange={(e) => {
                                if (e.target.files && e.target.files.length > 0) {
                                    setFile(e.target.files[0]);
                                }
                            }} 
                            className="hidden" 
                            id="file-upload"
                            accept=".txt"
                        />
                        <label htmlFor="file-upload" className="cursor-pointer flex items-end px-4 py-2 text-white text-sm hover:bg-purple-300 rounded-[30px] bg-[#808AFC]">
                            <Upload className="w-5 h-5 mr-2" />
                            ЗАГРУЗИТЬ ФАЙЛ
                        </label>
                        <Button 
                            className="rounded-[30px] bg-[#808AFC] text-white hover:bg-purple-600"
                            onClick={handleSubmit}
                            disabled={loading || !file || apiStatus !== 'online'}
                        >
                            {loading ? 'ОБРАБОТКА...' : 'КОНВЕРТИРОВАТЬ'}
                        </Button>
                    </div>
                    
                    {error && (
                        <p className="text-sm text-red-500 mt-2">
                            {error}
                        </p>
                    )}

                    {warnings.length > 0 && (
                        <div className="mt-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded-md">
                            <div className="flex">
                                <div className="flex-shrink-0">
                                    <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div className="ml-3">
                                    <h4 className="text-yellow-700 font-medium text-sm">Предупреждения:</h4>
                                    <ul className="list-disc pl-5 mt-1">
                                        {warnings.map((warning, index) => (
                                            <li key={index} className="text-yellow-600 text-sm">{warning}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}

                    <label className="text-sm font-semibold text-gray-800 mt-4">НОВЫЙ ГОСТ ФАЙЛ:</label>
                    <div className="flex items-center mt-2 bg-[#DBDEFF] rounded-[30px] p-2">
                        <div className="ml-3 text-sm text-gray-700">
                            {documentUrl && <span>{fileName}</span>}
                        </div>
                        <Button 
                            className="text-white ml-auto text-sm hover:bg-purple-300 rounded-[30px] bg-[#808AFC] flex items-center"
                            onClick={handleDownload}
                            disabled={!documentUrl}
                        >
                            <CloudDownload className="w-5 h-5 mr-2" />
                            СКАЧАТЬ
                        </Button>
                    </div>
                    <p className="text-xs text-gray-500 mt-4 text-center">*ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ</p>
                </div>
            </div>
        </div>
    );
} 