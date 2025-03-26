package ru.xnet.gost.docservice.config;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class FilterConfig {

    // Создание специального Бина
    @Bean
    public FilterRegistrationBean<JwtAuthFilter> jwtFilter(
            JwtAuthFilter filter) 
    {
        FilterRegistrationBean<JwtAuthFilter> bean = new FilterRegistrationBean<>();
        bean.setFilter(filter);
        bean.addUrlPatterns("/api/*");
        return bean;
    }
}