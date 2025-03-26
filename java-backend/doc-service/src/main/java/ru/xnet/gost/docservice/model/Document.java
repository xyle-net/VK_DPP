package ru.xnet.gost.docservice.model;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "documents")
@Data
public class Document {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private long id;
    private String userId;
    private String fileName;
    @Enumerated(EnumType.STRING)
    private DocumentStatus status;
    @CreationTimestamp
    private LocalDateTime uploadedAt;
    private LocalDateTime endAt;
}
