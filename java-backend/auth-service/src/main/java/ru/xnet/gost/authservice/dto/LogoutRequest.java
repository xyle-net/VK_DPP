package ru.xnet.gost.authservice.dto;

import lombok.Data;

@Data
public class LogoutRequest {
    private String token;
}
