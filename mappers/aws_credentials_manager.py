import configparser
import os
from pathlib import Path
from typing import Optional, Dict, Tuple
import boto3

class AWSCredentialsManager:
    def __init__(self):
        self.credentials_path = os.path.expanduser("~/.aws/credentials")
        self.config_path = os.path.expanduser("~/.aws/config")
    
    def get_profile_credentials(self, profile_name: str = 'default') -> Optional[Dict[str, str]]:
        """
        Get AWS credentials from a profile in ~/.aws/credentials and ~/.aws/config
        
        Args:
            profile_name (str): The name of the AWS profile to use
            
        Returns:
            Optional[Dict[str, str]]: Dictionary containing aws_access_key, aws_secret_key, and aws_region
                                    Returns None if profile not found or invalid
        """
        try:
            # Read credentials file
            credentials = configparser.ConfigParser()
            credentials.read(self.credentials_path)
            
            # Read config file for region
            config = configparser.ConfigParser()
            config.read(self.config_path)
            
            # Handle 'default' profile name special case
            profile_section = profile_name
            if profile_name != 'default':
                profile_section = f"profile {profile_name}"
            
            # Get credentials
            if profile_name not in credentials.sections():
                raise ValueError(f"Profile '{profile_name}' not found in AWS credentials")
                
            aws_access_key = credentials[profile_name]['aws_access_key_id']
            aws_secret_key = credentials[profile_name]['aws_secret_access_key']
            
            # Try to get region from config file
            aws_region = None
            if config.has_section(profile_section):
                aws_region = config[profile_section].get('region')
            
            # If region not found in config, try credentials file
            if not aws_region and profile_name in credentials.sections():
                aws_region = credentials[profile_name].get('region')
            
            # If still no region, use default
            if not aws_region:
                aws_region = 'us-east-1'
                
            return {
                'aws_access_key': aws_access_key,
                'aws_secret_key': aws_secret_key,
                'aws_region': aws_region
            }
            
        except Exception as e:
            raise ValueError(f"Error reading AWS profile '{profile_name}': {str(e)}")
    
    def validate_credentials(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """
        Validate AWS credentials by trying to make a simple AWS API call
        
        Args:
            credentials (Dict[str, str]): Dictionary containing aws_access_key, aws_secret_key, and aws_region
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            session = boto3.Session(
                aws_access_key_id=credentials['aws_access_key'],
                aws_secret_access_key=credentials['aws_secret_key'],
                region_name=credentials['aws_region']
            )
            
            # Try to make a simple API call
            sts = session.client('sts')
            sts.get_caller_identity()
            
            return True, "Credentials are valid"
        except Exception as e:
            return False, f"Invalid credentials: {str(e)}"
    
    def list_profiles(self) -> list:
        """
        List all available AWS profiles
        
        Returns:
            list: List of profile names
        """
        credentials = configparser.ConfigParser()
        credentials.read(self.credentials_path)
        return credentials.sections()