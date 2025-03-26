import numpy as np
import re
import pickle
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, feature_dim, output_dim=3, dropout=0.2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, bidirectional=True, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(hidden_dim * 2, 32)  # * 2 for bidirectional
        self.fc2 = nn.Linear(32 + feature_dim, output_dim)
        self.relu = nn.ReLU()
        
    def forward(self, text, features):
        # text shape: [batch_size, seq_len]
        embedded = self.embedding(text)
        # embedded shape: [batch_size, seq_len, embedding_dim]
        
        lstm_out, (hidden, cell) = self.lstm(embedded)
        # lstm_out shape: [batch_size, seq_len, hidden_dim * 2]
        
        # Concatenate the final hidden states from both directions
        hidden = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim=1)
        # hidden shape: [batch_size, hidden_dim * 2]
        
        fc1_out = self.dropout(self.relu(self.fc1(hidden)))
        # fc1_out shape: [batch_size, 32]
        
        # Concatenate with additional features
        concat = torch.cat((fc1_out, features), dim=1)
        # concat shape: [batch_size, 32 + feature_dim]
        
        output = self.fc2(concat)
        # output shape: [batch_size, output_dim]
        
        return output

class TextTokenizer:
    def __init__(self, num_words=5000):
        self.num_words = num_words
        self.word_index = {}
        self.index_word = {}
        self.word_counts = {}
        self.fitted = False
    
    def fit_on_texts(self, texts):
        """Create vocabulary index based on word frequency."""
        # Count word occurrences
        for text in texts:
            for word in text.lower().split():
                if word in self.word_counts:
                    self.word_counts[word] += 1
                else:
                    self.word_counts[word] = 1
        
        # Sort words by frequency
        sorted_words = sorted(self.word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Take top num_words-1 (reserve 0 for padding)
        top_words = sorted_words[:self.num_words-1]
        
        # Create word_index mapping
        self.word_index = {word: idx+1 for idx, (word, _) in enumerate(top_words)}
        self.index_word = {idx: word for word, idx in self.word_index.items()}
        
        self.fitted = True
    
    def texts_to_sequences(self, texts):
        """Convert texts to sequences of word indices."""
        if not self.fitted:
            raise ValueError("Tokenizer not fitted. Call fit_on_texts first.")
        
        sequences = []
        for text in texts:
            sequence = []
            for word in text.lower().split():
                if word in self.word_index:
                    sequence.append(self.word_index[word])
            sequences.append(sequence)
        
        return sequences

def pad_sequences(sequences, maxlen=None, padding='pre'):
    """Pad sequences to the same length."""
    if maxlen is None:
        maxlen = max(len(seq) for seq in sequences)
    
    padded_sequences = []
    for seq in sequences:
        if len(seq) > maxlen:
            # Truncate
            padded_seq = seq[:maxlen]
        else:
            # Pad
            pad_length = maxlen - len(seq)
            if padding == 'pre':
                padded_seq = [0] * pad_length + seq
            else:
                padded_seq = seq + [0] * pad_length
        padded_sequences.append(padded_seq)
    
    return padded_sequences

class TextClassifier:
    def __init__(self, model_path=None):
        self.model = None
        self.tokenizer = None
        self.max_sequence_length = 50
        self.embedding_dim = 100
        self.hidden_dim = 64
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Class labels
        self.HEADER = 0
        self.LIST = 1
        self.TEXT = 2
        
        self.class_names = ['HEADER', 'LIST', 'TEXT']
        
        # Load model if provided
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
    
    def _extract_features(self, text):
        """Extract additional features from text line."""
        features = []
        
        # Text length
        text_len = len(text)
        
        # Capitalization ratio
        if text_len > 0:
            cap_ratio = sum(1 for c in text if c.isupper()) / text_len
            features.append(cap_ratio)
        else:
            features.append(0)
        
        # Has numbers
        features.append(1 if any(c.isdigit() for c in text) else 0)
        
        # Line length normalized - more extreme scaling to differentiate better
        # Short lines (typical for headers) will have values closer to 1
        # Long lines (typical for paragraphs) will have values closer to 0
        features.append(min(1.0, 15.0 / max(1, text_len)))
        
        # Has periods
        features.append(1 if '.' in text else 0)
        
        # Starts with number + period pattern (like "1.", "1.1.")
        features.append(1 if re.match(r'^\d+\.', text) else 0)
        
        # Is all caps and at least 4 characters
        features.append(1 if text.isupper() and text_len >= 4 else 0)
        
        # Word count (headers typically have fewer words) - more extreme scaling
        # Normalize to range 0-1 where fewer words are closer to 1
        word_count = len(text.split())
        features.append(min(1.0, 3.0 / max(1, word_count)))
        
        # Contains typical header words
        header_words = ['глава', 'введение', 'заключение', 'список', 'методы', 'результаты', 'выводы']
        features.append(1 if any(word.lower() in text.lower() for word in header_words) else 0)
        
        # Ends with punctuation typical in normal text (not headers)
        features.append(1 if text.rstrip().endswith(('.', '?', '!', ':', ';')) else 0)
        
        # Contains verbs typical in normal text, less common in headers
        verb_indicators = ['является', 'используется', 'был', 'будет', 'показал', 'имеет', 'может', 
                         'позволяет', 'включает', 'считается', 'представляет', 'определяет']
        has_verbs = any(verb in text.lower() for verb in verb_indicators)
        features.append(1 if has_verbs else 0)
        
        # Has a comma (headers rarely have commas)
        features.append(1 if ',' in text else 0)
        
        # Is a single word or very short phrase (potential header)
        features.append(1 if word_count <= 2 else 0)
        
        # Has parentheses (common in normal text, rare in headers)
        features.append(1 if '(' in text and ')' in text else 0)
        
        # Text-to-word ratio (headers tend to have shorter words)
        avg_word_len = text_len / max(1, word_count)
        features.append(min(1.0, avg_word_len / 10.0))
        
        # Sentence count (more sentences suggest normal text)
        sentence_count = len(re.split(r'[.!?]+', text))
        features.append(min(1.0, 1.0 / max(1, sentence_count-1)))
        
        # Space-to-character ratio (headers often have more spaces proportionally)
        space_ratio = text.count(' ') / max(1, text_len)
        features.append(space_ratio)
        
        return np.array(features)
    
    def prepare_data(self, texts, labels=None, training=False):
        """
        Prepare text data for model input.
        If training=True, fit the tokenizer, otherwise use existing tokenizer.
        """
        # Initialize tokenizer if in training mode or not yet initialized
        if training or self.tokenizer is None:
            self.tokenizer = TextTokenizer(num_words=5000)
            self.tokenizer.fit_on_texts(texts)
        
        # Convert text to sequences
        sequences = self.tokenizer.texts_to_sequences(texts)
        padded_sequences = pad_sequences(sequences, maxlen=self.max_sequence_length)
        
        # Extract additional features
        additional_features = np.array([self._extract_features(text) for text in texts])
        
        # Convert to PyTorch tensors
        text_tensor = torch.tensor(padded_sequences, dtype=torch.long)
        features_tensor = torch.tensor(additional_features, dtype=torch.float)
        
        if labels is not None:
            # Convert one-hot encoded labels to tensor
            labels_tensor = torch.tensor(labels, dtype=torch.float)
            return text_tensor, features_tensor, labels_tensor
        else:
            return text_tensor, features_tensor
    
    def build_model(self, vocab_size, feature_dim):
        """Build the LSTM model for multiclass classification."""
        model = LSTMClassifier(
            vocab_size=vocab_size,
            embedding_dim=self.embedding_dim,
            hidden_dim=self.hidden_dim,
            feature_dim=feature_dim,
            output_dim=3,  # 3 classes: HEADER, LIST, TEXT
            dropout=0.3    # Increase dropout for better regularization
        )
        return model
    
    def train(self, texts, labels, validation_split=0.2, epochs=15, batch_size=32):
        """Train the model on the provided text data and labels."""
        # Count examples per class
        header_count = sum(label[0] for label in labels)
        list_count = sum(label[1] for label in labels)
        text_count = sum(label[2] for label in labels)
        
        print(f"Training with {len(texts)} examples ({header_count} headers, {list_count} lists, {text_count} normal text)")
        
        # Prepare data
        X_text, X_features, y = self.prepare_data(texts, labels, training=True)
        
        # Split into training and validation sets
        train_indices, val_indices = train_test_split(
            range(len(texts)), 
            test_size=validation_split, 
            random_state=42,
            stratify=[np.argmax(label) for label in labels]  # Stratify by the dominant class
        )
        
        # Create datasets
        train_dataset = TensorDataset(
            X_text[train_indices], 
            X_features[train_indices], 
            y[train_indices]
        )
        val_dataset = TensorDataset(
            X_text[val_indices], 
            X_features[val_indices], 
            y[val_indices]
        )
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        
        # Build model
        vocab_size = len(self.tokenizer.word_index) + 1
        feature_dim = X_features.shape[1]
        self.model = self.build_model(vocab_size, feature_dim)
        self.model.to(self.device)
        
        # Define optimizer and loss function for multiclass classification
        optimizer = optim.Adam(self.model.parameters(), lr=0.0005, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        
        # Training loop
        best_val_loss = float('inf')
        best_model_state = None
        patience = 7
        patience_counter = 0
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            for batch_text, batch_features, batch_labels in train_loader:
                # Move tensors to device
                batch_text = batch_text.to(self.device)
                batch_features = batch_features.to(self.device)
                batch_labels = batch_labels.to(self.device)
                
                # Forward pass
                optimizer.zero_grad()
                logits = self.model(batch_text, batch_features)
                
                # Calculate loss using CrossEntropyLoss expects logits, not probabilities
                # We need to get the class indices from one-hot encoded labels
                target_indices = torch.argmax(batch_labels, dim=1)
                loss = criterion(logits, target_indices)
                
                # Backward pass
                loss.backward()
                
                # Gradient clipping to prevent exploding gradients
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                
                optimizer.step()
                
                # Update metrics
                train_loss += loss.item() * len(batch_labels)
                train_preds = torch.argmax(logits, dim=1)
                train_correct += (train_preds == target_indices).sum().item()
                train_total += len(batch_labels)
            
            train_loss /= train_total
            train_acc = train_correct / train_total
            
            # Validation
            self.model.eval()
            val_loss = 0
            val_correct = 0
            val_total = 0
            all_preds = []
            all_targets = []
            
            with torch.no_grad():
                for batch_text, batch_features, batch_labels in val_loader:
                    # Move tensors to device
                    batch_text = batch_text.to(self.device)
                    batch_features = batch_features.to(self.device)
                    batch_labels = batch_labels.to(self.device)
                    
                    # Forward pass
                    logits = self.model(batch_text, batch_features)
                    
                    # Compute loss
                    target_indices = torch.argmax(batch_labels, dim=1)
                    loss = criterion(logits, target_indices)
                    
                    # Update metrics
                    val_loss += loss.item() * len(batch_labels)
                    val_preds = torch.argmax(logits, dim=1)
                    val_correct += (val_preds == target_indices).sum().item()
                    val_total += len(batch_labels)
                    
                    # Store predictions and targets for analysis
                    all_preds.extend(val_preds.cpu().numpy())
                    all_targets.extend(target_indices.cpu().numpy())
            
            val_loss /= val_total
            val_acc = val_correct / val_total
            
            # Calculate per-class metrics
            metrics = []
            for cls in range(3):  # 3 classes: HEADER, LIST, TEXT
                # True positives, false positives, false negatives
                tp = sum(1 for p, t in zip(all_preds, all_targets) if p == cls and t == cls)
                fp = sum(1 for p, t in zip(all_preds, all_targets) if p == cls and t != cls)
                fn = sum(1 for p, t in zip(all_preds, all_targets) if p != cls and t == cls)
                
                # Calculate precision, recall, F1
                precision = tp / max(1, tp + fp)
                recall = tp / max(1, tp + fn)
                f1 = 2 * precision * recall / max(0.001, precision + recall)
                
                metrics.append((precision, recall, f1))
            
            # Convert any NumPy arrays to Python scalars to avoid formatting issues
            epoch_num = int(epoch + 1) if isinstance(epoch, np.ndarray) else epoch + 1
            epochs_num = int(epochs) if isinstance(epochs, np.ndarray) else epochs
            train_loss_val = float(train_loss) if isinstance(train_loss, np.ndarray) else train_loss
            train_acc_val = float(train_acc) if isinstance(train_acc, np.ndarray) else train_acc
            val_loss_val = float(val_loss) if isinstance(val_loss, np.ndarray) else val_loss
            val_acc_val = float(val_acc) if isinstance(val_acc, np.ndarray) else val_acc
            
            # Print metrics
            print(f'Epoch {epoch_num}/{epochs_num} | '
                  f'Train Loss: {train_loss_val:.4f}, Train Acc: {train_acc_val:.4f} | '
                  f'Val Loss: {val_loss_val:.4f}, Val Acc: {val_acc_val:.4f}')
            
            # Print per-class metrics
            for i, cls_name in enumerate(['HEADER', 'LIST', 'TEXT']):
                p, r, f1 = metrics[i]
                p_val = float(p) if isinstance(p, np.ndarray) else p
                r_val = float(r) if isinstance(r, np.ndarray) else r
                f1_val = float(f1) if isinstance(f1, np.ndarray) else f1
                print(f'{cls_name} P/R/F1: {p_val:.4f}/{r_val:.4f}/{f1_val:.4f}')
            
            # Early stopping with patience
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = self.model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
        
        # Restore best model
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
        
        return {'train_loss': train_loss, 'train_acc': train_acc, 
                'val_loss': val_loss, 'val_acc': val_acc}
    
    def predict(self, texts):
        """
        Predict the class probabilities for each text.
        Returns a numpy array of shape (n_samples, n_classes)
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded. Call train() or load a pretrained model.")
        
        self.model.eval()
        X_text, X_features = self.prepare_data(texts)
        
        # Move tensors to device
        X_text = X_text.to(self.device)
        X_features = X_features.to(self.device)
        
        # Get predictions
        with torch.no_grad():
            logits = self.model(X_text, X_features)
            probabilities = torch.softmax(logits, dim=1)
        
        # Convert to numpy array
        return probabilities.cpu().numpy()
    
    def post_process_prediction(self, text, probabilities, thresholds=None):
        """
        Apply post-processing rules to predictions to improve accuracy.
        Returns the final classification (0=HEADER, 1=LIST, 2=TEXT)
        
        Args:
            text: The text to classify
            probabilities: Array of class probabilities [header_prob, list_prob, text_prob]
            thresholds: Optional dictionary of thresholds for each class, defaults to {HEADER: 0.5, LIST: 0.5, TEXT: 0.3}
        """
        if thresholds is None:
            thresholds = {self.HEADER: 0.5, self.LIST: 0.5, self.TEXT: 0.3}
        
        # PRIORITY RULE: Always classify chapter headings as headers regardless of ML prediction
        if re.match(r'^ГЛАВА\s+\d+', text, re.IGNORECASE):
            return self.HEADER
            
        # Check for strong pattern matches before even looking at predictions
        
        # Patterns that are always lists regardless of prediction
        if re.match(r'^[a-zа-я]\)\s+', text) or re.match(r'^[a-zа-я]\.\)\s+', text):  # Lettered list items
            return self.LIST
            
        if re.match(r'^\d+\)\s+', text):  # Numbered list items with parenthesis
            return self.LIST
            
        if re.match(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.\s+', text):  # Roman numerals
            return self.LIST
        
        # Always classify standard section headers as headers
        if re.match(r'^(ВВЕДЕНИЕ|ЗАКЛЮЧЕНИЕ|СПИСОК\s+.*ЛИТЕРАТУР)', text, re.IGNORECASE):
            return self.HEADER
        
        # List introductions - sentences that end with a colon and introduce lists but are not headers
        # Lines like "The key methods include:" or "Methods consist of:"
        if (text.strip().endswith(':') and 
            not re.match(r'^[0-9]+\.[0-9]+\.?\s+', text) and  # Not a subsection number
            not text.isupper() and                            # Not all uppercase
            len(text.split()) <= 8 and                        # Not too long
            not re.match(r'^ГЛАВА|^ВВЕДЕНИЕ|^ЗАКЛЮЧЕНИЕ', text, re.IGNORECASE)):  # Not a main section
            
            # These should typically be classified as normal text, not headers
            # Check for common list introduction patterns
            list_intro_patterns = [
                r'включа[ею]т',        # включает, включают
                r'состо[ия]т из',      # состоит из, состоят из 
                r'явля[ею]тся',        # является, являются
                r'выделя[ею]т',        # выделяет, выделяют
                r'относятся',
                r'можно (?:отнести|выделить|разделить|отметить)', # можно отнести, можно выделить
                r'следующие',
                r'таких как',
                r'таким образом',
                r'приведены',
                r'представлены'
            ]
            
            if any(re.search(pattern, text.lower()) for pattern in list_intro_patterns):
                return self.TEXT  # This is a list introduction, not a header
            
        # Get initial classification (argmax of probabilities)
        initial_class = np.argmax(probabilities)
        
        # Apply confidence thresholds
        # If the confidence is too low, fall back to TEXT
        if probabilities[initial_class] < thresholds.get(initial_class, 0.5):
            return self.TEXT
        
        # Apply specific rule for dash bullets that are frequently misclassified
        # This specifically targets cases like "- Something: description" that might be misclassified as headers
        if text.startswith('- '):
            return self.LIST
            
        # Additional rules for HEADER classification
        if initial_class == self.HEADER:
            # Rule 1: Table/Figure references are not headers
            if re.match(r'^(таблица|рисунок|график|табл\.|рис\.)\s+\d+', text.lower()):
                return self.LIST  # These are more like lists
            
            # Rule 2: Short phrases that contain typical text indicators are not headers
            if len(text.split()) <= 3:
                text_indicators = ['является', 'был', 'были', 'имеет', 'имеют', 'показал', 'показали']
                if any(indicator in text.lower() for indicator in text_indicators):
                    return self.TEXT
            
            # Rule 3: If text contains a full sentence with a subject and predicate, it's likely not a header
            if ',' in text and len(text.split()) > 5:
                return self.TEXT
            
            # Rule 4: Text with multiple sentences is not a header
            if text.count('.') > 1 and not re.match(r'^\d+\.\d+\.', text):
                return self.TEXT
            
            # Rule 5: Text starting with these words in lowercase is likely not a header
            non_header_starts = ['в ', 'на ', 'с ', 'для ', 'при ', 'по ', 'методы ', 'подход ']
            if any(text.lower().startswith(start) for start in non_header_starts) and not text.isupper():
                return self.TEXT
                
            # Rule 6: Check for lettered or numbered list formats
            if re.match(r'^[a-zа-я]\)', text) or re.match(r'^\d+\)', text):
                return self.LIST
                
            # Rule 7: Lines ending with colon that introduce lists are not headers
            # For example: "Examples include:" or "Methods consist of:"
            if text.strip().endswith(':'):
                # Check for common verbs that introduce lists
                list_introduction_verbs = [
                    'включа', 'явля', 'содерж', 'состо', 'представ', 'включ', 
                    'относ', 'выдел', 'существ', 'счита', 'класс'
                ]
                
                if any(verb in text.lower() for verb in list_introduction_verbs):
                    return self.TEXT

        # Additional rules for LIST classification
        elif initial_class == self.LIST:
            # If it starts with a number or dash followed by a space, it's likely a list item
            if re.match(r'^(\d+[\.\)]\s+|[-•]\s+)', text):
                return self.LIST
                
            # Bibliography-style references (Author Year)
            if re.match(r'^(\d+\.\s+[\w]+\s+[\w]\.[\w]\.|\d+\.\s+[А-Я][а-я]+\s+[А-Я]\.)', text):
                return self.LIST
                
            # Check for roman numerals at start
            if re.match(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.\s+', text):
                return self.LIST
                
            # If none of the list patterns match, confirm it's actually list-like
            if not re.match(r'^([-•]\s+|\d+[\.)\s]+|[a-zа-я][\.)\s]+|[IVX]+\.\s+)', text):
                # If it doesn't match standard list patterns AND has sentence structure, 
                # it's more likely normal text
                if len(text.split()) > 6 and ('.' in text[5:] or ',' in text):
                    return self.TEXT
        
        # Additional rule for TEXT classification to catch some common patterns
        elif initial_class == self.TEXT:
            # If it's a dash-prefixed item, verify it's not actually a list item
            if text.startswith('- '):
                return self.LIST
                
            # Check for numbered lists that might be misclassified as text
            if re.match(r'^\d+\.\s+', text) and not re.match(r'^\d+\.\d+\.\s+', text):  # Numbered but not subsection
                if len(text.split()) < 10:  # Not too long
                    return self.LIST
        
        return initial_class
    
    def predict_document(self, document_lines):
        """
        Predict classes for a full document, using document structure context to improve accuracy.
        This implements tracking list blocks to avoid misclassifying list items as headers.
        
        Args:
            document_lines: List of text lines in the document
            
        Returns:
            List of predicted classes (0=HEADER, 1=LIST, 2=TEXT)
        """
        # Get initial predictions
        probabilities = self.predict(document_lines)
        initial_predictions = [np.argmax(probs) for probs in probabilities]
        
        # Apply basic post-processing to get better starting predictions
        predictions = [self.post_process_prediction(text, probs) 
                      for text, probs in zip(document_lines, probabilities)]
        
        # Now apply document context-aware processing
        context_predictions = predictions.copy()
        
        # Track list block context
        in_list_block = False
        list_block_indent = None
        list_style = None  # Track the style of current list (numbered, bulleted, etc.)
        list_item_pattern = re.compile(r'^([-•*]\s+|\d+[\.)\s]+|[a-zа-я][\.)\s]+)')
        subsection_pattern = re.compile(r'^\d+\.\d+\.?\s+')
        
        # Process document in sequence
        for i in range(len(document_lines)):
            text = document_lines[i].strip()
            if not text:
                continue
                
            # Special priority: Always keep main section headers as HEADER regardless of context
            if re.match(r'^(ВВЕДЕНИЕ|ГЛАВА\s+\d+|ЗАКЛЮЧЕНИЕ|СПИСОК\s+[А-Я\s]+)', text, re.IGNORECASE):
                context_predictions[i] = self.HEADER
                in_list_block = False  # End any active list block
                continue
            
            # Check if this is a list item based on its pattern
            is_list_pattern = bool(list_item_pattern.match(text))
            
            # Check for subsection headers (N.N. pattern)
            is_subsection = bool(subsection_pattern.match(text))
            
            # First case: Handle subsection headers specifically
            if is_subsection:
                # Check if it was initially classified as a header
                if predictions[i] == self.HEADER:
                    # If initial prediction was HEADER, trust that over list context
                    context_predictions[i] = self.HEADER
                    in_list_block = False  # End list block
                    continue
                
                # Check text content for indicators this is a true subsection header
                # Subsection headers are typically short and don't end with ":"
                if len(text.split()) <= 6 and not text.endswith(':') and not re.match(r'^.+\d', text.split()[1] if len(text.split()) > 1 else ""):
                    # Heuristic: If it looks like a numbered item followed by a short word, 
                    # it's more likely a subsection header
                    context_predictions[i] = self.HEADER
                    in_list_block = False  # End list block
                    continue
                    
                # Another case: If this is "1.1." followed by a capitalized title-like text
                # and not in the middle of a list sequence, it's likely a subsection header
                if i > 0 and not in_list_block and len(text.split()) > 1:
                    # Check if the text after the number starts with uppercase (likely a title)
                    title_part = ' '.join(text.split()[1:])
                    if title_part and title_part[0].isupper():
                        # Check previous line isn't a list item (avoid breaking list sequences)
                        prev_is_list = context_predictions[i-1] == self.LIST
                        if not prev_is_list or re.match(r'^[a-zа-я][\.)\s]+', document_lines[i-1]):
                            context_predictions[i] = self.HEADER
                            continue
            
            # Check for change in numbering pattern (as user suggested)
            # If we just saw "1. 2. 3." pattern and now see "1.1." pattern, that's a header transition
            if is_subsection and i > 0:
                # Check if previous line was a regular numbered item
                prev_line = document_lines[i-1].strip()
                if re.match(r'^\d+[\.)\s]+', prev_line) and not re.match(r'^\d+\.\d+', prev_line):
                    # We've switched from "1." to "1.1." format - likely a subsection header
                    context_predictions[i] = self.HEADER
                    in_list_block = False
                    continue
            
            # Check for list block start
            if is_list_pattern and not in_list_block:
                # First, check if this might be a subsection header that looks like a list item
                is_likely_subsection = False
                
                # If it was initially classified as HEADER and has a specific format,
                # it might be a subsection header despite looking like a list item
                if predictions[i] == self.HEADER and re.match(r'^\d+\.\d+[\.\s]', text):
                    is_likely_subsection = True
                
                if is_likely_subsection:
                    context_predictions[i] = self.HEADER
                    continue
                
                # Otherwise, it's a list item starting a new list block
                in_list_block = True
                list_block_indent = len(document_lines[i]) - len(document_lines[i].lstrip())
                list_style = 'numbered' if re.match(r'^\d+[\.)\s]', text) else 'bulleted'
                context_predictions[i] = self.LIST
                continue
                
            # Track list block state
            if in_list_block:
                current_indent = len(document_lines[i]) - len(document_lines[i].lstrip())
                
                # List items or indented content within list
                if is_list_pattern or current_indent > list_block_indent:
                    # Check for subsection headers that might be misclassified as list items
                    if is_subsection:
                        # Subsection headers with same format (short, title-case) as described above
                        if len(text.split()) <= 6 and not text.endswith(':'):
                            context_predictions[i] = self.HEADER
                            in_list_block = False  # End list block
                            continue
                    
                    context_predictions[i] = self.LIST
                    continue
                
                # Check if we're still in a list but at same indentation
                if current_indent == list_block_indent and not text.strip():
                    # Empty line within list - keep context
                    continue
                    
                # Check if this is a subsection header inside a list
                if (re.match(r'^\d+\.\d+\.', text) and 
                    (predictions[i] == self.HEADER or len(text.split()) <= 5)):
                    
                    # This specifically handles the "2.1. Смешанные списки" case
                    # Check text length and format to distinguish subsection headers from list items
                    words = text.split()
                    if len(words) <= 6 and not text.strip().endswith(':'):
                        # Short text without ending colon is likely a real header
                        context_predictions[i] = self.HEADER
                        in_list_block = False  # End list block
                        continue
                
                # End of list block detection
                if current_indent <= list_block_indent and len(text.strip()) > 0:
                    # Check if it's a clearly different structure like a header
                    if context_predictions[i] == self.HEADER:
                        in_list_block = False
                        continue
                    
                    # Check if we're in a paragraph after a list
                    if not is_list_pattern and len(text.split()) > 3:
                        in_list_block = False
                        continue
            
            # Special case: Actual list items that weren't initially detected
            if is_list_pattern and context_predictions[i] != self.LIST and not is_subsection:
                context_predictions[i] = self.LIST
                in_list_block = True
                list_block_indent = len(document_lines[i]) - len(document_lines[i].lstrip())
                list_style = 'numbered' if re.match(r'^\d+[\.)\s]', text) else 'bulleted'
            
            # Special case: Header detection improvement
            if context_predictions[i] == self.HEADER:
                # Check prior and next lines to validate header context
                is_valid_header = True
                
                # If previous line exists and is a list, this might be a list continuation
                if i > 0 and context_predictions[i-1] == self.LIST:
                    # Check if this matches list item patterns to avoid misclassifying
                    if is_list_pattern and not is_subsection:
                        context_predictions[i] = self.LIST
                        is_valid_header = False
                
                # If we have next line, check heading -> content pattern
                if is_valid_header and i < len(document_lines) - 1:
                    next_text = document_lines[i+1]
                    next_prediction = context_predictions[i+1]
                    
                    # Headers are typically followed by text or list items, not other headers
                    if next_prediction == self.HEADER and not re.match(r'^(ГЛАВА|РАЗДЕЛ)', next_text, re.IGNORECASE):
                        # Consecutive headers - check which one is more likely to be real
                        if len(text.split()) > len(next_text.split()):
                            # Current line is longer - more likely text or list
                            context_predictions[i] = self.TEXT
        
        # Final pass - check for subsection headers that may have been missed
        # This prioritizes preservation of document structure
        for i in range(len(document_lines)):
            text = document_lines[i].strip()
            
            # Check specifically for subsection headers that may have been classified as LIST
            if context_predictions[i] == self.LIST and re.match(r'^\d+\.\d+\.?\s+', text):
                # Look at surrounding context
                words = text.split()
                
                # Strong indicators this is a subsection header:
                # 1. Short text (1-5 words)
                # 2. Doesn't end with colon (which often introduces lists)
                # 3. First word after number is capitalized
                if (len(words) >= 2 and len(words) <= 5 and 
                    not text.endswith(':') and 
                    words[1][0].isupper()):
                    
                    context_predictions[i] = self.HEADER
                    
                    # If we classified this as a header, ensure next few lines aren't
                    # inadvertently classified as headers too (avoid false header chains)
                    for j in range(i+1, min(i+3, len(document_lines))):
                        if (context_predictions[j] == self.HEADER and 
                            not re.match(r'^\d+\.\d+\.?\s+', document_lines[j].strip()) and
                            not re.match(r'^(ГЛАВА|ВВЕДЕНИЕ|ЗАКЛЮЧЕНИЕ)', document_lines[j].strip(), re.IGNORECASE)):
                            # Downgrade likely paragraph text after a header that was misclassified
                            context_predictions[j] = self.TEXT
        
        # Return the context-aware predictions
        return context_predictions
    
    def classify_text(self, text):
        """
        Classify a single text string and return the class label.
        """
        probabilities = self.predict([text])[0]
        class_idx = self.post_process_prediction(text, probabilities)
        return self.class_names[class_idx]
    
    def save_model(self, model_path):
        """Save the trained model and tokenizer."""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Save model state
        torch.save(self.model.state_dict(), model_path)
        
        # Save tokenizer
        tokenizer_path = os.path.join(os.path.dirname(model_path), 'tokenizer.pickle')
        with open(tokenizer_path, 'wb') as handle:
            pickle.dump(self.tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Save model info (for reconstruction)
        model_info = {
            'vocab_size': len(self.tokenizer.word_index) + 1,
            'embedding_dim': self.embedding_dim,
            'hidden_dim': self.hidden_dim,
            'feature_dim': 16,  # Updated number of features from _extract_features
            'max_sequence_length': self.max_sequence_length
        }
        
        model_info_path = os.path.join(os.path.dirname(model_path), 'model_info.pickle')
        with open(model_info_path, 'wb') as handle:
            pickle.dump(model_info, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _load_model(self, model_path):
        """Load a saved model and tokenizer."""
        # Load tokenizer
        tokenizer_path = os.path.join(os.path.dirname(model_path), 'tokenizer.pickle')
        with open(tokenizer_path, 'rb') as handle:
            self.tokenizer = pickle.load(handle)
        
        # Load model info
        model_info_path = os.path.join(os.path.dirname(model_path), 'model_info.pickle')
        with open(model_info_path, 'rb') as handle:
            model_info = pickle.load(handle)
        
        # Update parameters
        self.embedding_dim = model_info['embedding_dim']
        self.hidden_dim = model_info['hidden_dim']
        self.max_sequence_length = model_info['max_sequence_length']
        
        # Create and load model
        self.model = LSTMClassifier(
            vocab_size=model_info['vocab_size'],
            embedding_dim=self.embedding_dim,
            hidden_dim=self.hidden_dim,
            feature_dim=model_info['feature_dim'],
            output_dim=3,
            dropout=0.2
        )
        
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

def generate_training_data():
    """Generate synthetic training data for header/list/normal text classification."""
    import random
    random.seed(42)  # For reproducibility
    
    # Sample section headers
    section_headers = [
        "ВВЕДЕНИЕ", "ГЛАВА 1. ТЕОРЕТИЧЕСКИЕ ОСНОВЫ", "ГЛАВА 2. МЕТОДОЛОГИЯ ИССЛЕДОВАНИЯ",
        "ГЛАВА 3. РЕЗУЛЬТАТЫ И ОБСУЖДЕНИЕ", "ЗАКЛЮЧЕНИЕ", "СПИСОК ИСПОЛЬЗОВАННОЙ ЛИТЕРАТУРЫ",
        "СПИСОК ЛИТЕРАТУРЫ", "ОБЗОР ЛИТЕРАТУРЫ", "МЕТОДЫ", "МАТЕРИАЛЫ И МЕТОДЫ", "РЕЗУЛЬТАТЫ",
        "ОБСУЖДЕНИЕ", "ВЫВОДЫ", "БЛАГОДАРНОСТИ", "ПРИЛОЖЕНИЕ", "ABSTRACT", "АННОТАЦИЯ",
        "1.1. Исторический обзор", "1.2. Современное состояние проблемы", 
        "2.1. Методы исследования", "2.2. Материалы и оборудование",
        "3.1. Анализ полученных данных", "3.2. Сравнение с существующими результатами"
    ]
    
    # True headers - only these patterns should be classified as headers
    true_headers = [
        "ВВЕДЕНИЕ",
        "ГЛАВА 1. МЕТОДЫ ИССЛЕДОВАНИЯ",
        "ГЛАВА 2. РЕЗУЛЬТАТЫ ЭКСПЕРИМЕНТОВ",
        "ЗАКЛЮЧЕНИЕ",
        "СПИСОК ЛИТЕРАТУРЫ",
        "1. ОБЩИЕ ПОЛОЖЕНИЯ",
        "2. МЕТОДИКА ПРОВЕДЕНИЯ ИСПЫТАНИЙ",
        "1.1. Основные принципы",
        "2.3. Анализ данных",
        "ВЫВОДЫ И РЕКОМЕНДАЦИИ"
    ]
    
    # More subsection patterns - being more selective with fewer patterns
    for i in range(1, 4):
        for j in range(1, 4):
            section_headers.append(f"{i}.{j}. Подраздел {i}.{j}")
            section_headers.append(f"{i}.{j} Подраздел {i}.{j}")  # Without period after subsection number
    
    # More chapter patterns - being more selective with fewer patterns
    for i in range(1, 4):
        section_headers.append(f"ГЛАВА {i}. НАЗВАНИЕ ГЛАВЫ {i}")
        section_headers.append(f"Глава {i}. Название главы {i}")  # Mixed case variation
        section_headers.append(f"РАЗДЕЛ {i}. НАЗВАНИЕ РАЗДЕЛА {i}")
        section_headers.append(f"Раздел {i}. Название раздела {i}")
    
    # Generate variations of headers - but limit the variations to avoid overfitting
    headers = []
    for header in section_headers:
        headers.append(header)
        
        # Only add a couple of variations to avoid overwhelming the dataset
        if not header.isupper() and len(header.split()) <= 3:
            headers.append(header.upper())
    
    # Add our true headers to make sure they're included
    headers.extend(true_headers)
    
    # NEW: Create list items examples
    list_items = []
    
    # Bibliography style entries (numbered)
    bibliography_items = [
        "1. Рассел С., Норвиг П. Искусственный интеллект: современный подход. - М.: Вильямс, 2016.",
        "2. Флах П. Машинное обучение. Наука и искусство построения алгоритмов. - М.: ДМК Пресс, 2015.",
        "3. Гудфеллоу Я., Бенджио И., Курвилль А. Глубокое обучение. - М.: ДМК Пресс, 2018.",
        "4. Хайкин С. Нейронные сети: полный курс. - М.: Вильямс, 2019.",
        "5. Ульман Д. Основы систем баз данных. - М.: Лори, 2014.",
        "6. Шалев-Шварц Ш., Бен-Давид Ш. Идеи машинного обучения. - М.: ДМК Пресс, 2018.",
        "7. Николенко С.И., Кадурин А., Архангельская Е. Глубокое обучение. - СПб.: Питер, 2018.",
        "8. Аббас А. Основы искусственного интеллекта и машинное обучение. - М.: Вильямс, 2020."
    ]
    
    # Generate more bibliography items
    for i in range(9, 30):
        authors = random.choice(["Иванов И.И.", "Петров П.П.", "Сидоров С.С.", "Смирнов А.А.", "Кузнецов В.В."])
        title = f"Название книги {i} о машинном обучении и ИИ"
        publisher = random.choice(["М.: ДМК Пресс", "СПб.: Питер", "М.: Вильямс", "М.: Лори"])
        year = random.randint(2010, 2023)
        bibliography_items.append(f"{i}. {authors} {title}. - {publisher}, {year}.")
    
    # Dash bullet points
    dash_bullets = [
        "- 1950-1960-е годы: зарождение ИИ как научного направления",
        "- 1970-1980-е годы: развитие экспертных систем и логического программирования",
        "- 1990-2000-е годы: возрождение нейронных сетей и развитие машинного обучения",
        "- 2010-2020-е годы: глубокое обучение, большие данные и прикладные системы ИИ"
    ]
    
    # Generate more dash bullet points
    bullet_topics = [
        "преимущества метода", "недостатки подхода", "этапы исследования", 
        "компоненты системы", "принципы работы", "ключевые алгоритмы",
        "основные концепции", "области применения", "ограничения модели"
    ]
    
    for topic in bullet_topics:
        for i in range(3):
            dash_bullets.append(f"- {topic.capitalize()} {i+1}: {random.choice(['описание', 'характеристика', 'анализ'])} важных аспектов")
    
    # Add educational/technical list items that are similar to the problem cases
    educational_list_items = [
        "- Обучение с учителем: алгоритм обучается на размеченных данных и примерах",
        "- Обучение без учителя: алгоритм самостоятельно находит структуру в данных",
        "- Обучение с подкреплением: алгоритм обучается через взаимодействие со средой",
        "- Полуконтролируемое обучение: использует как размеченные, так и неразмеченные данные",
        "- Трансферное обучение: перенос знаний из одной области в другую",
        "- Адаптивные обучающие системы: подстраиваются под уровень знаний пользователя",
        "- Интеллектуальные репетиторы и ассистенты: помогают в образовательном процессе",
        "- Анализ больших данных: используется для оптимизации различных процессов",
        "- Генеративные модели: создают новый контент на основе обучающих данных",
        "- Дискриминативные модели: различают классы объектов в данных"
    ]
    
    # Add numbered list items (not bibliography style)
    numbered_list_items = [
        "1) Анализ требований и проектирование системы",
        "2) Разработка архитектуры программного обеспечения",
        "3) Реализация компонентов системы",
        "4) Тестирование и отладка программного продукта",
        "5) Внедрение и сопровождение системы"
    ]
    
    # List items with longer explanations
    long_list_items = [
        "- Глубокое обучение: современный подход в машинном обучении, основанный на использовании многослойных нейронных сетей для решения сложных задач, таких как распознавание образов, обработка естественного языка и др.",
        "- Компьютерное зрение: область искусственного интеллекта, которая занимается анализом и пониманием изображений и видео с использованием алгоритмов обработки и распознавания визуальной информации.",
        "- Обработка естественного языка: направление искусственного интеллекта и компьютерной лингвистики, изучающее проблемы компьютерного анализа и синтеза текстов на естественном человеческом языке."
    ]
    
    # List items that might be confused with headers
    potential_header_like_list_items = [
        "- КЛЮЧЕВЫЕ ТЕХНОЛОГИИ машинного обучения включают нейронные сети",
        "- ОСНОВНЫЕ КОНЦЕПЦИИ искусственного интеллекта охватывают различные подходы",
        "- СОВРЕМЕННЫЕ МЕТОДЫ анализа данных основаны на статистических моделях",
        "- ВАЖНЫЕ АСПЕКТЫ разработки включают проектирование архитектуры"
    ]
    
    # Add more examples of numbered list formats
    numbered_formats = [
        "1) Первый элемент списка в формате с закрывающей скобкой",
        "2) Второй элемент списка в формате с закрывающей скобкой",
        "3) Третий элемент списка в формате с закрывающей скобкой",
        "4) Четвертый элемент списка в формате с закрывающей скобкой",
        "5) Пятый элемент списка в формате с закрывающей скобкой",
        "1). Первый элемент списка в формате с точкой и скобкой",
        "2). Второй элемент списка в формате с точкой и скобкой",
        "3). Третий элемент списка в формате с точкой и скобкой"
    ]
    
    # Add more examples of lettered list formats
    lettered_formats = [
        "a) Первый элемент списка с буквенной нумерацией",
        "b) Второй элемент списка с буквенной нумерацией",
        "c) Третий элемент списка с буквенной нумерацией",
        "d) Четвертый элемент списка с буквенной нумерацией",
        "a). Вариант буквенной нумерации с точкой",
        "b). Второй вариант буквенной нумерации с точкой",
        "а) Вариант с кириллической буквой", 
        "б) Второй вариант с кириллической буквой"
    ]
    
    # Roman numerals
    roman_formats = [
        "I. Первый раздел с римскими цифрами",
        "II. Второй раздел с римскими цифрами",
        "III. Третий раздел с римскими цифрами",
        "IV. Четвертый раздел с римскими цифрами",
        "V. Пятый раздел с римскими цифрами"
    ]
    
    # Add specific examples from our analysis that were misclassified as headers
    problematic_list_items = [
        "1) Первый пункт нумерованного списка",
        "2) Второй пункт нумерованного списка",
        "3) Третий пункт с более длинным описанием, который должен точно отличаться от заголовка по своей структуре и формату",
        "1. Начальный этап исследования",
        "2. Основной этап проведения работ",
        "3. Заключительный этап и анализ результатов",
        "1). Подготовка образцов",
        "2). Калибровка оборудования",
        "3). Проведение измерений",
        "- Первый элемент маркированного списка",
        "- Второй элемент маркированного списка",
        "- Третий элемент с детальным описанием функциональности и особенностей работы данного компонента",
        "• Основной компонент системы",
        "• Вспомогательный элемент",
        "• Дополнительные модули и расширения",
        "* Важное примечание первое",
        "* Важное примечание второе",
        "* Важное примечание третье с пояснениями",
        "a) Первый вариант действий",
        "б) Второй вариант действий",
        "в) Третий вариант с расширенными пояснениями и комментариями",
        "а. Исходное положение",
        "б. Промежуточное состояние",
        "в. Конечное состояние системы",
        "а). Начальная конфигурация",
        "б). Оптимальная конфигурация",
        "в). Расширенная конфигурация с дополнительными параметрами",
        "1. Первый основной пункт",
        "- Подпункт первого пункта",
        "- Ещё один подпункт первого пункта",
        "2. Второй основной пункт",
        "a) Подпункт с буквенной нумерацией",
        "б) Ещё один подпункт с буквенной нумерацией"
    ]
    
    # Triple the amount of problematic examples to ensure the model learns these patterns
    problematic_list_items = problematic_list_items * 3
    
    # Combine all list items
    list_items = bibliography_items + dash_bullets + educational_list_items + numbered_list_items + long_list_items + potential_header_like_list_items + numbered_formats + lettered_formats + roman_formats + problematic_list_items
    
    # Sample normal text paragraphs (longer than before)
    normal_text = [
        "Искусственный интеллект (ИИ) является одной из самых динамично развивающихся областей компьютерных наук. Начиная с середины XX века, развитие ИИ прошло путь от простых алгоритмов до сложных нейронных сетей, способных решать многообразные задачи. В настоящее время технологии искусственного интеллекта всё глубже проникают в повседневную жизнь людей, изменяя характер труда, образования и досуга.",
        
        "Машинное обучение является одним из ключевых подходов в современном ИИ. Оно позволяет системам автоматически улучшать свою работу на основе опыта без явного программирования. Основные парадигмы машинного обучения включают обучение с учителем, обучение без учителя и обучение с подкреплением. Среди популярных методов машинного обучения можно выделить линейную и логистическую регрессию, деревья решений, случайные леса, методы опорных векторов и различные типы нейронных сетей.",
        
        "Глубокое обучение – это подраздел машинного обучения, основанный на использовании многослойных нейронных сетей. Этот подход произвел революцию в области ИИ, особенно в задачах распознавания образов и обработки естественного языка. Ключевые архитектуры глубоких нейронных сетей включают сверточные нейронные сети (CNN) для обработки изображений, рекуррентные нейронные сети (RNN) для обработки последовательностей, трансформеры для обработки текстов и генеративно-состязательные сети (GAN) для генерации новых данных.",
        
        "В медицине ИИ используется для диагностики заболеваний, разработки новых лекарств, персонализации лечения и оптимизации работы медицинских учреждений. Примеры успешного применения ИИ в медицине включают системы анализа медицинских изображений (рентгенограмм, МРТ, КТ), прогнозирование развития заболеваний на основе генетических и других данных, разработку новых лекарственных препаратов с использованием методов машинного обучения и системы поддержки принятия решений для врачей.",
        
        "Технологии искусственного интеллекта находят применение во все большем количестве сфер человеческой деятельности, трансформируя существующие процессы и создавая новые возможности. Среди приоритетных направлений развития ИИ можно выделить компьютерное зрение, обработку естественного языка, робототехнику, автономный транспорт и системы принятия решений. Каждая из этих областей имеет свои особенности, проблемы и перспективы развития.",
        
        # История
        "История России XX века представляет собой сложный и противоречивый период, наполненный драматическими событиями и радикальными преобразованиями. Революции 1917 года, Гражданская война, индустриализация и коллективизация, Великая Отечественная война, послевоенное восстановление страны, период оттепели, годы застоя и, наконец, перестройка – все эти события фундаментально изменили российское общество, государственное устройство и экономику.",
        
        "Великие географические открытия XV-XVII веков кардинально изменили представления европейцев о мире и оказали огромное влияние на последующее развитие человечества. Путешествия Христофора Колумба, Васко да Гамы, Фернана Магеллана и других мореплавателей привели к установлению новых торговых путей, колонизации обширных территорий и формированию первых глобальных империй. Эти процессы сопровождались как техническим и научным прогрессом, так и трагическими последствиями для коренных народов колонизируемых земель.",
        
        # Литература
        "Роман 'Война и мир' Льва Толстого считается одним из величайших произведений мировой литературы. В этом монументальном произведении, охватывающем период с 1805 по 1820 годы, автор создает обширную панораму российского общества эпохи наполеоновских войн. Толстой мастерски переплетает исторические события с судьбами вымышленных персонажей, глубоко исследуя вопросы войны и мира, смысла жизни, роли личности в истории.",
        
        "Серебряный век русской поэзии – период расцвета русской литературы в конце XIX – начале XX века, характеризующийся появлением множества талантливых поэтов и формированием новых художественных течений. Символизм, акмеизм, футуризм – эти и другие направления обогатили русскую и мировую культуру. Творчество Александра Блока, Анны Ахматовой, Владимира Маяковского, Марины Цветаевой и многих других поэтов этого периода до сих пор оказывает значительное влияние на развитие литературы.",
        
        # Биология и экология
        "Биоразнообразие является фундаментальной основой устойчивости экосистем и необходимым условием выживания человечества. Сохранение биологического разнообразия на генетическом, видовом и экосистемном уровнях представляет собой одну из важнейших задач современности. Деградация естественных местообитаний, чрезмерная эксплуатация природных ресурсов, загрязнение окружающей среды, инвазивные виды и изменение климата – основные факторы, угрожающие биоразнообразию планеты.",
        
        "Теория эволюции, сформулированная Чарльзом Дарвином и дополненная последующими исследователями, является фундаментальной концепцией современной биологии. Согласно этой теории, все существующие виды живых организмов произошли от общих предков путем естественного отбора и других эволюционных механизмов. Молекулярно-генетические исследования последних десятилетий предоставили множество новых доказательств эволюционного процесса и позволили уточнить многие детали филогенетических взаимосвязей между различными группами организмов.",
        
        # Физика
        "Квантовая физика – раздел физики, изучающий поведение материи и энергии на атомном и субатомном уровнях. В отличие от классической физики, квантовая механика описывает мир, в котором частицы могут находиться в состоянии суперпозиции, проявлять корпускулярно-волновой дуализм и быть квантово запутанными. Принцип неопределенности Гейзенберга, волновая функция Шрёдингера, принцип дополнительности Бора – все эти концепции революционизировали научное понимание природы материи и энергии.",
        
        "Общая теория относительности, созданная Альбертом Эйнштейном, описывает гравитацию как проявление искривления пространства-времени. Согласно этой теории, массивные тела искривляют пространство-время вокруг себя, что воспринимается другими телами как гравитационное притяжение. Предсказания общей теории относительности, такие как отклонение света в гравитационном поле, гравитационное красное смещение и существование черных дыр, были подтверждены многочисленными экспериментами и наблюдениями.",
        
        # Экономика
        "Глобализация мировой экономики характеризуется усилением взаимозависимости национальных экономик, интернационализацией производства и капитала, либерализацией международной торговли и формированием глобальных рынков. Этот процесс, ускорившийся во второй половине XX века, привел к существенным изменениям в структуре мирового хозяйства, международном разделении труда и механизмах экономического регулирования. Глобализация создает как новые возможности для экономического роста и повышения благосостояния, так и новые вызовы и риски.",
        
        "Цифровая экономика – экономическая деятельность, основанная на цифровых технологиях, включая электронную коммерцию, интернет-банкинг, онлайн-сервисы и цифровые платформы. Развитие цифровой экономики сопровождается фундаментальными изменениями в бизнес-моделях, структуре занятости, потребительском поведении и государственном управлении. Внедрение технологий больших данных, искусственного интеллекта, блокчейна и интернета вещей стимулирует дальнейшую цифровую трансформацию различных секторов экономики.",
        
        # Психология
        "Когнитивная психология изучает внутренние психические процессы, включая восприятие, внимание, память, мышление, воображение и речь. В отличие от бихевиоризма, концентрирующегося на наблюдаемом поведении, когнитивная психология рассматривает человека как активного обработчика информации. Исследования в области когнитивной психологии имеют широкое практическое применение в образовании, разработке пользовательских интерфейсов, нейрореабилитации и других сферах.",
        
        "Эмоциональный интеллект – способность человека распознавать эмоции, понимать намерения, мотивацию и желания других людей и свои собственные, а также управлять своими эмоциями и влиять на эмоции других людей. Высокий эмоциональный интеллект связан с успешностью в различных сферах жизни, включая профессиональную деятельность, межличностные отношения и психологическое благополучие. Многочисленные исследования показывают, что эмоциональный интеллект может развиваться на протяжении всей жизни человека.",
        
        # Образование
        "Современные образовательные технологии трансформируют традиционные подходы к обучению, делая его более персонализированным, интерактивным и доступным. Массовые открытые онлайн-курсы, адаптивные обучающие системы, образовательные приложения и игры, виртуальная и дополненная реальность – все эти инструменты расширяют возможности для получения знаний и развития навыков. Интеграция технологий в образовательный процесс требует не только технической инфраструктуры, но и новых педагогических подходов, соответствующих цифровой эпохе.",
        
        "Концепция непрерывного образования предполагает, что обучение является постоянным процессом, продолжающимся на протяжении всей жизни человека. В условиях быстро меняющегося мира, характеризующегося технологическими инновациями и трансформацией рынка труда, способность адаптироваться и приобретать новые знания и навыки становится критически важной. Система непрерывного образования включает формальное, неформальное и информальное обучение и направлена на постоянное повышение профессиональной квалификации и личностное развитие.",
        
        # Архитектура и искусство
        "Барокко – художественный стиль, зародившийся в Италии в конце XVI века и распространившийся по всей Европе. Для барокко характерны пышность, динамика, контрастность, эмоциональная насыщенность и стремление к синтезу различных видов искусства. В архитектуре этого периода преобладают сложные криволинейные формы, богатый декор, игра света и тени. Творчество Джанлоренцо Бернини, Франческо Борромини, Питера Пауля Рубенса и других мастеров барокко оказало огромное влияние на развитие европейского искусства.",
        
        "Импрессионизм – направление в искусстве последней трети XIX века, зародившееся во Франции и оказавшее значительное влияние на дальнейшее развитие мировой живописи. Импрессионисты стремились передать мимолетные впечатления от окружающего мира, изменения света и цвета в природе, движение и атмосферу. Клод Моне, Эдуард Мане, Пьер-Огюст Ренуар, Эдгар Дега и другие художники-импрессионисты разработали новые технические приемы, такие как письмо раздельными мазками, работа на пленэре и использование чистых цветов.",
        
        # Социология
        "Социальное неравенство представляет собой дифференциацию людей по различным критериям, включая доход, образование, профессиональный статус, пол, этническую принадлежность и другие характеристики. Исследования показывают, что высокий уровень социального неравенства связан с различными негативными последствиями, включая ухудшение здоровья населения, снижение социальной мобильности, рост преступности и политическую нестабильность. Разработка эффективных мер по сокращению неравенства является одной из важнейших задач современной социальной политики.",
        
        "Урбанизация – процесс повышения роли городов в развитии общества, характеризующийся ростом городского населения, расширением городских территорий и распространением городского образа жизни. В настоящее время более половины мирового населения проживает в городах, и эта доля продолжает увеличиваться. Современная урбанизация сопровождается такими явлениями, как субурбанизация, джентрификация, формирование городских агломераций и мегаполисов, а также поиск новых моделей устойчивого городского развития.",
        
        # Философия
        "Экзистенциализм – философское направление XX века, исследующее проблему человеческого существования. Согласно экзистенциалистам, человек сам определяет смысл своей жизни через свободный выбор и принятие ответственности за свои действия. Представители этого направления, такие как Жан-Поль Сартр, Альбер Камю, Мартин Хайдеггер и Симона де Бовуар, разрабатывали концепции свободы, подлинности, абсурда, тревоги и отчуждения, которые оказали значительное влияние на философию, литературу и искусство XX века.",
        
        "Этика добродетели, восходящая к работам Аристотеля, фокусируется на развитии моральных качеств и характера человека, а не на правилах или последствиях действий. Согласно этому подходу, правильные поступки – это те, которые совершил бы добродетельный человек в данных обстоятельствах. Современные философы, такие как Аласдер Макинтайр, Филиппа Фут и Марта Нуссбаум, способствовали возрождению интереса к этике добродетели в конце XX века, предлагая альтернативу деонтологическим и утилитаристским теориям морали.",
        
        # Химия и материаловедение
        "Нанотехнология – междисциплинарная область науки и техники, связанная с исследованием и манипулированием материей на атомном и молекулярном уровне. Наноматериалы обладают уникальными физическими, химическими и биологическими свойствами, отличающимися от свойств этих же веществ в макроскопических количествах. Применение нанотехнологий открывает новые возможности в различных областях, включая медицину, электронику, энергетику, охрану окружающей среды и создание новых материалов с заданными свойствами.",
        
        "Органическая химия изучает соединения углерода с другими элементами, прежде всего с водородом, кислородом, азотом, серой и галогенами. Углерод способен образовывать прочные связи с атомами других элементов и с другими атомами углерода, что приводит к огромному многообразию органических соединений. Органическая химия имеет фундаментальное значение для биохимии, фармацевтики, производства полимеров, красителей, пестицидов и многих других материалов, используемых в повседневной жизни.",
        
        # Астрономия и космология
        "Чёрные дыры – области пространства-времени с настолько сильным гравитационным полем, что ничто, даже свет, не может покинуть их пределы. Чёрные дыры могут образовываться в результате гравитационного коллапса массивных звёзд после исчерпания ими ядерного топлива. В центрах большинства галактик, включая наш Млечный Путь, находятся сверхмассивные чёрные дыры, масса которых может превышать массу Солнца в миллионы и миллиарды раз. Изучение чёрных дыр позволяет проверить предсказания общей теории относительности в условиях экстремальных гравитационных полей.",
        
        "Теория Большого взрыва – основная космологическая модель, описывающая раннее развитие Вселенной. Согласно этой теории, примерно 13,8 миллиарда лет назад Вселенная находилась в чрезвычайно горячем и плотном состоянии, а затем начала расширяться. Экспериментальные подтверждения теории Большого взрыва включают наблюдаемое расширение Вселенной, обнаружение космического микроволнового фонового излучения и объяснение распространенности лёгких элементов. Современные исследования направлены на выяснение физических процессов, происходивших в первые мгновения существования Вселенной.",
        
        # Медицина и здоровье
        "Сердечно-сосудистые заболевания являются основной причиной смертности во всем мире. К ним относятся ишемическая болезнь сердца, инсульт, гипертоническая болезнь, пороки сердца и другие патологии сердечно-сосудистой системы. Факторы риска развития сердечно-сосудистых заболеваний включают нездоровое питание, недостаточную физическую активность, употребление табака и алкоголя, а также такие состояния, как гипертония, диабет, ожирение и высокий уровень холестерина. Современные стратегии профилактики и лечения направлены на модификацию образа жизни, контроль факторов риска и внедрение новых медицинских технологий.",
        
        "Иммунная система защищает организм от патогенных микроорганизмов, вирусов, раковых клеток и других потенциально опасных агентов. Она состоит из сложной сети клеток, тканей и органов, работающих вместе для распознавания и уничтожения чужеродных веществ. Врожденный иммунитет обеспечивает быструю, но неспецифическую защиту, тогда как адаптивный иммунитет формирует специфический ответ на конкретные патогены и создает иммунологическую память. Нарушения функции иммунной системы могут приводить к различным заболеваниям, включая аллергии, аутоиммунные заболевания и иммунодефициты.",
        
        # Лингвистика
        "Языковая картина мира представляет собой отражение реальности в языке, особый способ концептуализации действительности, характерный для каждого языка. Она формируется исторически и включает в себя систему ключевых концептов и стереотипов, метафор, образов, оценок, которые фиксируются в лексике, фразеологии, грамматических конструкциях. Изучение языковой картины мира позволяет лучше понять культурные особенности народа, говорящего на данном языке, его мировоззрение, ценности и традиции.",
        
        "Когнитивная лингвистика изучает язык как когнитивный механизм, играющий ключевую роль в концептуализации и категоризации мира, хранении и передаче информации. В отличие от структурной лингвистики, которая рассматривает язык как автономную систему, когнитивная лингвистика исследует связь между языком и другими когнитивными способностями человека, такими как восприятие, внимание, память и мышление. Центральное место в когнитивной лингвистике занимает понятие концепта – ментальной репрезентации, формирующейся в сознании человека.",
        
        # География и геология
        "Тектоника плит – современная геологическая теория, объясняющая движение литосферы Земли. Согласно этой теории, литосфера разделена на относительно целостные плиты, которые движутся по поверхности более пластичной астеносферы. Взаимодействие этих плит приводит к различным геологическим процессам и формированиям, включая землетрясения, вулканическую активность, горообразование, формирование океанических впадин и континентальный дрейф. Теория тектоники плит объединяет и объясняет многие геологические феномены, которые ранее рассматривались как отдельные явления.",
        
        "Изменение климата, вызванное деятельностью человека, представляет собой одну из наиболее серьезных глобальных проблем современности. Увеличение концентрации парниковых газов в атмосфере в результате сжигания ископаемого топлива, обезлесения и других видов антропогенной активности приводит к повышению средней температуры планеты. Последствия изменения климата включают таяние ледников, повышение уровня Мирового океана, увеличение частоты и интенсивности экстремальных погодных явлений, изменение характера осадков, негативное воздействие на биоразнообразие и сельское хозяйство.",
        
        # Юриспруденция и право
        "Международное право представляет собой систему правовых норм, регулирующих отношения между государствами и другими субъектами международного общения. Оно основано на взаимном согласии государств и включает в себя такие отрасли, как право международных договоров, право международных организаций, международное гуманитарное право, международное экономическое право, международное морское право и другие. В отличие от национального права, международное право не имеет единого законодательного органа и централизованного механизма принуждения, что обусловливает особенности его формирования и реализации.",
        
        "Конституционное право изучает основополагающие нормы, определяющие государственное устройство, принципы организации и функционирования государственной власти, взаимоотношения государства и личности. Конституция, являясь основным законом государства, закрепляет фундаментальные права и свободы человека и гражданина, систему органов государственной власти, принципы территориального устройства и другие важнейшие аспекты государственного строя. Конституционный контроль обеспечивает соответствие законов и иных нормативных правовых актов конституции, защищая тем самым верховенство права и конституционный строй.",
        
        # Музыка
        "Симфоническая музыка – один из важнейших жанров европейской классической музыки, развивавшийся с середины XVIII века. Симфония как музыкальная форма обычно состоит из нескольких частей, различающихся по темпу, характеру и тональности, но объединенных общей музыкальной идеей. Творчество таких композиторов, как Йозеф Гайдн, Вольфганг Амадей Моцарт, Людвиг ван Бетховен, Петр Ильич Чайковский, Густав Малер и Дмитрий Шостакович, внесло огромный вклад в развитие симфонической музыки и формирование ее традиций.",
        
        "Джаз возник в начале XX века в афроамериканской среде Нового Орлеана и быстро распространился по всему миру, став одним из влиятельнейших музыкальных направлений. Характерными чертами джаза являются импровизация, сложные ритмические структуры, гармонические эксперименты и особый подход к артикуляции и фразировке. На протяжении своей истории джаз эволюционировал, порождая различные стили и направления, такие как новоорлеанский джаз, свинг, бибоп, кул-джаз, хард-боп, свободный джаз, фьюжн и другие. Джаз оказал значительное влияние на развитие популярной музыки XX века."
    ]
    
    # Add specific examples of non-header text that might be confused with headers
    problematic_normal_text = [
        "Основные результаты исследования представлены в таблице 1.",
        "Результаты проведенного анализа показывают, что предложенный метод эффективен.",
        "Таблица 1. Сравнение результатов различных методов",
        "Рисунок 2. Архитектура предложенной модели",
        "График 1. Динамика изменения параметров",
        "МЕТОДИКА расчета показателей основана на следующих принципах...",
        "Результаты анализа представлены в следующем разделе.",
        "Выводы, полученные в ходе исследования, позволяют утверждать, что...",
        "Дальнейшие исследования в этом направлении помогут расширить понимание изучаемых процессов.",
        "Предварительные результаты показывают перспективность данного подхода.",
        
        # Добавляем текст, который вводит списки
        "Рассмотрим различные типы списков:",
        "В рамках исследования были выделены следующие категории:",
        "Основные подходы к решению данной проблемы включают:",
        "Можно выделить несколько ключевых факторов:",
        "Данный метод имеет следующие преимущества:",
        "Недостатки предложенного подхода заключаются в следующем:",
        "Классификация может быть проведена по нескольким критериям:",
        "Для анализа были отобраны следующие параметры:",
        "Процесс включает в себя несколько этапов:",
        "Существует несколько подходов к классификации систем ИИ:",
        "Основные результаты можно сформулировать следующим образом:",
        "Структура работы представлена следующими разделами:",
        "Рассмотрим основные этапы развития данной технологии:",
        "В ходе исследования были получены следующие результаты:",
        "Метод основан на следующих принципах:",
        "Среди основных концепций выделяются:",
        "Необходимо учитывать следующие особенности:",
        "Приведем примеры использования данного подхода:",
        "Выделим основные характеристики изучаемого объекта:",
        "Перечислим ключевые преимущества данного метода:"
    ]
    
    # Add examples that were incorrectly classified as headers in our test
    more_problematic_texts = [
        "Маркированные списки используются для представления пунктов без определенной последовательности:",
        "В реальных документах часто встречаются смешанные типы списков и библиография.",
        "Смешанные списки могут содержать различные типы маркеров:",
        "Исследование показало, что экспериментальные данные соответствуют теоретическим предсказаниям.",
        "В данной работе представлены результаты анализа влияния различных факторов на эффективность системы.",
        "Методика проведения экспериментов основана на стандартных протоколах и включает следующие этапы.",
        "Применение новых технологий позволило существенно повысить эффективность работы системы.",
        "Результаты исследования могут быть использованы для дальнейшего развития теоретических моделей.",
        "Разработанный метод отличается высокой точностью и надежностью полученных результатов.",
        "Основные принципы работы устройства заключаются в следующем.",
        "Технические характеристики системы соответствуют современным требованиям и стандартам."
    ]
    
    # Generate more medium-length text samples
    all_sentences = []
    for text in normal_text:
        sentences = [s.strip() + '.' for s in text.split('.') if s.strip()]
        all_sentences.extend(sentences)
    
    # Generate more medium-length text samples
    medium_text = []
    for i in range(0, len(all_sentences) - 2, 2):
        combined = all_sentences[i] + ' ' + all_sentences[i+1]
        medium_text.append(combined)
    
    # Add academic paragraph patterns - being selective to avoid overwhelming headers
    academic_intros = [
        "В данной работе рассматривается проблема",
        "Настоящее исследование посвящено вопросу",
        "Актуальность данной темы обусловлена",
        "Целью данной работы является изучение",
        "В рамках настоящего исследования анализируются",
        "Представленные результаты демонстрируют"
    ]
    
    academic_topics = [
        "применения искусственного интеллекта в различных сферах деятельности",
        "совершенствования методов машинного обучения для анализа данных",
        "разработки новых подходов к созданию нейронных сетей",
        "использования глубокого обучения для решения прикладных задач",
        "применения алгоритмов компьютерного зрения в медицинской диагностике",
        "оптимизации алгоритмов обработки естественного языка",
        "внедрения интеллектуальных систем в производственные процессы"
    ]
    
    academic_contexts = [
        "в контексте цифровой трансформации экономики",
        "с учетом современных тенденций развития технологий",
        "при решении задач автоматизации производства",
        "в условиях ограниченных вычислительных ресурсов",
        "для повышения эффективности бизнес-процессов",
        "в рамках четвертой промышленной революции"
    ]
    
    # Combine academic patterns to create more paragraphs
    academic_text = []
    for intro in academic_intros:
        for topic in academic_topics:
            for context in academic_contexts:
                paragraph = f"{intro} {topic} {context}. Проведенный анализ литературы показывает, что данная проблема требует комплексного подхода с учетом множества факторов."
                academic_text.append(paragraph)
    
    # Add specific examples of text with introduction to lists (should be classified as text, not headers)
    list_introduction_text = [
        "Примеры успешного применения ИИ в медицине включают:",
        "Существует несколько подходов к классификации систем ИИ:",
        "Развитие ИИ можно условно разделить на несколько этапов:",
        "Ключевые архитектуры глубоких нейронных сетей включают:",
        "Основные методы искусственного интеллекта состоят из:",
        "К основным типам нейронных сетей относятся:",
        "Преимущества данного подхода включают в себя:",
        "Технология имеет следующие ограничения:",
        "Процесс разработки включает следующие этапы:",
        "Система состоит из следующих компонентов:",
        "Результаты эксперимента показывают:",
        "Основные причины этого явления включают:",
        "Исследователи выделяют следующие проблемы:",
        "К ключевым принципам работы алгоритма относятся:",
        "Применение искусственного интеллекта в данной области имеет следующие особенности:",
        "Можно выделить несколько типов данных:",
        "Параметры модели включают:",
        "Для обучения нейронной сети требуются следующие компоненты:",
        "Архитектура системы включает такие элементы как:",
        "В состав программного комплекса входят:",
        "Существует несколько подходов к решению данной проблемы:",
        "Наиболее эффективные методы включают:",
        "Процесс обработки данных состоит из следующих этапов:",
        "Критерии оценки качества алгоритма таковы:",
        "Факторы, влияющие на точность модели, включают:",
        "В ходе исследования были выявлены следующие закономерности:",
        "Методы оптимизации включают такие подходы как:",
        "Основные компоненты системы представлены ниже:",
        "Технология может быть применена в следующих областях:",
        "В ходе экспериментов были получены следующие результаты:"
    ]
    
    # Add more variations of problematic patterns
    for base in ["включают", "состоят из", "относятся к", "представлены", "являются", "содержат"]:
        list_introduction_text.extend([
            f"Ключевые характеристики системы {base}:",
            f"Основные параметры модели {base}:",
            f"Главные компоненты алгоритма {base}:",
            f"Важные аспекты методологии {base}:"
        ])
    
    # Combine all normal text (including our new examples)
    all_normal_text = normal_text + medium_text + academic_text + all_sentences + problematic_normal_text + list_introduction_text + more_problematic_texts
    
    # Create training data
    texts = headers + list_items + all_normal_text
    
    # Create one-hot encoded labels
    # 0 = HEADER, 1 = LIST, 2 = TEXT
    labels = [[1, 0, 0]] * len(headers) + [[0, 1, 0]] * len(list_items) + [[0, 0, 1]] * len(all_normal_text)
    
    # Calculate ratio of classes
    header_percent = len(headers) / len(texts) * 100
    list_percent = len(list_items) / len(texts) * 100
    text_percent = len(all_normal_text) / len(texts) * 100
    
    print(f"Dataset created with {len(headers)} headers ({header_percent:.1f}%), "
          f"{len(list_items)} list items ({list_percent:.1f}%), and "
          f"{len(all_normal_text)} normal text samples ({text_percent:.1f}%)")
    
    # Aim for approximate ratio of TEXT:LIST:HEADER = 60:25:15
    # If headers are more than 15%, sample them
    if header_percent > 15:
        target_headers = int(len(texts) * 0.15)
        random.shuffle(headers)
        headers = headers[:target_headers]
        print(f"Sampled headers down to {len(headers)} examples")
    
    # If list items are too few (less than 25%), duplicate some
    if list_percent < 25:
        target_lists = int(len(texts) * 0.25)
        additional_lists = random.choices(list_items, k=target_lists - len(list_items))
        list_items.extend(additional_lists)
        print(f"Expanded list items to {len(list_items)} examples")
    
    # Recombine and create updated labels
    texts = headers + list_items + all_normal_text
    labels = [[1, 0, 0]] * len(headers) + [[0, 1, 0]] * len(list_items) + [[0, 0, 1]] * len(all_normal_text)
    
    # Shuffle the data
    combined = list(zip(texts, labels))
    random.shuffle(combined)
    texts, labels = zip(*combined)
    
    final_header_percent = len(headers) / len(texts) * 100
    final_list_percent = len(list_items) / len(texts) * 100
    final_text_percent = len(all_normal_text) / len(texts) * 100
    
    print(f"Final dataset balance: Headers {final_header_percent:.1f}%, Lists {final_list_percent:.1f}%, Text {final_text_percent:.1f}%")
    
    return list(texts), list(labels)

def train_and_save_model(model_path='models/section_classifier.pt'):
    """Train a new model and save it to the specified path."""
    # Generate training data
    texts, labels = generate_training_data()
    
    # Count examples per class
    header_count = sum(label[0] for label in labels)
    list_count = sum(label[1] for label in labels)
    text_count = sum(label[2] for label in labels)
    
    print(f"Training data: {len(texts)} examples ({header_count} headers, {list_count} lists, {text_count} normal text)")
    
    # Create classifier and train
    classifier = TextClassifier()
    
    # Updated training parameters with more epochs for better learning
    results = classifier.train(
        texts, 
        labels, 
        epochs=25,             # More epochs for better learning with new data
        batch_size=16,         # Smaller batch size
        validation_split=0.2
    )
    
    # Save the trained model
    classifier.save_model(model_path)
    print(f"Model trained and saved to {model_path}")
    
    # Test the model on examples to verify performance
    test_on_examples(classifier)
    
    return classifier

def quick_train_and_test():
    """Quickly train and test a model on a small dataset - useful for development."""
    # Get a small subset of the data
    import random
    random.seed(42)
    
    texts, labels = generate_training_data()
    
    # Get all header, list, and normal text samples, but limit sample size
    header_indices = [i for i, label in enumerate(labels) if np.argmax(label) == 0]  # HEADER
    list_indices = [i for i, label in enumerate(labels) if np.argmax(label) == 1]    # LIST
    text_indices = [i for i, label in enumerate(labels) if np.argmax(label) == 2]    # TEXT
    
    # Make sure we don't try to get more samples than available
    header_count = min(len(header_indices), 30)
    list_count = min(len(list_indices), 30)
    text_count = min(len(text_indices), 60)
    
    # Shuffle and take limited samples
    random.shuffle(header_indices)
    random.shuffle(list_indices)
    random.shuffle(text_indices)
    
    sample_indices = header_indices[:header_count] + list_indices[:list_count] + text_indices[:text_count]
    sample_texts = [texts[i] for i in sample_indices]
    sample_labels = [labels[i] for i in sample_indices]
    
    # Count examples per class for display
    header_count = sum(1 for label in sample_labels if np.argmax(label) == 0)
    list_count = sum(1 for label in sample_labels if np.argmax(label) == 1)
    text_count = sum(1 for label in sample_labels if np.argmax(label) == 2)
    
    print(f"Quick train data: {len(sample_texts)} examples ({header_count} headers, {list_count} lists, {text_count} normal text)")
    
    # Create classifier and train quickly
    classifier = TextClassifier()
    results = classifier.train(sample_texts, sample_labels, epochs=5, batch_size=16)
    
    # Test the model
    test_on_examples(classifier)
    
    return classifier

def add_custom_training_data(custom_texts, custom_labels, model_path='models/section_classifier.pt'):
    """Add custom training data and retrain the model."""
    # First try to load existing model
    if os.path.exists(model_path):
        classifier = TextClassifier(model_path)
        print("Loaded existing model for fine-tuning")
    else:
        classifier = TextClassifier()
        print("Creating new model")
    
    # Combine with synthetic data
    texts, labels = generate_training_data()
    all_texts = texts + custom_texts
    all_labels = labels + custom_labels
    
    # Train with combined data
    classifier.train(all_texts, all_labels, epochs=10, batch_size=16)
    
    # Save the retrained model
    classifier.save_model(model_path)
    print(f"Model trained with custom data and saved to {model_path}")
    
    return classifier

def test_on_examples(classifier):
    """Test the classifier on some example text lines."""
    examples = [
        # Clear headers (should be detected as headers)
        "ВВЕДЕНИЕ",
        "ГЛАВА 1. ТЕОРЕТИЧЕСКИЕ ОСНОВЫ",
        "1.1. Определение и классификация",
        "ЗАКЛЮЧЕНИЕ",
        "СПИСОК ИСПОЛЬЗОВАННОЙ ЛИТЕРАТУРЫ",
        
        # List items (should be detected as lists)
        "1. Рассел С., Норвиг П. Искусственный интеллект: современный подход.",
        "- 1950-1960-е годы: зарождение ИИ как научного направления",
        "3) Выбор алгоритмов и создание модели",
        "a) Первый пункт классификации",
        "II. Римская нумерация два",
        
        # Clear normal text (should be detected as text)
        "Искусственный интеллект (ИИ) является одной из самых динамично развивающихся областей компьютерных наук.",
        "Технологии машинного обучения позволяют системам автоматически улучшать свою работу на основе опыта.",
        "В медицине ИИ используется для диагностики заболеваний и разработки новых лекарств.",
        "Результаты исследования показали значительное улучшение точности при использовании нового алгоритма.",
        "Дальнейшие исследования в этом направлении помогут расширить понимание изучаемых процессов.",
        
        # Tricky cases - could be confused
        "Основные результаты",  # Short but not a proper header
        "МЕТОДИКА ЭКСПЕРИМЕНТА",  # All caps like a header
        "Таблица 1. Результаты эксперимента",  # Table reference (should be LIST)
        "- Каждый метод имеет свои преимущества и недостатки", # Could be confused as list but is text
        "2.3 Способы применения искусственного интеллекта"  # Looks like a subsection but missing period
    ]
    
    # Get raw predictions
    raw_predictions = classifier.predict(examples)
    
    # Apply post-processing
    processed_classes = [classifier.post_process_prediction(text, probs) for text, probs in zip(examples, raw_predictions)]
    
    # Convert to class names
    predictions = [classifier.class_names[cls_idx] for cls_idx in processed_classes]
    
    # Expected class indices
    # 0 = HEADER, 1 = LIST, 2 = TEXT
    expected_classes = [
        0, 0, 0, 0, 0,  # Headers
        1, 1, 1, 1, 1,  # Lists
        2, 2, 2, 2, 2,  # Normal text
        2, 0, 1, 2, 0   # Tricky cases
    ]
    
    expected = [classifier.class_names[cls] for cls in expected_classes]
    
    print("\nTest Results:")
    print("=" * 100)
    print(f"{'Text':<50} | {'Prediction':<10} | {'Confidence':<15} | {'Should be'}")
    print("-" * 100)
    
    correct = 0
    for i, (text, pred, pred_probs, exp) in enumerate(zip(examples, predictions, raw_predictions, expected)):
        truncated = text[:45] + "..." if len(text) > 45 else text
        
        # Get confidence and class with highest probability
        best_idx = np.argmax(pred_probs)
        confidence = f"{pred_probs[best_idx]:.4f} ({classifier.class_names[best_idx]})"
        
        is_correct = pred == exp
        correct += is_correct
        
        marker = "✓" if is_correct else "✗"
        print(f"{truncated:<50} | {pred:<10} | {confidence:<15} | {exp} {marker}")
    
    accuracy = correct / len(examples)
    print("-" * 100)
    print(f"Overall accuracy: {accuracy:.2%} ({correct}/{len(examples)})")
    
    # Analyze errors in more detail
    confusion = {}
    for actual_cls in classifier.class_names:
        confusion[actual_cls] = {}
        for pred_cls in classifier.class_names:
            confusion[actual_cls][pred_cls] = 0
    
    for pred, exp in zip(predictions, expected):
        confusion[exp][pred] += 1
    
    print("\nConfusion Matrix:")
    print(f"{'Expected/Predicted':<15} | {'HEADER':<8} | {'LIST':<8} | {'TEXT':<8}")
    print("-" * 50)
    for actual_cls in classifier.class_names:
        row = f"{actual_cls:<15} | "
        for pred_cls in classifier.class_names:
            row += f"{confusion[actual_cls][pred_cls]:<8} | "
        print(row)
    
    # Test document context-aware classification
    print("\nTesting document context-aware classification:")
    print("=" * 100)
    
    # Create test documents with list blocks
    test_document1 = [
        "ГЛАВА 1. ТЕСТИРОВАНИЕ СПИСКОВ",
        "Рассмотрим различные типы списков:",
        "1. Первый пункт",
        "2. Второй пункт",
        "3. Третий пункт",
        "",
        "1.1. Маркированные списки",
        "Маркированные списки используются для перечисления:",
        "- Первый элемент",
        "- Второй элемент",
        "- Третий элемент",
        "",
        "1.2. Смешанные списки",
        "Смешанные списки могут содержать различные типы маркеров:",
        "1. Первый основной пункт",
        "   - Подпункт первого пункта",
        "   - Ещё один подпункт первого пункта",
        "2. Второй основной пункт",
        "   а) Подпункт с буквенной нумерацией",
        "   б) Ещё один подпункт с буквенной нумерацией"
    ]
    
    # Get individual predictions without context
    individual_preds = []
    for line in test_document1:
        probs = classifier.predict([line])[0]
        cls_idx = classifier.post_process_prediction(line, probs)
        individual_preds.append(cls_idx)
    
    # Get context-aware predictions
    context_preds = classifier.predict_document(test_document1)
    
    # Compare results
    print("Document context comparison:\n")
    print(f"{'Line':<45} | {'Without Context':<15} | {'With Context':<15}")
    print("-" * 80)
    
    for i, (line, ind_pred, ctx_pred) in enumerate(zip(test_document1, individual_preds, context_preds)):
        truncated = line[:40] + "..." if len(line) > 40 else line
        ind_class = classifier.class_names[ind_pred]
        ctx_class = classifier.class_names[ctx_pred]
        change = "✓" if ind_pred != ctx_pred else " "
        print(f"{truncated:<45} | {ind_class:<15} | {ctx_class:<15} {change}")

if __name__ == "__main__":
    import sys
    
    # Create models directory if it doesn't exist
    os.makedirs('models', exist_ok=True)
    
    # Check for quick test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("Running quick train and test...")
        classifier = quick_train_and_test()
        sys.exit(0)
    
    # Check for document analysis mode
    if len(sys.argv) > 2 and sys.argv[1] == "--analyze":
        document_path = sys.argv[2]
        if not os.path.exists(document_path):
            print(f"Error: Document '{document_path}' not found")
            sys.exit(1)
            
        print(f"Analyzing document: {document_path}")
        
        # Load the model
        model_path = 'models/section_classifier.pt'
        if not os.path.exists(model_path):
            print("Error: Model not found. Train the model first.")
            sys.exit(1)
            
        classifier = TextClassifier(model_path)
        
        # Read the document
        with open(document_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
            
        # Get individual predictions
        individual_preds = []
        for line in lines:
            if not line:  # Skip empty lines
                individual_preds.append(2)  # Mark as TEXT
                continue
                
            probs = classifier.predict([line])[0]
            cls_idx = classifier.post_process_prediction(line, probs)
            individual_preds.append(cls_idx)
        
        # Get context-aware predictions
        context_preds = classifier.predict_document(lines)
        
        # Output analysis
        print("\nDocument Structure Analysis:")
        print(f"{'Line':<4} | {'Text':<50} | {'Individual':<9} | {'Context':<9}")
        print("-" * 80)
        
        for i, (line, ind_pred, ctx_pred) in enumerate(zip(lines, individual_preds, context_preds)):
            if not line:  # Skip empty lines in output
                continue
                
            truncated = line[:45] + "..." if len(line) > 45 else line
            ind_class = classifier.class_names[ind_pred]
            ctx_class = classifier.class_names[ctx_pred]
            marker = "*" if ind_pred != ctx_pred else " "
            print(f"{i+1:<4} | {truncated:<50} | {ind_class:<9} | {ctx_class:<9} {marker}")
        
        # Summary stats
        ind_headers = individual_preds.count(0)
        ind_lists = individual_preds.count(1)
        ind_texts = individual_preds.count(2)
        
        ctx_headers = context_preds.count(0)
        ctx_lists = context_preds.count(1)
        ctx_texts = context_preds.count(2)
        
        print("\nSummary:")
        print(f"Individual classification: {ind_headers} headers, {ind_lists} list items, {ind_texts} text paragraphs")
        print(f"Context-aware classification: {ctx_headers} headers, {ctx_lists} list items, {ctx_texts} text paragraphs")
        print(f"Changes made: {sum(1 for i, c in zip(individual_preds, context_preds) if i != c)}")
        
        sys.exit(0)
    
    # Regular execution
    model_path = 'models/section_classifier.pt'
    
    if not os.path.exists(model_path):
        print("Training new model...")
        classifier = train_and_save_model(model_path)
    else:
        print(f"Loading existing model from {model_path}...")
        classifier = TextClassifier(model_path)
    
    # Test the model
    test_on_examples(classifier)