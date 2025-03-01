package ru.xnet.gost.docservice.service;

import java.io.File;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import ru.xnet.gost.docservice.dto.DocumentResponseDto;
import ru.xnet.gost.docservice.exception.DocumentNotFoundException;
import ru.xnet.gost.docservice.exception.DocumentProcessingException;
import ru.xnet.gost.docservice.model.Document;
import ru.xnet.gost.docservice.model.DocumentStatus;
import ru.xnet.gost.docservice.repository.DocumentRepository;

@Service
@RequiredArgsConstructor
@Slf4j
@EnableAsync
public class DocumentService {
    private final DocumentRepository documentRepository;
    private LocalDateTime firstUploadTime;
    private static final String ML_PARSER_PATH = "C:/Users/ITdiakon/dev/Java4ka/GOST/python-backend/ml-service/parser/";
    private static final String ML_RESULT_PATH = "C:/Users/ITdiakon/dev/Java4ka/GOST/python-backend/ml-service/result/";

    @Async
public CompletableFuture<List<String>> uploadDocuments(List<MultipartFile> files, String userId) {
    log.info("Starting parallel upload of {} files for user {}", files.size(), userId);
    
    List<CompletableFuture<String>> futures = files.stream()
            .map(file -> CompletableFuture.supplyAsync(() -> {
                try {
                    Long docId = uploadDocument(file, userId);
                    log.info("Completed upload of file {} for user {}, got docId: {}", 
                            file.getOriginalFilename(), userId, docId);
                    return docId.toString();
                } catch (IOException e) {
                    log.error("Error uploading file {}: {}", file.getOriginalFilename(), e.getMessage());
                    return "Error: " + e.getMessage();
                }
            }))
            .collect(Collectors.toList());

    CompletableFuture<Void> allFutures = CompletableFuture.allOf(
            futures.toArray(CompletableFuture[]::new)  
    );

    return allFutures.thenApply(v -> futures.stream()
            .map(CompletableFuture::join)
            .collect(Collectors.toList()));
}
    

    
    private Long uploadDocument(MultipartFile file, String userId) throws IOException {
        if (firstUploadTime == null) {
            firstUploadTime = LocalDateTime.now();
        }

        
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String fileName = userId + "_" + timestamp + "_" + file.getOriginalFilename();
        String filePath = ML_PARSER_PATH + fileName;

      
        File dest = new File(filePath);
        file.transferTo(dest);

        Document document = new Document();
        document.setUserId(userId);
        document.setFileName(file.getOriginalFilename());
        document.setFilePath(filePath);
        document.setStatus(DocumentStatus.UPLOADED);

        document = documentRepository.save(document);
        log.info("Document uploaded: {} for user: {} at path: {}", document.getId(), userId, filePath);

        return document.getId();
    }


    @Async
    public CompletableFuture<DocumentResponseDto> getDocumentStatus(String docId, String userId) {
        Document document = documentRepository.findByIdAndUserId(Long.parseLong(docId), userId)
                .orElseThrow(() -> new DocumentNotFoundException(Long.parseLong(docId)));
        return CompletableFuture.completedFuture(convertToDto(document));
    }

   
    @Async
    public CompletableFuture<List<DocumentResponseDto>> getUserDocuments(String userId) {
        List<DocumentResponseDto> results = documentRepository.findByUserId(userId).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
        return CompletableFuture.completedFuture(results);
    }

    
    @Async
    public CompletableFuture<Resource> downloadDocument(String docId, String userId) {
        Document document = documentRepository.findByIdAndUserId(Long.valueOf(docId), userId)
                .orElseThrow(() -> new DocumentNotFoundException(Long.valueOf(docId)));
        
        try {
            File resultFile = new File(ML_RESULT_PATH + "ml_is_on_vacation.docx");
            if (!resultFile.exists()) {
                document.setStatus(DocumentStatus.ERROR);
                documentRepository.save(document);
                throw new DocumentProcessingException("ML ушел в себя и не вернулся");
            }
            
         
            document.setStatus(DocumentStatus.COMPLETED);
            document.setEndAt(LocalDateTime.now());
            documentRepository.save(document);
            
            return CompletableFuture.completedFuture(new FileSystemResource(resultFile));
        } catch (DocumentProcessingException e) {
            document.setStatus(DocumentStatus.ERROR);
            document.setEndAt(LocalDateTime.now());
            documentRepository.save(document);
            
            log.error("Error downloading document: {}", e.getMessage());
            throw new DocumentProcessingException("ML-сервис медитирует, попробуйте позже", e);
        }
    }


    @Async
    public CompletableFuture<DocumentResponseDto> getDocumentPreview(String docId, String userId) {
        return getDocumentStatus(docId, userId);
    }

    
    private DocumentResponseDto convertToDto(Document document) {
        DocumentResponseDto dto = new DocumentResponseDto();
        dto.setId(document.getId());
        dto.setFileName(document.getFileName());
        dto.setStatus(document.getStatus());
        return dto;
    }

    
    @Scheduled(fixedRate = 3600000) 
    public void cleanup() {
        if (firstUploadTime != null &&
                LocalDateTime.now().minusHours(1).isAfter(firstUploadTime)) {

            documentRepository.deleteAll();
            firstUploadTime = null;

            log.info("Cleanup completed. Ready for new documents!");
        }
    }
}