'use client';

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { Upload, CloudDownload } from "lucide-react";
import Image from "next/image";

export default function Home() {
    const [file, setFile] = useState(null);

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
                    </div>

                    <div className="w-100 h-100 flex-shrink-0">
                        <Image src="/images/report.png" alt="Cloud Report" width={500} height={500} />
                    </div>
                </div>

                <div className="mt-8">
                    <label className="text-sm font-semibold text-gray-800">ФАЙЛ ДЛЯ ОФОРМЛЕНИЯ:</label>
                    <div className="flex items-center mt-2 space-x-2 bg-[#DBDEFF] rounded-[30px] p-2">
                        <input 
                            type="file" 
                            onChange={(e) => setFile(e.target.files[0])} 
                            className="hidden" 
                            id="file-upload"
                        />
                        <label htmlFor="file-upload" className="cursor-pointer flex items-end ml-auto px-4 py-2 text-white text-sm hover:bg-purple-300 rounded-[30px] bg-[#808AFC]">
                            <Upload className="w-5 h-5 mr-2" />
                            ЗАГРУЗИТЬ ФАЙЛ
                        </label>
                        <Button className="rounded-[30px] bg-[#808AFC] text-white hover:bg-purple-600">КОНВЕРТИРОВАТЬ</Button>
                    </div>

                    <label className="text-sm font-semibold text-gray-800 mt-4">НОВЫЙ ГОСТ ФАЙЛ:</label>
                    <div className="flex items-center mt-2 bg-[#DBDEFF] rounded-[30px] p-2">
                        <Button className="text-white ml-auto text-sm hover:bg-purple-300 rounded-[30px] bg-[#808AFC] flex items-center">
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
