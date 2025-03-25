import { redirect } from 'next/navigation'

export default function Home() {
    redirect('/register') // Автоматический переход на регистрацию
}