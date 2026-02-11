from dotenv import load_dotenv 
import os

load_dotenv() # This loads variables from .env into os.environ 

bucket_name = os.getenv("BUCKET") 

print(f"Bucket name is: {bucket_name}")

# read the CE_DATA environment variable, which contains the event data from the COS trigger
event_data = os.getenv("CE_DATA")

print(f"Event data is: {event_data}")


