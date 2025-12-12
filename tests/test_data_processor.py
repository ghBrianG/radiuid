#!/usr/bin/env python3
"""
Tests for DataProcessor class
"""

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

    def test_munge_match_any(self, data_processor):
        """Test munge with match-any rule (passes all input through)"""
        users = ["testuser123", "admin456"]
        # Munge config uses rule-based format with match/step structure
        munge_config = {
            "rule101": {
                "match": {"any": True},
                "step101.10": {"accept": True}
            }
        }
        result = data_processor.munge(users, munge_config)
        # With match-any and accept, inputs pass through unchanged
        assert "testuser123" in result
        assert "admin456" in result

    def test_munge_discard(self, data_processor):
        """Test munge discard functionality"""
        users = ["testuser", "admin"]
        # Rule that matches 'admin' and discards it
        munge_config = {
            "rule101": {
                "match": {"criterion": "complete", "regex": "admin"},
                "step101.10": {"discard": True}
            },
            "rule102": {
                "match": {"any": True},
                "step102.10": {"accept": True}
            }
        }
        result = data_processor.munge(users, munge_config)
        assert "testuser" in result
        assert "admin" not in result

    def test_munge_set_variable_and_assemble(self, data_processor):
        """Test munge set-variable and assemble functionality"""
        users = ["testuser"]
        # Rule that adds a prefix using variables
        # Note: Step numbers must be unique single numbers for sortlist to work
        # (sortlist uses only the first number found in each string)
        munge_config = {
            "rule101": {
                "match": {"any": True},
                "step10": {
                    "set-variable": "prefix",
                    "from-string": "DOMAIN\\"
                },
                "step20": {
                    "set-variable": "username",
                    "from-match": {}  # Match entire input
                },
                "step30": {
                    "assemble": {
                        "var1": "prefix",
                        "var2": "username"
                    }
                },
                "step40": {"accept": True}
            }
        }
        result = data_processor.munge(users, munge_config)
        assert result[0] == "DOMAIN\\testuser"

    def test_munge_partial_match(self, data_processor):
        """Test munge with partial match criterion"""
        users = ["testuser123", "admin456", "guest"]
        # Rule that matches strings containing digits
        munge_config = {
            "rule101": {
                "match": {"criterion": "partial", "regex": r"\d+"},
                "step101.10": {"accept": True}
            },
            "rule102": {
                "match": {"any": True},
                "step102.10": {"discard": True}
            }
        }
        result = data_processor.munge(users, munge_config)
        # Only users with digits should pass through
        assert "testuser123" in result
        assert "admin456" in result
        assert "guest" not in result


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
        """Test NPS mixed (XML and CSV) format detection"""
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
        """Test that the legacy class name still works"""
        from radiuid import data_processing
        dp = data_processing()
        assert isinstance(dp, DataProcessor)
