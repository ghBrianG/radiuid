#!/usr/bin/env python3
"""
Tests for DataProcessor class
"""

import pytest
import os
from radiuid.core.data_processor import DataProcessor


class TestDataProcessor:
    """Test cases for DataProcessor class"""

    def test_clean_ips(self, data_processor):
        """Test IP address extraction and cleaning"""
        test_dict = {
            "entry1": "192.168.1.100",
            "entry2": "10.0.0.1",
            "entry3": "invalid",
            "entry4": "256.256.256.256",  # Invalid IP
        }
        cleaned = data_processor.clean_ips(test_dict)
        assert "192.168.1.100" in str(cleaned.values())
        assert "10.0.0.1" in str(cleaned.values())

    def test_munge_regex(self, data_processor):
        """Test munge regex functionality"""
        users = ["testuser123", "admin456"]
        munge_config = {
            "regex": {r"\d+": ""}  # Remove numbers
        }
        result = data_processor.munge(users, munge_config)
        assert "testuser" in result
        assert "admin" in result

    def test_munge_prefix(self, data_processor):
        """Test munge prefix functionality"""
        users = ["testuser"]
        munge_config = {
            "prefix": {"value": "DOMAIN\\"}
        }
        result = data_processor.munge(users, munge_config)
        assert result[0] == "DOMAIN\\testuser"

    def test_munge_suffix(self, data_processor):
        """Test munge suffix functionality"""
        users = ["testuser"]
        munge_config = {
            "suffix": {"value": "@domain.com"}
        }
        result = data_processor.munge(users, munge_config)
        assert result[0] == "testuser@domain.com"

    def test_munge_lowercase(self, data_processor):
        """Test munge lowercase functionality"""
        users = ["TESTUSER", "Admin"]
        munge_config = {
            "lowercase": {}
        }
        result = data_processor.munge(users, munge_config)
        assert result[0] == "testuser"
        assert result[1] == "admin"

    def test_munge_uppercase(self, data_processor):
        """Test munge uppercase functionality"""
        users = ["testuser", "Admin"]
        munge_config = {
            "uppercase": {}
        }
        result = data_processor.munge(users, munge_config)
        assert result[0] == "TESTUSER"
        assert result[1] == "ADMIN"


class TestLogFormatDetection:
    """Test log format detection"""

    def test_detect_freeradius_format(self, data_processor, sample_radius_log):
        """Test FreeRADIUS format detection"""
        format_type = data_processor.detect_log_format(sample_radius_log)
        assert format_type == "freeradius"

    def test_detect_nps_csv_format(self, data_processor, sample_nps_csv_log):
        """Test NPS CSV format detection"""
        format_type = data_processor.detect_log_format(sample_nps_csv_log)
        assert format_type == "nps_csv"

    def test_detect_nps_mixed_format(self, data_processor, sample_nps_mixed_log):
        """Test NPS mixed (XML + CSV) format detection"""
        format_type = data_processor.detect_log_format(sample_nps_mixed_log)
        assert format_type == "nps_csv"


class TestLogParsing:
    """Test log file parsing"""

    def test_parse_nps_csv(self, data_processor, sample_nps_csv_log):
        """Test NPS CSV parsing"""
        result = data_processor.parse_nps_csv([sample_nps_csv_log])
        assert len(result) == 3
        assert "10.1.75.8" in result
        assert result["10.1.75.8"]["username"] == "testuser"

    def test_parse_nps_csv_domain_user(self, data_processor, sample_nps_csv_log):
        """Test NPS CSV parsing with domain\\user format"""
        result = data_processor.parse_nps_csv([sample_nps_csv_log])
        # domain\\jsmith should become just jsmith
        assert "192.168.1.50" in result
        assert result["192.168.1.50"]["username"] == "jsmith"

    def test_parse_nps_mixed_skips_xml(self, data_processor, sample_nps_mixed_log):
        """Test that NPS parser skips XML lines"""
        result = data_processor.parse_nps_csv([sample_nps_mixed_log])
        assert len(result) == 2  # Only CSV lines parsed

    def test_parse_log_files_auto_detect(self, data_processor, sample_nps_csv_log):
        """Test unified parse_log_files with auto-detection"""
        result = data_processor.parse_log_files([sample_nps_csv_log])
        assert len(result) > 0


class TestDataProcessorLegacyAlias:
    """Test legacy alias compatibility"""

    def test_legacy_import(self):
        """Test that legacy class name still works"""
        from radiuid import data_processing
        dp = data_processing()
        assert isinstance(dp, DataProcessor)
