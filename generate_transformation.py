from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import re

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
        raise Exception(f"Error analyzing dog breed: {str(e)}")

def extract_dog_breed(breed_description):
    """
    Extract the dog breed name from the analysis text.
    """
    # Try to extract the breed name (usually the first few words before a period or comma)
    # Common pattern: "Labrador Retriever" or "Golden Retriever" etc.
    # Take first 2-3 words as breed name
    words = breed_description.split()
    if len(words) >= 2:
        # Check if it's a compound breed name (like "Golden Retriever", "German Shepherd")
        if words[1][0].isupper() or len(words) == 2:
            return f"{words[0]} {words[1]}"
    return words[0] if words else "dog"

def generate_progressive_images(image_path, dog_breed, output_dir=None):
    """
    Generate 3 progressive images transforming from human to dog.
    Each image gets closer to the final dog form.
    
    Args:
        image_path: Path to the input image
        dog_breed: Dog breed name
        output_dir: Optional directory to save images (defaults to current directory)
    
    Returns:
        List of tuples: [(filename1, base64_data1), (filename2, base64_data2), (filename3, base64_data3)]
    """
    # Read and encode the original image
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    
    generated_images = []
    
    # Image 1: Slight transformation - subtle dog-like features
    print("\nGenerating image 1/3: Subtle transformation...")
    prompt1 = f"Transform this person's face to have very subtle {dog_breed} dog-like features - slightly more pronounced nose, subtle changes around the eyes and mouth, but maintain the human appearance overall. Keep the same pose, expression, and lighting."
    
    try:
        response1 = client.responses.create(
            model="gpt-5",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt1},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    },
                ],
            }],
            tools=[{"type": "image_generation", "action": "auto", "input_fidelity": "high"}],
        )
    except Exception as e:
        print(f"Error in API call for image 1: {str(e)}")
        raise
    
    # Extract image 1
    image1_data = [
        output.result
        for output in response1.output
        if hasattr(output, 'type') and output.type == "image_generation_call" and hasattr(output, 'result')
    ]
    
    if not image1_data:
        raise Exception("Failed to generate image 1")
    
    image1_base64 = image1_data[0]
    generated_images.append(("image1_transition.png", image1_base64))
    print("✓ Image 1 generated")
    
    # Image 2: Medium transformation - halfway between human and dog
    print("Generating image 2/3: Medium transformation...")
    prompt2 = f"Transform this image to be halfway between human and {dog_breed} dog - blend human and canine features more prominently. The face should show clear dog characteristics while maintaining some human-like structure. Keep the same pose and composition."
    
    response2 = client.responses.create(
        model="gpt-5",
        previous_response_id=response1.id,
        input=prompt2,
        tools=[{"type": "image_generation", "action": "edit", "input_fidelity": "high"}],
    )
    
    # Extract image 2
    image2_data = [
        output.result
        for output in response2.output
        if hasattr(output, 'type') and output.type == "image_generation_call" and hasattr(output, 'result')
    ]
    
    if not image2_data:
        raise Exception("Failed to generate image 2")
    
    image2_base64 = image2_data[0]
    generated_images.append(("image2_transition.png", image2_base64))
    print("✓ Image 2 generated")
    
    # Image 3: Final transformation - full dog form
    print("Generating image 3/3: Final dog transformation...")
    prompt3 = f"Transform this into a realistic {dog_breed} dog portrait that maintains the same pose, expression, and composition as the original person. The dog should have the same general facial structure and expression, but as a fully formed {dog_breed} dog."
    
    try:
        response3 = client.responses.create(
            model="gpt-5",
            previous_response_id=response2.id,
            input=prompt3,
            tools=[{"type": "image_generation", "action": "edit", "input_fidelity": "high"}],
        )
    except Exception as e:
        print(f"[DEBUG] Error in API call for image 3: {str(e)}")
        raise
    
    # Debug: Check response structure
    if hasattr(response3, 'output'):
        print(f"[DEBUG] Response3.output length: {len(response3.output) if hasattr(response3.output, '__len__') else 'N/A'}")
        for i, output in enumerate(response3.output):
            if hasattr(output, 'type'):
                print(f"[DEBUG] Output {i} type: {output.type}")
                if output.type == "image_generation_call" and hasattr(output, 'result'):
                    print(f"[DEBUG] Output {i} has result: {bool(output.result)}")
    
    # Extract image 3
    image3_data = [
        output.result
        for output in response3.output
        if hasattr(output, 'type') and output.type == "image_generation_call" and hasattr(output, 'result')
    ]
    
    if not image3_data:
        print(f"[DEBUG] No image_generation_call found for image 3. Available outputs:")
        for output in response3.output:
            print(f"  - {output}")
        raise Exception("Failed to generate image 3")
    
    image3_base64 = image3_data[0]
    generated_images.append(("image3_final_dog.png", image3_base64))
    print("✓ Image 3 generated")
    
    # Save all images
    if output_dir:
        import os
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nSaving images to {output_dir}...")
        saved_paths = []
        for filename, image_base64 in generated_images:
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_base64))
            saved_paths.append((filepath, image_base64))
            print(f"  Saved: {filepath}")
        return saved_paths
    else:
        print("\nSaving images...")
        for filename, image_base64 in generated_images:
            with open(filename, "wb") as f:
                f.write(base64.b64decode(image_base64))
            print(f"  Saved: {filename}")
        return generated_images

def main(image_path):
    """
    Main function that analyzes the breed and generates progressive images.
    """
    print("="*60)
    print("Shaggy Dog Transformation Generator")
    print("="*60)
    
    # Step 1: Analyze dog breed
    print(f"\nStep 1: Analyzing {image_path}...")
    breed_description = analyze_dog_breed(image_path)
    print("\nDog Breed Analysis:")
    print("-" * 60)
    print(breed_description)
    print("-" * 60)
    
    # Extract dog breed name
    dog_breed = extract_dog_breed(breed_description)
    print(f"\nExtracted breed: {dog_breed}")
    
    # Step 2: Generate progressive images
    print(f"\nStep 2: Generating 3 progressive transformation images...")
    print("="*60)
    
    try:
        images = generate_progressive_images(image_path, dog_breed)
        print("\n" + "="*60)
        print("SUCCESS! All images generated successfully!")
        print(f"Generated {len(images)} images:")
        for filename, _ in images:
            print(f"  - {filename}")
        print("="*60)
        return images
    except Exception as e:
        print(f"\nERROR: Failed to generate images: {str(e)}")
        raise

if __name__ == "__main__":
    image_path = "Obama.jpeg"
    main(image_path)

