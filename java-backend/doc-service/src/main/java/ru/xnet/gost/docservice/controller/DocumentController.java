package ru.xnet.gost.docservice.controller;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import ru.xnet.gost.docservice.dto.DocumentResponseDto;
import ru.xnet.gost.docservice.service.DocumentService2;

// Базовый абстрактный класс
abstract class BaseDocumentController {
    protected static final Logger log = LoggerFactory.getLogger(DocumentController.class);
    
    protected <T> T executeDocOperation(
            HttpServletRequest request,
            String operationName,
            DocOperation<T> operation
    ) {
        String userId = (String) request.getAttribute("userId");
        log.info("Starting {} for user {}", operationName, userId);
        
        try {
            T result = operation.execute(userId);
            log.info("Completed {} for user {}", operationName, userId);
            return result;
        } catch (Exception e) {
            log.error("Error in {}: {}", operationName, e.getMessage());
            throw new RuntimeException("Error processing " + operationName, e);
        }
    }
    
    @FunctionalInterface
    protected interface DocOperation<T> {
        T execute(String userId) throws Exception;
    }
}

// Основной контроллер
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/doc")
public class DocumentController extends BaseDocumentController {
    private final DocumentService2 documentService2;


    // загрузка новых док-тов
    @PostMapping("/upload")
    public List<String> uploadDocuments(
            @RequestParam("files") List<MultipartFile> files,
            HttpServletRequest request
    ) {
        return executeDocOperation(
            request,
            "upload documents",
            userId -> documentService2.uploadDocuments(files, userId).join()
        );
    }

    // получение списка док-тов юзера
    @GetMapping("/my")
    public List<DocumentResponseDto> getMyDocuments(
            HttpServletRequest request
    ) {
        return executeDocOperation(
            request,
            "fetch documents",
            userId -> documentService2.getUserDocuments(userId).join()
        );
    }

    // скачивание док-та
@GetMapping("/download/{docId}")
public ResponseEntity<Resource> downloadDocument(
        @PathVariable String docId,
        HttpServletRequest request
) {
    Resource resource = executeDocOperation(
        request,
        "download document " + docId,
        userId -> documentService2.downloadDocument(docId, userId).join()
    );
    
    return ResponseEntity.ok()
        .header(HttpHeaders.CONTENT_DISPOSITION, 
                "attachment; filename=\"" + resource.getFilename() + "\"")
        .contentType(MediaType.parseMediaType(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
        .body(resource);
}

    // Просмотр информации о док-те
    @GetMapping("/status/{docId}")
    public DocumentResponseDto getStatus(
        @PathVariable String docId,
        HttpServletRequest request
    ) {
        return executeDocOperation(
            request,
            "status document" +  docId,
            userId -> documentService2.getDocumentStatus(docId, userId).join()
            );
    }
}