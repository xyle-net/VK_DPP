package ru.xnet.gost.docservice.dto;

import lombok.Data;
import org.springframework.data.annotation.Transient;
import ru.xnet.gost.docservice.model.DocumentStatus;

@Data
public class DocumentResponseDto {
    private long id;
    private String fileName;
    private DocumentStatus status;
    @Transient
    private String message;

    public void setMessage(DocumentStatus status){
        this.status = status;
        this.message =  switch (status){
            case UPLOADED -> "Документ загружен";
            case PROCESSING -> "Обработка...";
            case COMPLETED -> "Готов";
            case ERROR -> "Ошибка";
        };
    }
}