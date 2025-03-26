package ru.xnet.gost.docservice.repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import ru.xnet.gost.docservice.model.Document;
import ru.xnet.gost.docservice.model.DocumentStatus;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Long> {

    List<Document> findByUserId(String userId);
    List<Document> findByUserIdAndStatus(
         String userId,
         DocumentStatus status);
    List<Document> findByUploadedAtBetween(
        LocalDateTime start,
        LocalDateTime end
    );
    boolean existsByIdAndUserId(Long id, String userId);
    Optional<Document> findByIdAndUserId(Long id, String userId);
}