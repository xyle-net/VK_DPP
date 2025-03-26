package ru.xnet.gost.docservice.service;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import ru.xnet.gost.docservice.model.Document;
import ru.xnet.gost.docservice.model.DocumentStatus;
import ru.xnet.gost.docservice.repository.DocumentRepository;

@Slf4j
@Service
@RequiredArgsConstructor
public class KafkaService {
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final DocumentRepository documentRepository;


    private static final String DOC_UPLOADED_TOPIC = "doc-uploaded";
    private static final String DOC_PROCESSING_TOPIC = "doc-processing";
    private static final String DOC_PROCESSED_TOPIC = "doc-processed";

    //документ загружен
    public void notifyDocumentUploaded(String docId, String userId, String filePath) {
        String message = String.format("%s:%s:%s", docId, userId, filePath);
        log.info("Отправляем уведомление о загрузке документа: {}", message);
        kafkaTemplate.send(DOC_UPLOADED_TOPIC, message);
    }

    // начало обработки
    @KafkaListener(topics = DOC_PROCESSING_TOPIC)
    public void handleProcessingDocument(String message) {

        log.info("Получено сообщение о начале обработки документа: {}", message);
        String docId = message.trim();
        Document doc = documentRepository.findById(Long.valueOf(docId))
            .orElse(null);

            
        if (doc != null) {
            doc.setStatus(DocumentStatus.PROCESSING);
            documentRepository.save(doc);
            log.info("Обновлен статус документа {} на PROCESSING", docId);
        }
    }

    // завершение обработки
    @KafkaListener(topics = DOC_PROCESSED_TOPIC)
    public void handleProcessedDocument(String message) {
        log.info("Получено сообщение об обработанном документе: {}", message);
        
        String[] parts = message.split(":");
        if (parts.length >= 2) {
            String docId = parts[0];
            String status = parts[1];
            
            Document doc = documentRepository.findById(Long.valueOf(docId))
                .orElse(null);
                
            if (doc != null) {
                doc.setStatus("SUCCESS".equals(status) ? 
                    DocumentStatus.COMPLETED : DocumentStatus.ERROR);
                documentRepository.save(doc);
                log.info("Обновлен статус документа {}: {}", docId, status);
            }
        }
    }
}