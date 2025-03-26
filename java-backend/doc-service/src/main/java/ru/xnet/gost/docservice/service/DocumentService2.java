package ru.xnet.gost.docservice.service;

import java.io.IOException;
import java.io.InputStream;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.CompletableFuture;

import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import io.minio.GetObjectArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.errors.ErrorResponseException;
import io.minio.errors.InsufficientDataException;
import io.minio.errors.InternalException;
import io.minio.errors.InvalidResponseException;
import io.minio.errors.ServerException;
import io.minio.errors.XmlParserException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import ru.xnet.gost.docservice.dto.DocumentResponseDto;
import ru.xnet.gost.docservice.exception.DocumentNotFoundException;
import ru.xnet.gost.docservice.exception.DocumentProcessingException;
import ru.xnet.gost.docservice.model.Document;
import ru.xnet.gost.docservice.model.DocumentStatus;
import ru.xnet.gost.docservice.repository.DocumentRepository;

@Slf4j
@Service
@EnableAsync
@RequiredArgsConstructor
public class DocumentService2 {
    private final DocumentRepository documentRepository;
    private final MinioClient minioClient;
    private final KafkaService kafkaService;

    // Загрузка нескольких документов
    @Async
    public CompletableFuture<List<String>> uploadDocuments(List<MultipartFile> files, String userId){

        log.info("Starting parallel upload of {} files for user {}",
                files.size(), userId);

        List<CompletableFuture<String>> filesOfUser = files.stream()
                .map(file -> CompletableFuture.supplyAsync(() -> {
                    try {
                        String docId = uploadOneDocument(file, userId);
                        log.info("Uploading file {} for fileName {} for user {}",
                                docId, file.getOriginalFilename(), userId);
                        return docId;

                    } catch (Exception e) {
                        log.error("Error uploading file {}: {}",
                                file.getOriginalFilename(),
                                e.getMessage());
                        return "Error: " + e.getMessage();
                    }
                }))
                .toList();

       CompletableFuture<Void> filesDone = CompletableFuture.allOf(
               filesOfUser.toArray(CompletableFuture[]::new)
       );

       return filesDone.thenApply(v -> filesOfUser.stream()
                                                  .map(CompletableFuture::join)
                                                  .toList());
    }

    private String uploadOneDocument(MultipartFile file, String userId) {
        try {

            String fileName = userId + "_" +
                    file.getOriginalFilename();

            // Сохранить в базу
            Document document = new Document();
            document.setUserId(userId);
            document.setFileName(file.getOriginalFilename());
            document.setStatus(DocumentStatus.UPLOADED);
            document.setUploadedAt(LocalDateTime.now());

            documentRepository.save(document);
            String docId = String.valueOf(document.getId());

            // Сохранить файл 
            String objectPath = userId + "/" + fileName;
            minioClient.putObject(
                    PutObjectArgs.builder()
                            .bucket("raw-documents")
                            .object(objectPath)
                            .stream(file.getInputStream(), file.getSize(), -1)
                            .build()
            );

            // Отправить в Kafka
            kafkaService.notifyDocumentUploaded(docId, userId, objectPath);

            // Вернуть ID
            log.info("Document uploaded: {} for user: {} at path: {}",
                docId, userId, userId + "/" + fileName);
            return docId;

        } catch (IOException | ErrorResponseException | InsufficientDataException | InternalException |
                 InvalidKeyException | InvalidResponseException | NoSuchAlgorithmException | ServerException |
                 XmlParserException e) {
            log.error("Error reading file: {}", e.getMessage());
            return "Error: " + e.getMessage();
        }
    }

    // доп информация о статусе
    @Async
    public CompletableFuture<DocumentResponseDto> getDocumentStatus(String docId, String userId) {
        Document document = documentRepository
                .findById(Long.parseLong(docId))
                .orElseThrow(() -> new DocumentNotFoundException(Long.valueOf(docId)));

        log.info("Getting information about the document {} status for the user {}",
                docId, userId);

        return CompletableFuture.completedFuture(convertToDto(document));
    }

    // конвертер для ответа
    public DocumentResponseDto convertToDto(Document document) {
        DocumentResponseDto statusDto = new DocumentResponseDto();
        statusDto.setId(document.getId());
        statusDto.setFileName(document.getFileName());
        statusDto.setStatus(document.getStatus());
        statusDto.setMessage(document.getStatus());
        return statusDto;
    }

    // Доп информация о документах пользователя
    @Async
    public CompletableFuture<List<DocumentResponseDto>> getUserDocuments(String userId) {
        List<DocumentResponseDto> documents = documentRepository
                .findByUserId(userId)
                .stream()
                .map(this::convertToDto)
                .toList();
        log.info("Getting information about the list documents for the user {}",
                userId);
        return CompletableFuture.completedFuture(documents);
    }

    @Async
    public CompletableFuture<Resource> downloadDocument(String docId, String userId) {
        try {
            //  Проверяем существование в БД
            Document document = documentRepository
                    .findByIdAndUserId(Long.valueOf(docId), userId)
                    .orElseThrow(() -> new DocumentNotFoundException(Long.valueOf(docId)));

            //  Формируем путь в s3
            String objectPath = userId + "/" + userId + "_" +
                document.getFileName();

            //  Скачиваем из MinIO
            InputStream stream = minioClient.getObject(
                    GetObjectArgs.builder()
                            .bucket("formatted-document")
                            .object(objectPath)
                            .build()
            );

            // Создаем Resource
            return CompletableFuture.completedFuture(new InputStreamResource(stream) {
            @Override
            public String getFilename() {
                return document.getFileName();
            }
        });

        } catch (DocumentNotFoundException e) {
            log.error("Document not found: {}", docId);
            throw new DocumentProcessingException("Document not found");
    
        } catch (IOException e) {
            log.error("Failed to read file for document {}: {}", docId, e.getMessage());
            throw new DocumentProcessingException("Failed to read file", e);
    
        } catch (Exception e) {
            log.error("Error downloading document {}: {}", docId, e.getMessage());
            throw new DocumentProcessingException("Failed to download document", e);
        }
    }
}