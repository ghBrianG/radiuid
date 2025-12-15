#!/usr/bin/env python3
"""
Tests for PaloAltoFirewall class
"""

from radiuid.firewall.palo_alto import PaloAltoFirewall


class TestPaloAltoFirewall:
    """Test cases for PaloAltoFirewall class"""

    def test_xml_formatter(self, firewall, sample_mappings, sample_targets):
        """Test XML formatting for User-ID API"""
        xml_dict = firewall.xml_formatter_v67(
            sample_mappings,
            sample_targets,
            timeout=60
        )
        assert len(xml_dict) > 0
        # Check that targets are in the result
        for target in sample_targets:
            key = f"{target['hostname']}:vsys{target['vsys']}"
            assert key in xml_dict

    def test_xml_formatter_login_entries(self, firewall, sample_targets):
        """Test XML contains login entries for start status"""
        mappings = {
            "192.168.1.100": {"username": "user1", "status": "start"}
        }
        xml_dict = firewall.xml_formatter_v67(mappings, sample_targets, timeout=60)

        # Get first target's XML
        first_key = list(xml_dict.keys())[0]
        xml_entries = xml_dict[first_key]

        # Should contain login entry
        xml_content = "".join(xml_entries)
        assert "<login>" in xml_content or "<entry" in xml_content

    def test_xml_formatter_stop_status(self, firewall, sample_targets):
        """Test XML formatting for stop status entries (same format as start)"""
        mappings = {
            "10.0.0.50": {"username": "admin", "status": "stop"}
        }
        xml_dict = firewall.xml_formatter_v67(mappings, sample_targets, timeout=60)

        first_key = list(xml_dict.keys())[0]
        xml_entries = xml_dict[first_key]
        xml_content = "".join(xml_entries)

        # The formatter creates entry elements regardless of status
        # Status handling is done at the push_uids level, not in XML formatting
        assert "<entry" in xml_content
        assert "admin" in xml_content
        assert "10.0.0.50" in xml_content

    def test_xml_formatter_with_domain(self, firewall, sample_targets):
        """Test XML formatting includes domain prefix"""
        mappings = {
            "192.168.1.100": {"username": "user1", "status": "start"}
        }
        xml_dict = firewall.xml_formatter_v67(
            mappings,
            sample_targets,
            timeout=60,
            userdomain="TESTDOMAIN"
        )

        first_key = list(xml_dict.keys())[0]
        xml_content = "".join(xml_dict[first_key])
        assert "TESTDOMAIN" in xml_content

    def test_xml_assembler(self, firewall, sample_mappings, sample_targets):
        """Test URL assembly for API calls"""
        xml_dict = firewall.xml_formatter_v67(
            sample_mappings,
            sample_targets,
            timeout=60
        )
        # xml_assembler_v67 returns a tuple of (url_dict, xml_dict)
        url_dict, assembled_xml_dict = firewall.xml_assembler_v67(xml_dict, sample_targets)

        assert len(url_dict) > 0
        for target_key, urls in url_dict.items():
            assert len(urls) > 0
            for url in urls:
                assert "https://" in url or "http://" in url
                assert "type=user-id" in url

    def test_max_uids_per_call(self):
        """Test that max UIDs per call are respected"""
        fw = PaloAltoFirewall(max_uids_per_call=2)

        mappings = {
            "192.168.1.1": {"username": "user1", "status": "start"},
            "192.168.1.2": {"username": "user2", "status": "start"},
            "192.168.1.3": {"username": "user3", "status": "start"},
            "192.168.1.4": {"username": "user4", "status": "start"},
        }
        targets = [{"hostname": "fw01", "vsys": "1", "apikey": "test"}]

        xml_dict = fw.xml_formatter_v67(mappings, targets, timeout=60)
        first_key = list(xml_dict.keys())[0]

        # Should have multiple entries due to max_uids_per_call=2
        assert len(xml_dict[first_key]) >= 2


class TestPaloAltoFirewallLegacyAlias:
    """Test legacy alias compatibility"""

    def test_legacy_import(self):
        """Test that the legacy class name still works"""
        from radiuid import palo_alto_firewall_interaction
        fw = palo_alto_firewall_interaction()
        assert isinstance(fw, PaloAltoFirewall)
