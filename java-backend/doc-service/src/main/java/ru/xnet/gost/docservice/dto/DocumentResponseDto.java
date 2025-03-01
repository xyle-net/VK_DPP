package ru.xnet.gost.docservice.dto;

import lombok.Data;
import ru.xnet.gost.docservice.model.DocumentStatus;

@Data
public class DocumentResponseDto {
    private long id;
    private String fileName;
    private DocumentStatus status;
}