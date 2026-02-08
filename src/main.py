from dotenv import load_dotenv 
import os 

load_dotenv() # This loads variables from .env into os.environ 

bucket_name = os.getenv("BUCKET") 

print(f"Bucket name is: {bucket_name}")