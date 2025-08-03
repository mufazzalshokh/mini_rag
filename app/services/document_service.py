from fastapi import UploadFile
from typing import List
import os

class DocumentService:

    def ingest_files(self, files: List[UploadFile]):
        # Already implemented by you – good!
        ...

    def ingest_local_docs(self, folder_path: str):
        files = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                files.append(open(file_path, "rb"))

        # Convert to UploadFile-like objects or use your internal chunking logic here
        # You might need to refactor chunking into a shared method

        # For now, return dummy response:
        return {
            "docs": len(files),
            "chunks": 0,  # update when you implement it
            "est_tokens": 0
        }
