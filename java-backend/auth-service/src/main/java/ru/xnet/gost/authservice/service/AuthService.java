package ru.xnet.gost.authservice.service;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import ru.xnet.gost.authservice.exception.AuthException;
import ru.xnet.gost.authservice.model.User;
import ru.xnet.gost.authservice.repository.UserRepository;

@Service
@RequiredArgsConstructor
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final EmailValidator emailValidator;
    private final JwtService jwtService;
    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    public void registerUser(String username, String password, String email) {
        if (userRepository.existsByUsername(username)) {
            throw new AuthException("Username already exists");
        }

        if (userRepository.existsByEmail(email)) {  
            throw new AuthException("Email already exists");
        }

        if (!emailValidator.validate(email)) {
            throw new AuthException("Invalid email");
        }

        User user = new User();
        user.setUsername(username);
        user.setPassword(passwordEncoder.encode(password));
        user.setEmail(email);

        userRepository.save(user);
    }

    public String loginUser(String username, String password) {
        User user = userRepository.findByUsername(username)
                                  .orElseThrow(() -> new AuthException("User not found"));

        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new AuthException("Invalid password");
        }

        return jwtService.generateToken(user);
    }

    public boolean hasAccess(User user, String requiredRole) {
        return user != null &&
                user.getRole().toString().equals(requiredRole);
    }
    private final Set<String> invalidatedTokens = Collections.synchronizedSet(new HashSet<>());
    public void logout(String token) {
        try {
            if (jwtService.isTokenExpired(token)) {
                log.warn("Attempt to logout with expired token");
                throw new AuthException("The token is already invalid");
            }

            String username = jwtService.extractUsername(token);
            invalidatedTokens.add(token);
            log.info("User {} logged out", username);

        } catch (AuthException e) {
            log.error("Logout failed: {}", e.getMessage());
            throw new AuthException("Error in logout");
        }
    }

    public boolean isTokenExpired(String token) {
        try {
            return jwtService.isTokenExpired(token) || invalidatedTokens.contains(token);
        } catch (AuthException e) {
            log.warn("Token validation failed: {}", e.getMessage());
            return true; 
        }
    }
}




