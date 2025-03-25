import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function Home() {
    return (
        <div className="min-h-screen bg-black flex flex-col">
            {/* Кнопка входа в правом верхнем углу */}
            <div className="self-end p-4">
                <Link href="/login">
                    <Button
                        variant="ghost"
                        className="text-white hover:text-white hover:bg-transparent"
                    >
                        Войти
                    </Button>
                </Link>
            </div>

            {/* Основное содержимое по центру */}
            <div className="flex-grow flex flex-col items-center justify-center p-4 space-y-4">
                <h1 className="text-6xl font-bold text-white">Mbl</h1>
                <p className="text-2xl text-white">СДЕЛАЕМ ТВОЙ ОТЧЕТ</p>
            </div>
        </div>
    )
}
