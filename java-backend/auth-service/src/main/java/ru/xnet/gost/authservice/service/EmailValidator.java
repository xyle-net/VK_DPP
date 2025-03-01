package ru.xnet.gost.authservice.service;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.stereotype.Component;

@Component
public class EmailValidator {
    private static final String EMAIL_PATTERN = "^[A-Za-z0-9+_.-]+@(.+)$";
    private static final Pattern PATTERN = Pattern.compile(EMAIL_PATTERN);

    public boolean validate(String email) {
        Matcher matcher = PATTERN.matcher(email);
        return matcher.matches();
    }
}
