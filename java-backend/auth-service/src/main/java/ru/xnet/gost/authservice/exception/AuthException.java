package ru.xnet.gost.authservice.exception;

public class AuthException extends RuntimeException {
    public AuthException(String message) {
        super(message);
    }
}