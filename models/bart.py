
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Load tokenizer and model for summarization
model_name = "facebook/bart-large-cnn"  # Example model with large sequence length
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def summarize(text, max_output_length=150, min_output_length=30):
    """
    Summarizes the provided text using a pre-trained BART model.

    Args:
    text (str): The text to be summarized.
    max_output_length (int): The maximum length of the summary output in tokens.
    min_output_length (int): The minimum length of the summary output in tokens.

    Returns:
    str: The summarized text.
    """
    
    if not text: 
        return ''

    # Tokenize and truncate input text
    inputs = tokenizer(text, max_length=1024, truncation=True, return_tensors="pt")

    # Generate summary
    summary_ids = model.generate(inputs["input_ids"], max_length=max_output_length, min_length=min_output_length, num_beams=2, early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return summary
