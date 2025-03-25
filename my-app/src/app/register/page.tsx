import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import Link from "next/link"

export default function RegisterPage() {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl font-bold">Mы</CardTitle>
                    <p className="text-sm text-gray-500">СДЕЛАЕМ ТВОЙ ОТЧЕТ</p>
                </CardHeader>

                <CardContent className="space-y-4">
                    <div className="flex justify-center space-x-4 mb-6">
                        <Link href="/login">
                            <Button variant="ghost" className="font-bold">LOG IN</Button>
                        </Link>
                        <Button variant="ghost" className="font-bold border-b-2 border-black">REGISTRATION</Button>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-center text-xl font-semibold">РЕГИСТРАЦИЯ</h2>

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Имя</Label>
                                <Input id="name" placeholder="Софья" />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="surname">Фамилия</Label>
                                <Input id="surname" placeholder="Константинова" />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="email">E-mail</Label>
                                <Input id="email" type="email" placeholder="turkish.sweetshop@gmail.com" />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="password">Пароль</Label>
                                <Input id="password" type="password" placeholder="***********" />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirm-password">Подтвердите пароль</Label>
                                <Input id="confirm-password" type="password" placeholder="***********" />
                            </div>
                        </div>
                    </div>
                </CardContent>

                <CardFooter className="flex flex-col space-y-4">
                    <Button className="w-full bg-black hover:bg-gray-800">
                        РЕГИСТРАЦИЯ
                    </Button>

                    <div className="relative my-4">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                ИЛИ
              </span>
                        </div>
                    </div>

                    <Button variant="outline" className="w-full">
                        <svg className="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/>
                        </svg>
                        Продолжить с Google
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}