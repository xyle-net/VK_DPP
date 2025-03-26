package ru.xnet.gost.docservice.config;

import io.minio.MinioClient;
import lombok.Data;
import okhttp3.OkHttpClient;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Configuration
@ConfigurationProperties(prefix = "minio")
@Data
public class MinioConfig {
    private String url;
    private String accessKey;
    private String secretKey;
    private String bucketRaw;
    private String bucketFormatted;

    @Bean
    public MinioClient minioClient() {
        OkHttpClient httpClient = new OkHttpClient.Builder()
                .connectTimeout(Duration.ofSeconds(10)).build();
        return MinioClient.builder()
                .endpoint(url)
                .credentials(accessKey, secretKey)
                .httpClient(httpClient)
                .build();
    }
}
