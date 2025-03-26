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

// Схема валидации
const formSchema = z.object({
    name: z.string().min(2, { message: "Никнейм должно содержать минимум 2 символа" }),
    email: z.string().email("Некорректный email"),
    password: z.string().min(6, "Пароль должен содержать минимум 6 символов"),
    confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
})

export default function RegisterPage() {
    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            email: "",
            password: "",
            confirmPassword: "",
        },
    })

    const onSubmit = (values: z.infer<typeof formSchema>) => {
        console.log("Данные формы:", values)
    }

    return (
        <div className="min-h-screen bg-[#808AFC] flex items-center justify-center p-8">
            <div className="bg-white rounded-[30px] shadow-lg p-10 max-w-4xl w-full flex items-center space-x-8">
                <div className="flex-1 bg-[#808AFC] p-8 rounded-[30px]">
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl text-white font-bold">Регистрация</CardTitle>
                    </CardHeader>

                    <CardContent className="space-y-4">
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                
                                <FormField
                                    control={form.control}
                                    name="name"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-white">Никнейм</FormLabel>
                                            <FormControl>
                                                <Input
                                                    placeholder="sofia2023"
                                                    {...field}
                                                    className={form.formState.errors.name && "border-red-500"}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="email"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-white">E-mail</FormLabel>
                                            <FormControl>
                                                <Input
                                                    placeholder="turkish.sweetshop@gmail.com"
                                                    {...field}
                                                    className={form.formState.errors.email && "border-red-500"}
                                                />
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
                                                <Input
                                                    type="password"
                                                    placeholder="***********"
                                                    {...field}
                                                    className={form.formState.errors.password && "border-red-500"}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="confirmPassword"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-white">Подтвердите пароль</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="password"
                                                    placeholder="***********"
                                                    {...field}
                                                    className={form.formState.errors.confirmPassword && "border-red-500"}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="flex justify-center">
                                    <Button
                                        type="submit"
                                        className="flex items-center justify-center w-2/3 bg-white hover:bg-gray-800 text-black rounded-[30px]"
                                    >
                                        РЕГИСТРАЦИЯ
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
                            Уже есть аккаунт?{' '}
                            <Link href="/login" className="font-medium text-white hover:underline">
                                Войдите
                            </Link>
                        </div>
                    </CardContent>
                </div>

                <div className="w-[350px] flex-shrink-0">
                    <Image src="/images/report.png" alt="Cloud Report" width={500} height={500} />
                </div>
            </div>
        </div>
    )
}
