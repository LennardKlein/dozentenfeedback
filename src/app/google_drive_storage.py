"""
Google Drive Storage Module for PDF Reports
"""

import os
import json
import io
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime


class GoogleDriveStorage:
    """Handle Google Drive storage for PDF reports"""
    
    def __init__(self, credentials_json: Optional[str] = None, folder_id: Optional[str] = None):
        """
        Initialize Google Drive storage
        
        Args:
            credentials_json: JSON string with service account credentials
            folder_id: Google Drive folder ID where files will be stored
        """
        self.folder_id = folder_id or os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        
        # Get credentials from parameter or environment
        creds_json = credentials_json or os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
        
        if not creds_json:
            raise ValueError("Google Drive credentials not provided")
        
        # Parse credentials
        if isinstance(creds_json, str):
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = creds_json
        
        # Create credentials object
        self.credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        # Build Drive service
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def upload_pdf(self, pdf_bytes: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Upload PDF to Google Drive
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Name for the file
            metadata: Optional metadata for the file
            
        Returns:
            Dict with file_id and web_view_link
        """
        # Prepare file metadata
        file_metadata = {
            'name': filename,
            'mimeType': 'application/pdf'
        }
        
        # Add to specific folder if configured
        if self.folder_id:
            file_metadata['parents'] = [self.folder_id]
        
        # Add custom properties if metadata provided
        if metadata:
            file_metadata['properties'] = {
                'topic': metadata.get('topic', ''),
                'host_email': metadata.get('host_email', ''),
                'duration': metadata.get('duration', ''),
                'score': str(metadata.get('score', '')),
                'processed_date': datetime.now().isoformat()
            }
        
        # Create media upload
        media = MediaIoBaseUpload(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            resumable=True
        )
        
        # Upload file
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink,webContentLink'
        ).execute()
        
        # Make file shareable (optional - can be configured)
        self._set_file_permissions(file['id'])
        
        return {
            'file_id': file['id'],
            'web_view_link': file.get('webViewLink'),
            'download_link': file.get('webContentLink')
        }
    
    def _set_file_permissions(self, file_id: str):
        """
        Set file permissions (make readable by anyone with link)
        
        Args:
            file_id: Google Drive file ID
        """
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
        except Exception as e:
            print(f"Warning: Could not set file permissions: {e}")
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive
        
        Args:
            folder_name: Name for the new folder
            parent_id: Optional parent folder ID
            
        Returns:
            Folder ID
        """
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        elif self.folder_id:
            file_metadata['parents'] = [self.folder_id]
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        return folder['id']
    
    def generate_filename(self, metadata: Dict[str, Any]) -> str:
        """
        Generate a structured filename based on metadata
        
        Args:
            metadata: Recording metadata
            
        Returns:
            Formatted filename
        """
        # Get components
        date = datetime.now().strftime('%Y%m%d')
        time = datetime.now().strftime('%H%M')
        topic = metadata.get('topic', 'Unknown').replace('/', '-').replace(' ', '_')[:50]
        host = metadata.get('host_email', 'unknown').split('@')[0]
        
        # Create filename
        filename = f"DozentenFeedback_{date}_{time}_{host}_{topic}.pdf"
        
        # Clean filename (remove any problematic characters)
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        return filename
    
    def organize_by_date(self, metadata: Dict[str, Any]) -> str:
        """
        Create date-based folder structure
        
        Args:
            metadata: Recording metadata
            
        Returns:
            Folder ID for today's folder
        """
        # Create year folder
        year = datetime.now().strftime('%Y')
        year_folder = self._get_or_create_folder(year)
        
        # Create month folder
        month = datetime.now().strftime('%m-%B')
        month_folder = self._get_or_create_folder(month, parent_id=year_folder)
        
        # Create day folder
        day = datetime.now().strftime('%d')
        day_folder = self._get_or_create_folder(f"Tag_{day}", parent_id=month_folder)
        
        return day_folder
    
    def _get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Get existing folder or create if not exists
        
        Args:
            folder_name: Name of the folder
            parent_id: Optional parent folder ID
            
        Returns:
            Folder ID
        """
        # Build query
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        
        if parent_id:
            query += f" and '{parent_id}' in parents"
        elif self.folder_id:
            query += f" and '{self.folder_id}' in parents"
        
        # Search for existing folder
        results = self.service.files().list(
            q=query,
            fields='files(id)'
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        else:
            return self.create_folder(folder_name, parent_id)