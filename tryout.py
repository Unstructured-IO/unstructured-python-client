import os
import json
import logging
from datetime import datetime
import unstructured_client
from unstructured_client.models import shared, operations

# Set up verbose logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("unstructured-client")
logger.setLevel(logging.INFO)

def run_partition_with_hook(pdf_path: str):
    api_url = os.getenv("URL", None)
    api_key = os.getenv("KEY", None)

    client = unstructured_client.UnstructuredClient(
        server_url=api_url,
        api_key_auth=api_key,
    )
    
    with open(pdf_path, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=pdf_path,
        )

    partition_parameters = shared.PartitionParameters(
        files=files,
        strategy="hi_res",
        # This is the crucial parameter that activates the hook's logic
        split_pdf_page=True, 
    )

    request = operations.PartitionRequest(
        partition_parameters=partition_parameters
    )

    resp = client.general.partition(request=request)
    
    print("\n--- Partitioning Response ---")
    if resp.elements:
        print(f"Successfully partitioned document into {len(resp.elements)} elements.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"response_{timestamp}.json"
        elements_data = [element for element in resp.elements]

        with open(filename, 'w') as f:
            json.dump(elements_data, f, indent=2)
        print(f"✅ Saved to: {filename}")

    else:
        print("Partitioning call completed, but no elements were returned.")

if __name__ == "__main__":
    test_filename = "input.pdf"
    
    if os.path.exists(test_filename):
        # Run the test
        run_partition_with_hook(test_filename)
    else:
        print(f"Error: The file '{test_filename}' was not found.")
