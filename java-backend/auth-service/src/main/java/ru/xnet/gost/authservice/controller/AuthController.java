package ru.xnet.gost.authservice.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import ru.xnet.gost.authservice.dto.LoginRequest;
import ru.xnet.gost.authservice.dto.RegisterRequest;
import ru.xnet.gost.authservice.exception.AuthException;
import ru.xnet.gost.authservice.service.AuthService;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/auth")
public class AuthController {
    private final AuthService authService;
    private static final Logger log = LoggerFactory.getLogger(AuthController.class);

    @PostMapping("/register")
    public String register(@RequestBody RegisterRequest request) {
        try {
            authService.registerUser(
                    request.getUsername(),
                    request.getPassword(),
                    request.getEmail()
            );
            String token = authService.loginUser(
                    request.getUsername(),
                    request.getPassword()
            );
            log.info("User successfully registered: {}", request.getUsername());
            return token;
        } catch (AuthException e) {
            log.warn("Registration failed for user {}: {}", request.getUsername(), e.getMessage());
            return "Error during registration: " + e.getMessage();
        }
    }

    @PostMapping("/login")
    public String login(@RequestBody LoginRequest request) {
        try {
            String token = authService.loginUser(
                    request.getUsername(),
                    request.getPassword()
            );
            log.info("User successfully logged in: {}", request.getUsername());
            return token;
        } catch (AuthException e) {
            log.warn("Login failed for user {}: {}", request.getUsername(), e.getMessage());
            return "Login error: " + e.getMessage();
        }
    }

    @PostMapping("/logout")
    public String logout(@RequestHeader("Authorization") String authHeader) {
        try {
            
            if (!authHeader.startsWith("Bearer ")) {
                throw new AuthException("Invalid token format");
            }
            String token = authHeader.substring(7); 
            authService.logout(token);
            log.info("User successfully logged out");
            return "Logged out successfully";
        } catch (AuthException e) {
            log.warn("Logout failed: {}", e.getMessage());
            return "Logout error: " + e.getMessage();
        }
    }
}