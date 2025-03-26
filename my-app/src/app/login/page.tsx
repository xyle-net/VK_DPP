"use client" 

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import Link from "next/link"
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import Image from "next/image"

const formSchema = z.object({
    email: z.string().email("Некорректный email"),
    password: z.string().min(6, "Пароль должен содержать минимум 6 символов"),
})

export default function LoginPage() {
    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    })

    const onSubmit = (values: z.infer<typeof formSchema>) => {
        console.log(values)
    }

    return (
        <div className="min-h-screen bg-[#808AFC] flex items-center justify-center p-8">
            <div className="bg-white rounded-[30px] shadow-lg p-10 max-w-3xl w-full flex items-center space-x-8">
                <div className="flex-1 bg-[#808AFC] p-8 rounded-[30px]">
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl text-white font-bold text-white">Авторизация</CardTitle>
                    </CardHeader>

                    <CardContent className="space-y-4">

                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="email"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-white">E-mail</FormLabel>
                                            <FormControl>
                                                <Input placeholder="turkish.sweetshop@gmail.com" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-white">Пароль</FormLabel>
                                            <FormControl>
                                                <Input type="password" placeholder="***********" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="flex justify-end">
                                    <Button variant="link" className="text-sm text-gray-200 hover:text-black">
                                        Забыли пароль?
                                    </Button>
                                </div>

                                <div className="flex justify-center">
                                    <Button
                                        type="submit"
                                        className="flex items-center justify-center w-1/3 bg-white hover:bg-gray-800 text-black rounded-[30px]"
                                    >
                                        ВОЙТИ
                                    </Button>
                                </div>
                            </form>
                        </Form>

                        <div className="relative my-4">
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="px-2 text-muted-foreground text-white">
                                    ИЛИ
                                </span>
                            </div>
                        </div>

                        <div className="text-center text-sm mt-4 text-white">
                            Нет аккаунта?{' '}
                            <Link href="/register" className="font-medium text-white hover:underline">
                                Зарегистрируйтесь
                            </Link>
                        </div>
                    </CardContent>
                </div>

                <div className="w-[300px] flex-shrink-0">
                    <Image src="/images/report.png" alt="Cloud Report" width={500} height={500} />
                </div>
            </div>
        </div>
    )
}
