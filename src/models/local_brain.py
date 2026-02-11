"""
VigilAI Local Brain - Toxicity Detection using BERT
Uses local model to analyze messages without API costs
"""

from transformers import XLMRobertaTokenizer, AutoModelForSequenceClassification
from scipy.special import expit as sigmoid  # sigmoid function
import numpy as np
import torch

class LocalBrain:
    """
    Local toxicity classifier using multilingual BERT model.
    This runs on CPU and doesn't require external API calls.
    
    The model outputs 6 labels: toxic, severe_toxic, obscene, threat, insult, identity_hate
    Each label is independent (multi-label classification), so we use sigmoid, not softmax.
    """
    
    def __init__(self):
        print("🧠 Initializing Local Brain (BERT)...")
        model_name = "unitary/multilingual-toxic-xlm-roberta"
        
        try:
            # Load tokenizer and model
            # These will be cached after first download (~1GB)
            # Using XLMRobertaTokenizer directly to avoid AutoTokenizer issues
            self.tokenizer = XLMRobertaTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()  # Set to evaluation mode
            print("✅ Local Brain ready!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def analyze(self, text: str) -> float:
        """
        Analyze text for toxicity.
        
        Args:
            text: The message to analyze
            
        Returns:
            float: Toxicity probability (0.0 to 1.0)
                   Higher = more toxic
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            # Get model predictions (no gradient needed for inference)
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Convert logits to probabilities using SIGMOID (multi-label classification)
            # Each label is independent: toxic, severe_toxic, obscene, threat, insult, identity_hate
            probs = sigmoid(outputs.logits.numpy()[0])
            
            # Return maximum toxicity probability across all labels
            max_prob = float(np.max(probs))
            
            return max_prob
            
        except Exception as e:
            print(f"⚠️ Error analyzing text: {e}")
            # Return safe value on error
            return 0.0
    
    def is_toxic(self, text: str, threshold: float = 0.90) -> tuple[bool, float]:
        """
        Check if text is toxic above threshold.
        
        Args:
            text: The message to check
            threshold: Toxicity threshold (default 0.90)
            
        Returns:
            tuple: (is_toxic: bool, score: float)
        """
        score = self.analyze(text)
        return (score >= threshold, score)
