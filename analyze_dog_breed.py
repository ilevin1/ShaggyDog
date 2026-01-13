from openai import OpenAI
import os
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_dog_breed(image_path):
    """
    Analyze an image to determine which dog breed the person most closely resembles.
    """
    try:
        # Read and encode the image
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Use Responses API to analyze the image
        response = client.responses.create(
            model="gpt-5-mini-2025-08-07",
            input=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Analyze this human face and determine which specific dog breed this person's facial features, structure, and overall appearance most closely resembles. Consider factors like face shape, eye shape, nose structure, ear position, and overall facial proportions. Respond with just the dog breed name and a brief one-sentence explanation of why."
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    },
                ],
            }],
        )
        
        return response.output_text
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    image_path = "Obama.jpeg"
    
    print(f"Analyzing {image_path}...")
    print("\n" + "="*50)
    
    dog_breed = analyze_dog_breed(image_path)
    
    print("\nDog Breed Analysis:")
    print("-" * 50)
    print(dog_breed)
    print("="*50)

