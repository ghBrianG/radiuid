#!/usr/bin/env python3
"""
Tests for FileManager class
"""

import pytest
import os
from radiuid.core.file_manager import FileManager


class TestFileManagerValidation:
    """Test validation methods"""

    def test_validate_ip_valid_ipv4(self, file_manager):
        """Test valid IPv4 address validation"""
        assert file_manager.validate_ip("address", "192.168.1.1") is True
        assert file_manager.validate_ip("address", "10.0.0.1") is True
        assert file_manager.validate_ip("address", "255.255.255.255") is True

    def test_validate_ip_invalid_ipv4(self, file_manager):
        """Test invalid IPv4 address validation"""
        assert file_manager.validate_ip("address", "256.1.1.1") is False
        assert file_manager.validate_ip("address", "192.168.1") is False
        assert file_manager.validate_ip("address", "not.an.ip") is False
        assert file_manager.validate_ip("address", "") is False

    def test_validate_ip_cidr(self, file_manager):
        """Test IPv4 CIDR notation validation"""
        assert file_manager.validate_ip("block", "192.168.1.0/24") is True
        assert file_manager.validate_ip("block", "10.0.0.0/8") is True
        assert file_manager.validate_ip("block", "192.168.1.1/32") is True

    def test_validate_ip_invalid_cidr(self, file_manager):
        """Test invalid CIDR notation"""
        assert file_manager.validate_ip("block", "192.168.1.0/33") is False
        assert file_manager.validate_ip("block", "192.168.1.0/-1") is False

    def test_validate_domain_name_valid(self):
        """Test valid domain name validation"""
        result = FileManager.validate_domain_name("example.com")
        assert result["status"] == "pass"

        result = FileManager.validate_domain_name("sub.example.com")
        assert result["status"] == "pass"

        result = FileManager.validate_domain_name("my-domain.com")
        assert result["status"] == "pass"

        # Underscores allowed for AD domains
        result = FileManager.validate_domain_name("my_domain")
        assert result["status"] == "pass"

    def test_validate_domain_name_invalid(self):
        """Test invalid domain name validation"""
        # Invalid characters
        result = FileManager.validate_domain_name("domain!.com")
        assert result["status"] == "fail"

        # Double periods
        result = FileManager.validate_domain_name("domain..com")
        assert result["status"] == "fail"

        # Starts with hyphen
        result = FileManager.validate_domain_name("-domain.com")
        assert result["status"] == "fail"

    def test_validate_username_valid(self):
        """Test valid username validation"""
        result = FileManager.validate_username("testuser")
        assert result["status"] == "pass"

        result = FileManager.validate_username("test_user")
        assert result["status"] == "pass"

        result = FileManager.validate_username("test.user")
        assert result["status"] == "pass"

        result = FileManager.validate_username("user123")
        assert result["status"] == "pass"

    def test_validate_username_invalid(self):
        """Test invalid username validation"""
        result = FileManager.validate_username("user@domain")
        assert result["status"] == "fail"

        result = FileManager.validate_username("user name")
        assert result["status"] == "fail"


class TestFileManagerFileOperations:
    """Test file operations"""

    def test_list_files(self, file_manager, temp_dir):
        """Test listing files in directory"""
        # Create some test files
        for i in range(3):
            filepath = os.path.join(temp_dir, f"test{i}.log")
            with open(filepath, 'w') as f:
                f.write(f"content {i}")

        files = file_manager.list_files(temp_dir)
        assert len(files) == 3

    def test_list_files_empty_dir(self, file_manager, temp_dir):
        """Test listing files in empty directory"""
        files = file_manager.list_files(temp_dir)
        assert len(files) == 0

    def test_write_file(self, file_manager, temp_dir):
        """Test writing file"""
        filepath = os.path.join(temp_dir, "test.txt")
        file_manager.write_file(filepath, "test content")

        assert os.path.exists(filepath)
        with open(filepath, 'r') as f:
            assert f.read() == "test content"

    def test_file_exists(self, file_manager, temp_dir):
        """Test file existence check"""
        filepath = os.path.join(temp_dir, "exists.txt")

        assert file_manager.file_exists(filepath) is False

        with open(filepath, 'w') as f:
            f.write("test")

        assert file_manager.file_exists(filepath) is True

    def test_remove_files(self, file_manager, temp_dir):
        """Test removing files"""
        # Create test files
        files = []
        for i in range(2):
            filepath = os.path.join(temp_dir, f"remove{i}.txt")
            with open(filepath, 'w') as f:
                f.write("test")
            files.append(filepath)

        # Verify files exist
        for f in files:
            assert os.path.exists(f)

        # Remove files
        file_manager.remove_files(files)

        # Verify files are gone
        for f in files:
            assert not os.path.exists(f)

    def test_remove_files_nonexistent(self, file_manager, temp_dir):
        """Test removing nonexistent files doesn't raise error"""
        files = [os.path.join(temp_dir, "nonexistent.txt")]
        # Should not raise an exception
        file_manager.remove_files(files)


class TestFileManagerPathUtilities:
    """Test path utility methods"""

    def test_strip_filepath(self, file_manager):
        """Test extracting directory and filename from path"""
        directory, filename = file_manager.strip_filepath("/var/log/test.log")
        assert directory == "/var/log/"
        assert filename == "test.log"

    def test_strip_filepath_no_directory(self, file_manager):
        """Test strip_filepath with no directory"""
        directory, filename = file_manager.strip_filepath("test.log")
        assert filename == "test.log"

    def test_directory_slash_add(self, file_manager):
        """Test adding trailing slash to directory"""
        assert file_manager.directory_slash_add("/var/log") == "/var/log/"
        assert file_manager.directory_slash_add("/var/log/") == "/var/log/"


class TestLiveLogProcessing:
    """Test live log file processing"""

    def test_process_live_log_disabled(self, file_manager, app_context):
        """Test that live log returns None when disabled"""
        app_context.config.live_log_enabled = False
        result = file_manager.process_live_log()
        assert result is None

    def test_process_live_log_no_file(self, file_manager, app_context, temp_dir):
        """Test live log with nonexistent file"""
        app_context.config.live_log_enabled = True
        app_context.config.live_log_file = os.path.join(temp_dir, "nonexistent.log")
        app_context.config.live_log_tracker = os.path.join(temp_dir, "tracker")
        app_context.config.radius_log_path = temp_dir

        result = file_manager.process_live_log()
        assert result is None

    def test_process_live_log_extracts_content(self, file_manager, app_context, temp_dir):
        """Test live log extraction"""
        live_log = os.path.join(temp_dir, "live.log")
        tracker = os.path.join(temp_dir, "tracker")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir)

        # Create live log file
        with open(live_log, 'w') as f:
            f.write("10.1.1.1,user1,12/10/2025,10:00:00,IAS,NPS,4\n")

        app_context.config.live_log_enabled = True
        app_context.config.live_log_file = live_log
        app_context.config.live_log_tracker = tracker
        app_context.config.radius_log_path = output_dir

        result = file_manager.process_live_log()

        # Should return path to extracted file
        assert result is not None
        assert os.path.exists(result)

        # Tracker should be created
        assert os.path.exists(tracker)
