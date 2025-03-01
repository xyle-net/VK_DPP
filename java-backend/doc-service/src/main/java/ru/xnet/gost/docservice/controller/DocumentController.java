package ru.xnet.gost.docservice.controller;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.Resource;
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
import ru.xnet.gost.docservice.service.DocumentService;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/doc")
public class DocumentController {
    private final DocumentService documentService;
    private static final Logger log = LoggerFactory.getLogger(DocumentController.class);

    @PostMapping("/upload")
    public List<String> uploadDocuments(
            @RequestParam("files") List<MultipartFile> files,
            HttpServletRequest request
    ) {
        try {
            String userId = (String) request.getAttribute("userId");
            log.info("Starting async upload of {} documents for user {}", files.size(), userId);
            return documentService.uploadDocuments(files, userId).join();
        } catch (Exception e) {
            log.error("Error uploading documents: {}", e.getMessage());
            return List.of("Error: " + e.getMessage());
        }
    }

    @GetMapping("/status/{docId}")
    public DocumentResponseDto getStatus(
            @PathVariable String docId,
            HttpServletRequest request
    ) {
        try {
            String userId = (String) request.getAttribute("userId");
            log.info("Checking status for document: {} by user: {}", docId, userId);
            return documentService.getDocumentStatus(docId, userId).join();
        } catch (Exception e) {
            log.error("Error checking status: {}", e.getMessage());
            throw e;
        }
    }

    @GetMapping("/my")
    public List<DocumentResponseDto> getMyDocuments(HttpServletRequest request) {
        try {
            String userId = (String) request.getAttribute("userId");
            log.info("Fetching documents for user: {}", userId);
            return documentService.getUserDocuments(userId).join();
        } catch (Exception e) {
            log.error("Error fetching documents: {}", e.getMessage());
            throw e;
        }
    }

    @GetMapping("/download/{docId}")
    public Resource downloadDocument(
            @PathVariable String docId,
            HttpServletRequest request
    ) {
        try {
            String userId = (String) request.getAttribute("userId");
            log.info("Downloading document: {} for user: {}", docId, userId);
            return documentService.downloadDocument(docId, userId).join();
        } catch (Exception e) {
            log.error("Error downloading document: {}", e.getMessage());
            throw e;
        }
    }

    @GetMapping("/preview/{docId}")
    public DocumentResponseDto previewDocument(
            @PathVariable String docId,
            HttpServletRequest request
    ) {
        try {
            String userId = (String) request.getAttribute("userId");
            log.info("Getting preview for document: {} for user: {}", docId, userId);
            return documentService.getDocumentPreview(docId, userId).join();
        } catch (Exception e) {
            log.error("Error getting preview: {}", e.getMessage());
            throw e;
        }
    }
}